import logging
import json


from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .constants import AP_DEFAULT_CONTEXT
from .constants import AP_PT_VIDEO_CONTEXT
from .constants import AP_PT_CHANNEL_CONTEXT
from .constants import PEERTUBE_ACTOR_ID
from django.contrib.auth.models import User
from .utils import ap_url
from pod.video.models import Video
from pod.video.models import Channel
from .tasks import send_accept_request

logger = logging.getLogger(__name__)

AP_PAGE_SIZE = 25


def nodeinfo(request):
    response = {
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                "href": ap_url("/nodeinfo/2.0.json"),
            },
            {
                "rel": "https://www.w3.org/ns/activitystreams#Application",
                # "href": f"http://localhost:9000/accounts/{PEERTUBE_ACTOR_ID}",
                "href": ap_url(reverse("activitypub:instance_account")),
            },
        ]
    }
    logger.warning(f"nodeinfo response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def webfinger(request):
    # TODO: reject accounts that are not peertube@THISDOMAIN

    resource = request.GET.get("resource", "")
    if resource:
        response = {
            "subject": resource,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": ap_url(reverse("activitypub:instance_account")),
                }
            ],
        }
        logger.warning(f"webfinger response: {response}")
        return JsonResponse(response, status=200)


@csrf_exempt
def instance_account(request):
    instance_actor_url = ap_url(reverse("activitypub:instance_account"))
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "type": "Application",
        "id": instance_actor_url,
        "following": ap_url(reverse("activitypub:following")),
        "followers": ap_url(reverse("activitypub:followers")),
        "inbox": ap_url(reverse("activitypub:inbox")),
        "outbox": ap_url(reverse("activitypub:outbox")),
        "url": instance_actor_url,
        "name": PEERTUBE_ACTOR_ID,
        "preferredUsername": PEERTUBE_ACTOR_ID,
        "publicKey": {
            "id": f"{instance_actor_url}#main-key",
            "owner": instance_actor_url,
            "publicKeyPem": settings.ACTIVITYPUB_PUBLIC_KEY,
        },
    }
    logger.warning(f"instance_account response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def user(request, username):
    user = get_object_or_404(User, username=username)
    instance_actor_url = ap_url(reverse("activitypub:instance_account"))
    response = {
        "@context": AP_DEFAULT_CONTEXT + [AP_PT_CHANNEL_CONTEXT],
        "type": "Person",
        "id": ap_url(reverse("activitypub:user", kwargs={"username": username})),
        "url": ap_url(reverse("activitypub:user", kwargs={"username": username})),
        # "following": "https://tube.aquilenet.fr/accounts/eloi/following",
        # "followers": "https://tube.aquilenet.fr/accounts/eloi/followers",
        # "playlists": "https://tube.aquilenet.fr/accounts/eloi/playlists",
        "inbox": ap_url(
            reverse("activitypub:user", kwargs={"username": username}) + "/inbox"
        ),
        # "outbox": "https://tube.aquilenet.fr/accounts/eloi/outbox",
        "preferredUsername": user.username,
        "name": user.get_full_name() or user.username,
        # "endpoints": {"sharedInbox": "https://tube.aquilenet.fr/inbox"},
        # needed by peertube
        "publicKey": {
            "id": f"{instance_actor_url}#main-key",
            "owner": instance_actor_url,
            "publicKeyPem": settings.ACTIVITYPUB_PUBLIC_KEY,
        },
        # "published": "2019-09-09T12:16:39.267Z",
        "summary": user.owner.commentaire,
    }

    if user.owner.userpicture:
        response["icon"] = [
            {
                "type": "Image",
                "url": user.owner.userpicture.file.url,
                # "height": 48,
                # "width": 48,
                "mediaType": user.owner.userpicture.file_type,
            },
        ]

    return JsonResponse(response, status=200)


@csrf_exempt
def inbox(request):
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"inbox query: {data}")
    # TODO: reject invalid objects
    # TODO: test double follows
    # TODO: test HTTP signature

    # TODO: make an async call from this
    if data["type"] == "Follow":
        send_accept_request(
            follow_actor=data["actor"],
            follow_object=data["object"],
            follow_id=data["id"],
        )

    return HttpResponse(204)


@csrf_exempt
def outbox(request):
    # list all current instance videos
    video_query = Video.objects.filter(is_restricted=False)
    nb_videos = video_query.count()
    page = int(request.GET.get("page", 0))
    if page:
        first_index = (page - 1) * AP_PAGE_SIZE
        last_index = min(nb_videos, first_index + AP_PAGE_SIZE)
        items = video_query[first_index:last_index].all()
        next_page = page + 1 if (page + 1) * AP_PAGE_SIZE < nb_videos else None
        response = {
            "@context": AP_DEFAULT_CONTEXT,
            "id": ap_url(reverse("activitypub:outbox")),
            "type": "OrderedCollection",
            "totalItems": nb_videos,
            "orderedItems": [
                {
                    "to": ["https://www.w3.org/ns/activitystreams#Public"],
                    "cc": [ap_url(reverse("activitypub:followers"))],
                    "type": "Announce",
                    "id": ap_url(
                        reverse("activitypub:video", kwargs={"slug": item.slug})
                    )
                    + "/announces/1",
                    "actor": ap_url(reverse("activitypub:instance_account")),
                    "object": ap_url(
                        reverse("activitypub:video", kwargs={"slug": item.slug})
                    ),
                }
                for item in items
            ],
        }
        if next_page:
            response["next"] = (
                ap_url(reverse("activitypub:outbox")) + "?page=" + next_page
            )

    elif nb_videos:
        response = {
            "@context": AP_DEFAULT_CONTEXT,
            "id": ap_url(reverse("activitypub:outbox")),
            "type": "OrderedCollection",
            "totalItems": nb_videos,
            "first": ap_url(reverse("activitypub:outbox")) + "?page=1",
        }

    else:
        response = {
            "@context": AP_DEFAULT_CONTEXT,
            "id": ap_url(reverse("activitypub:outbox")),
            "type": "OrderedCollection",
            "totalItems": 0,
        }

    logger.warning(f"outbox response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def following(request):
    # list all followed instances
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:following")),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    logger.warning(f"following response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def followers(request):
    # list all current instance followers
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:followers")),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    logger.warning(f"followers response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def video(request, slug):
    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": AP_DEFAULT_CONTEXT + [AP_PT_VIDEO_CONTEXT],
        "id": ap_url(reverse("activitypub:video", kwargs={"slug": slug})),
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": ["https://tube.aquilenet.fr/accounts/user/followers"],
        "type": "Video",
        "name": video.title,
        # duration must fit the xsd:duration format
        # https://www.w3.org/TR/xmlschema11-2/#duration
        "duration": f"PT{video.duration}S",
        # TODO: uuid is needed
        "uuid": "aad71797-78b9-4b5a-a3d6-f93fae80b7e7",
        # TODO
        # "category": {"identifier": "11", "name": "News & Politics & shit"},  # video.type
        # needed by peertube
        "views": video.viewcount,
        "waitTranscoding": video.encoding_in_progress,
        "commentsEnabled": not video.disable_comment,
        "downloadEnabled": video.allow_downloading,
        # TODO: peertube dates ends with Z
        # "2024-03-19T08:46:49.185Z"
        # needed by peertube
        "published": video.date_added.isoformat(),
        # needed by peertube
        "updated": video.date_added.isoformat(),
        # TODO
        "tag": [],  # video.type
        "url": (
            [
                {
                    "type": "Link",
                    "mediaType": "text/html",
                    "href": ap_url(reverse("video:video", args=(video.slug,))),
                },
            ]
            + [
                {
                    "type": "Link",
                    "mediaType": "video/mp4",
                    "href": ap_url(mp4["src"]),
                    "height": mp4["height"],
                    # size and fps are not available
                    # "size": 16555783,
                    # "fps": 24,
                }
                for mp4 in video.get_video_mp4_json()
            ]
        ),
        "attributedTo": [
            # needed by peertube
            {
                "type": "Person",
                "id": ap_url(
                    reverse(
                        "activitypub:user", kwargs={"username": video.owner.username}
                    )
                ),
            },
        ]
        + [
            # needed by peertube
            # TODO: ask peertube to make this optional
            # currently an error "Cannot find associated video channel to video" is raised
            # in the meantime, implement a default channel for users
            {
                "type": "Group",
                "id": ap_url(
                    reverse("activitypub:channel", kwargs={"slug": channel.slug})
                ),
            }
            for channel in video.channel.all()
        ],
        # needed by peertube
        "sensitive": False,
        # TODO: video.description
        #        "mediaType": "text/markdown",
        #        "content": null,
        # needed by peertube
        # TODO: ask to make likes/dislikes/shares/comments optional
        "likes": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        "dislikes": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        "shares": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        "comments": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        #        "state": 1,
        #        "originallyPublishedAt": null,
        #        "support": null,
        #        "subtitleLanguage": [],
        #        "preview": [  # video.overview
        #            {
        #                "type": "Image",
        #                "rel": ["storyboard"],
        #                "url": [
        #                    {
        #                        "mediaType": "image/jpeg",
        #                        "href": "https://tube.aquilenet.fr/lazy-static/storyboards/4e2b2c7e-d3aa-4de4-b264-ce9d258419e5.jpg",
        #                        "width": 1920,
        #                        "height": 1080,
        #                        "tileWidth": 192,
        #                        "tileHeight": 108,
        #                        "tileDuration": "PT1S",
        #                    }
        #                ],
        #            }
        #        ],
        #        "hasParts": "https://tube.aquilenet.fr/videos/watch/aad71797-78b9-4b5a-a3d6-f93fae80b7e7/chapters",
        #        "isLiveBroadcast": false,
        #        "liveSaveReplay": null,
        #        "permanentLive": null,
        #        "latencyMode": null,
        #        "peertubeLiveChat": false,
    }
    # if video.licence:
    #    response["licence"] = {"identifier": video.licence, "name": video.get_licence()}

    # if video.main_lang:
    #    response["language"] = {
    #        "identifier": video.main_lang,
    #        "name": video.get_main_lang(),
    #    }

    if video.thumbnail:
        # https://github.com/Chocobozzz/PeerTube/blob/8da3e2e9b8229215e3eeb030b491a80cf37f889d/server/core/helpers/custom-validators/activitypub/videos.ts#L185-L198
        response["icon"] = [
            {
                "type": "Image",
                "url": video.get_thumbnail_url(scheme=True),
                # only image/jpeg is supported on peertube - TODO: open a ticket to add support for other formats
                "mediaType": "image/jpeg",
                #                "mediaType": video.thumbnail.file_type,
                # width & height ar needed - TODO: implement size calculation in pod
                "width": 724,
                "height": 991,
            },
        ]

    logger.warning(f"video response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def channel(request, slug):
    channel = get_object_or_404(Channel, slug=slug)
    instance_actor_url = ap_url(reverse("activitypub:instance_account"))
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
        "inbox": ap_url(reverse("activitypub:channel", kwargs={"slug": slug}))
        + "/inbox",
        # "outbox": "https://tube.aquilenet.fr/video-channels/USER_channel/outbox",
        # needed by peertube, seems to not support spaces
        "preferredUsername": channel.slug,
        # needed by peertube
        "url": ap_url(reverse("activitypub:channel", kwargs={"slug": slug})),
        "name": channel.title,
        # "endpoints": {"sharedInbox": "https://tube.aquilenet.fr/inbox"},
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
                    reverse("activitypub:user", kwargs={"username": owner.username})
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
    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:likes", kwargs={"slug": slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)


@csrf_exempt
def dislikes(request, slug):
    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:dislikes", kwargs={"slug": slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)


@csrf_exempt
def shares(request, slug):
    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:shares", kwargs={"slug": slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)


@csrf_exempt
def comments(request, slug):
    video = get_object_or_404(Video, slug=slug)
    # TODO: video.notecomments
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:comments", kwargs={"slug": slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)
