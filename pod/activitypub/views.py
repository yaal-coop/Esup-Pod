"""Django ActivityPub endpoints"""

import json
import logging
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from pod.video.models import Channel, Video

from .constants import (
    AP_DEFAULT_CONTEXT,
    AP_PT_CHANNEL_CONTEXT,
    AP_PT_CHAPTERS_CONTEXT,
    AP_PT_VIDEO_CONTEXT,
    INSTANCE_ACTOR_ID,
)
from .models import Following
from .serialization import video_to_ap_payload
from .tasks import (
    task_external_video_deletion,
    task_external_video_update,
    task_read_announce,
    task_send_accept_request,
)
from .utils import ap_url

logger = logging.getLogger(__name__)


AP_PAGE_SIZE = 25


def nodeinfo(request):
    """
    Nodeinfo endpoint. This is the entrypoint for ActivityPub federation.

    https://github.com/jhass/nodeinfo/blob/main/PROTOCOL.md
    https://nodeinfo.diaspora.software/
    """

    response = {
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                # This URL is not implemented yet as it does not seem mandatory
                # for Peertube pairing.
                "href": ap_url("/nodeinfo/2.0.json"),
            },
            {
                "rel": "https://www.w3.org/ns/activitystreams#Application",
                "href": ap_url(reverse("activitypub:account")),
            },
        ]
    }
    logger.warning(f"nodeinfo response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def webfinger(request):
    """webfinger endpoint as described in RFC7033.

    Deal with account information request and return account endpoints.

    https://www.rfc-editor.org/rfc/rfc7033.html
    https://docs.joinmastodon.org/spec/webfinger/
    """

    # TODO: check that this is even needed
    # TODO: reject accounts that are not peertube@THISDOMAIN

    resource = request.GET.get("resource", "")
    if resource:
        response = {
            "subject": resource,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": ap_url(reverse("activitypub:account")),
                }
            ],
        }
        logger.warning(f"webfinger response: {response}")
        return JsonResponse(response, status=200)


@csrf_exempt
def account(request, username=None):
    """
    'Person' or 'Application' description as defined by ActivityStreams.

    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-person
    """

    url_args = {"username": username} if username else {}
    instance_actor_url = ap_url(reverse("activitypub:account"))
    context = (
        AP_DEFAULT_CONTEXT + [AP_PT_CHANNEL_CONTEXT] if username else AP_DEFAULT_CONTEXT
    )
    account_type = "Person" if username else "Application"
    response = {
        "@context": context,
        "type": account_type,
        "id": ap_url(reverse("activitypub:account", kwargs=url_args)),
        "url": ap_url(reverse("activitypub:account", kwargs=url_args)),
        "following": ap_url(reverse("activitypub:following", kwargs=url_args)),
        "followers": ap_url(reverse("activitypub:followers", kwargs=url_args)),
        "inbox": ap_url(reverse("activitypub:inbox", kwargs=url_args)),
        "outbox": ap_url(reverse("activitypub:outbox", kwargs=url_args)),
        "endpoints": {
            "sharedInbox": ap_url(reverse("activitypub:inbox", kwargs=url_args))
        },
        "publicKey": {
            "id": f"{instance_actor_url}#main-key",
            "owner": instance_actor_url,
            "publicKeyPem": settings.ACTIVITYPUB_PUBLIC_KEY,
        },
    }

    if username:
        user = get_object_or_404(User, username=username)
        response["preferredUsername"] = user.username
        response["name"] = user.get_full_name() or user.username
        response["summary"] = user.owner.commentaire

        if user.owner.userpicture:
            response["icon"] = [
                {
                    "type": "Image",
                    "url": ap_url(user.owner.userpicture.file.url),
                    "height": user.owner.userpicture.file.width,
                    "width": user.owner.userpicture.file.height,
                    "mediaType": user.owner.userpicture.file_type,
                },
            ]

    else:
        response["name"] = INSTANCE_ACTOR_ID
        response["preferredUsername"] = INSTANCE_ACTOR_ID

    logger.warning(f"account response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def inbox(request, username=None):
    """
    Inbox as defined in ActivityPub.
    https://www.w3.org/TR/activitypub/#inbox
    """

    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"inbox query: {data}")
    # TODO: reject invalid objects
    # TODO: test double follows
    # TODO: test HTTP signature

    if not username and data["type"] == "Follow":
        task_send_accept_request.delay(
            follow_actor=data["actor"],
            follow_object=data["object"],
            follow_id=data["id"],
        )

    elif (
        not username and data["type"] == "Accept" and data["object"]["type"] == "Follow"
    ):
        parsed = urlparse(data["object"]["object"])
        obj = f"{parsed.scheme}://{parsed.netloc}"
        follower = Following.objects.get(object=obj)
        follower.status = Following.Status.ACCEPTED
        follower.save()

    elif (
        not username and data["type"] == "Reject" and data["object"]["type"] == "Follow"
    ):
        parsed = urlparse(data["object"]["object"])
        obj = f"{parsed.scheme}://{parsed.netloc}"
        follower = Following.objects.get(object=obj)
        follower.status = Following.Status.REFUSED
        follower.save()

    elif not username and data["type"] == "Announce":
        task_read_announce.delay(actor=data["actor"], object_id=data["object"])

    elif (
        not username and data["type"] == "Update" and data["object"]["type"] == "Video"
    ):
        task_external_video_update.delay(video=data["object"])

    elif not username and data["type"] == "Delete":
        task_external_video_deletion.delay(object_id=data["object"])

    else:
        logger.warning(f"... ignoring: {data}")

    return HttpResponse(status=204)


@csrf_exempt
def outbox(request, username=None):
    """
    Outbox as defined in ActivityPub.
    https://www.w3.org/TR/activitypub/#outbox

    Lists videos 'Announce' objects.
    """

    url_args = {"username": username} if username else {}
    page = int(request.GET.get("page", 0))
    user = get_object_or_404(User, username=username) if username else None
    video_query = Video.objects.filter(is_restricted=False)
    if user:
        video_query = video_query.filter(owner=user)
    nb_videos = video_query.count()

    if page:
        first_index = (page - 1) * AP_PAGE_SIZE
        last_index = min(nb_videos, first_index + AP_PAGE_SIZE)
        items = video_query[first_index:last_index].all()
        next_page = page + 1 if (page + 1) * AP_PAGE_SIZE < nb_videos else None
        response = {
            "@context": AP_DEFAULT_CONTEXT,
            "id": ap_url(reverse("activitypub:outbox", kwargs=url_args)),
            "type": "OrderedCollection",
            "totalItems": nb_videos,
            "orderedItems": [
                {
                    "to": ["https://www.w3.org/ns/activitystreams#Public"],
                    "cc": [ap_url(reverse("activitypub:followers", kwargs=url_args))],
                    "type": "Announce",
                    "id": ap_url(
                        reverse("activitypub:video", kwargs={"slug": item.slug})
                    )
                    + "/announces/1",
                    "actor": ap_url(reverse("activitypub:account", kwargs=url_args)),
                    "object": ap_url(
                        reverse("activitypub:video", kwargs={"slug": item.slug})
                    ),
                }
                for item in items
            ],
        }
        if next_page:
            response["next"] = (
                ap_url(reverse("activitypub:outbox", kwargs=url_args))
                + "?page="
                + next_page
            )

    elif nb_videos:
        response = {
            "@context": AP_DEFAULT_CONTEXT,
            "id": ap_url(reverse("activitypub:outbox", kwargs=url_args)),
            "type": "OrderedCollection",
            "totalItems": nb_videos,
            "first": ap_url(reverse("activitypub:outbox", kwargs=url_args)) + "?page=1",
        }

    else:
        response = {
            "@context": AP_DEFAULT_CONTEXT,
            "id": ap_url(reverse("activitypub:outbox", kwargs=url_args)),
            "type": "OrderedCollection",
            "totalItems": 0,
        }

    logger.warning(f"outbox response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def following(request, username=None):
    """
    'Following' objects collection as defined in ActivityPub.

    https://www.w3.org/TR/activitypub/#following
    """

    url_args = {"username": username} if username else {}
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:following", kwargs=url_args)),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    logger.warning(f"following response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def followers(request, username=None):
    """
    'Followers' objects collection as defined ActivityPub.

    https://www.w3.org/TR/activitypub/#followers
    """

    url_args = {"username": username} if username else {}
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:followers", kwargs=url_args)),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    logger.warning(f"followers response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def video(request, slug):
    """
    'Video' object as defined on ActivityStreams, with additions from the Peertube NS.

    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-video
    https://docs.joinpeertube.org/api/activitypub#video
    """

    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": AP_DEFAULT_CONTEXT + [AP_PT_VIDEO_CONTEXT],
        **video_to_ap_payload(video),
    }
    logger.warning(f"video response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def channel(request, slug):
    """
    'Group' object as defined by ActivityStreams, with additions from the Peertube NS.

    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-group
    https://docs.joinpeertube.org/api/activitypub
    """

    channel = get_object_or_404(Channel, slug=slug)
    instance_actor_url = ap_url(reverse("activitypub:account"))
    inbox_url = ap_url(reverse("activitypub:channel", kwargs={"slug": slug})) + "/inbox"
    # https://github.com/Chocobozzz/PeerTube/blob/8da3e2e9b8229215e3eeb030b491a80cf37f889d/server/core/helpers/custom-validators/activitypub/actor.ts#L62
    response = {
        "@context": AP_DEFAULT_CONTEXT + [AP_PT_CHANNEL_CONTEXT],
        "type": "Group",
        "id": ap_url(reverse("activitypub:channel", kwargs={"slug": slug})),
        # "following": "https://tube.aquilenet.fr/video-channels/USER_channel/following",
        # "followers": "https://tube.aquilenet.fr/video-channels/USER_channel/followers",
        # "playlists": "https://tube.aquilenet.fr/video-channels/USER_channel/playlists",
        # needed by peertube
        # this is a fake URL and is not intented to be reached
        "inbox": inbox_url,
        # "outbox": "https://tube.aquilenet.fr/video-channels/USER_channel/outbox",
        # needed by peertube, seems to not support spaces
        "preferredUsername": channel.slug,
        # needed by peertube
        "url": ap_url(reverse("activitypub:channel", kwargs={"slug": slug})),
        "name": channel.title,
        "endpoints": {"sharedInbox": inbox_url},
        # needed by peertube
        "publicKey": {
            "id": f"{instance_actor_url}#main-key",
            "owner": instance_actor_url,
            "publicKeyPem": settings.ACTIVITYPUB_PUBLIC_KEY,
        },
        # "published": "2020-11-29T21:53:21.363Z",
        # "icon": [
        #    {
        #        "type": "Image",
        #        "mediaType": "image/png",
        #        "height": 48,
        #        "width": 48,
        #        "url": "https://tube.aquilenet.fr/lazy-static/avatars/e904f75e-917b-41da-97b6-0ec5d8d59990.png",
        #    },
        #    {
        #        "type": "Image",
        #        "mediaType": "image/png",
        #        "height": 120,
        #        "width": 120,
        #        "url": "https://tube.aquilenet.fr/lazy-static/avatars/e54d9c61-7c69-4ea9-9e22-0cd8b6847caf.png",
        #    },
        # ],
        "summary": channel.description,
        # "support": None,
        # needed by peertube
        "attributedTo": [
            {
                "type": "Person",
                "id": ap_url(
                    reverse("activitypub:account", kwargs={"username": owner.username})
                ),
            }
            for owner in channel.owners.all()
        ],
    }

    if channel.headband:
        response["image"] = {
            "type": "Image",
            "url": channel.headband.file.url,
            # "height": 317,
            # "width": 1920,
            "mediaType": channel.headband.file_type,
        }

    logger.warning(f"video response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def likes(request, slug):
    """
    'Like' objects collection as defined by ActivityStreams and ActivityPub.

    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-like
    https://www.w3.org/TR/activitypub/#liked
    """

    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)


@csrf_exempt
def dislikes(request, slug):
    """
    'Dislike' objects collection as defined by ActivityStreams and ActivityPub.

    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-like
    https://www.w3.org/TR/activitypub/#liked
    """

    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:dislikes", kwargs={"slug": video.slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)


@csrf_exempt
def shares(request, slug):
    """
    'Share' objects collection as defined by ActivityPub.

    https://www.w3.org/TR/activitypub/#video_shares
    """

    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:shares", kwargs={"slug": video.slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)


@csrf_exempt
def comments(request, slug):
    """
    'Note' objects collection as defined by ActivityStreams.

    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-note
    """

    video = get_object_or_404(Video, slug=slug)
    # TODO: video.notecomments
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:comments", kwargs={"slug": video.slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)


@csrf_exempt
def chapters(request, slug):
    """
    Video chapters description as defined by Peertube.

    https://joinpeertube.org/ns
    """

    video = get_object_or_404(Video, slug=slug)
    # TODO: video.chapters
    response = {
        "@context": AP_DEFAULT_CONTEXT + [AP_PT_CHAPTERS_CONTEXT],
        "id": ap_url(reverse("activitypub:comments", kwargs={"slug": video.slug})),
        "hasPart": [
            {
                "name": chapter.title,
                "startOffset": chapter.time_start,
                "endOffset": chapter.time_stop,
            }
            for chapter in video.chapter_set.all()
        ],
    }
    return JsonResponse(response, status=200)
