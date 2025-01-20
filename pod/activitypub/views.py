"""Django ActivityPub endpoints"""

import json
import logging

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
)
from .serialization.account import account_to_ap_payload
from .serialization.channel import channel_to_ap_payload
from .serialization.video import video_to_ap_payload
from .tasks import (
    task_handle_inbox_accept,
    task_handle_inbox_announce,
    task_handle_inbox_delete,
    task_handle_inbox_follow,
    task_handle_inbox_reject,
    task_handle_inbox_update,
    task_handle_inbox_undo,
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
    logger.debug("nodeinfo response: %s", json.dumps(response, indent=True))
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
        logger.debug("webfinger response: %s", json.dumps(response, indent=True))
        return JsonResponse(response, status=200)


@csrf_exempt
def account(request, username=None):
    """
    'Person' or 'Application' description as defined by ActivityStreams.

    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-person
    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-application
    """
    user = get_object_or_404(User, username=username) if username else None

    context = (
        AP_DEFAULT_CONTEXT + [AP_PT_CHANNEL_CONTEXT] if user else AP_DEFAULT_CONTEXT
    )
    response = {
        "@context": context,
        **account_to_ap_payload(user),
    }
    logger.debug("account response: %s", json.dumps(response, indent=True))
    return JsonResponse(response, status=200)


@csrf_exempt
def inbox(request, username=None):
    """
    Inbox as defined in ActivityPub.
    https://www.w3.org/TR/activitypub/#inbox
    """

    data = json.loads(request.body.decode()) if request.body else None
    logger.warning("inbox query: %s", json.dumps(data, indent=True))
    # TODO: test HTTP signature

    if not username and data["type"] == "Follow":
        task_handle_inbox_follow.delay(username, data)

    elif not username and data["type"] == "Accept":
        task_handle_inbox_accept.delay(username, data)

    elif not username and data["type"] == "Reject":
        task_handle_inbox_reject.delay(username, data)

    elif not username and data["type"] == "Announce":
        task_handle_inbox_announce.delay(username, data)

    elif not username and data["type"] == "Update":
        task_handle_inbox_update.delay(username, data)

    elif not username and data["type"] == "Delete":
        task_handle_inbox_delete.delay(username, data)

    elif not username and data["type"] == "Undo":
        task_handle_inbox_undo.delay(username, data)

    else:
        logger.debug("Ignoring inbox action: %s", data["type"])

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

    logger.debug("outbox response: %s", json.dumps(response, indent=True))
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
    logger.debug("following response: %s", json.dumps(response, indent=True))
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
    logger.debug("followers response: %s", json.dumps(response, indent=True))
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
    logger.debug("video response: %s", json.dumps(response, indent=True))
    return JsonResponse(response, status=200)


@csrf_exempt
def channel(request, slug):
    """
    'Group' object as defined by ActivityStreams, with additions from the Peertube NS.

    https://www.w3.org/TR/activitystreams-vocabulary/#dfn-group
    https://docs.joinpeertube.org/api/activitypub
    """
    channel = get_object_or_404(Channel, slug=slug)

    response = {
        "@context": AP_DEFAULT_CONTEXT + [AP_PT_CHANNEL_CONTEXT],
        **channel_to_ap_payload(channel),
    }

    logger.debug("video response: %s", json.dumps(response, indent=True))
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
