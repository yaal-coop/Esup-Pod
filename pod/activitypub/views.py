import json
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .constants import AP_DEFAULT_CONTEXT
from .constants import AP_PT_CHANNEL_CONTEXT
from .constants import AP_PT_VIDEO_CONTEXT
from .constants import INSTANCE_ACTOR_ID
from .tasks import send_accept_request
from .utils import ap_url
from .utils import stable_uuid
from pod.video.models import Channel
from pod.video.models import Video

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
                # "href": f"http://localhost:9000/accounts/{INSTANCE_ACTOR_ID}",
                "href": ap_url(reverse("activitypub:account")),
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
                    "href": ap_url(reverse("activitypub:account")),
                }
            ],
        }
        logger.warning(f"webfinger response: {response}")
        return JsonResponse(response, status=200)


@csrf_exempt
def account(request, username=None):
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
                    "url": user.owner.userpicture.file.url,
                    # "height": 48,
                    # "width": 48,
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
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"inbox query: {data}")
    # TODO: reject invalid objects
    # TODO: test double follows
    # TODO: test HTTP signature

    # TODO: make an async call from this
    if not username and data["type"] == "Follow":
        send_accept_request(
            follow_actor=data["actor"],
            follow_object=data["object"],
            follow_id=data["id"],
        )

    else:
        logger.warning(f"... ignoring")

    return HttpResponse(204)


@csrf_exempt
def outbox(request, username=None):
    # list all current videos
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
    # TODO: ask for a better error description than 'maybe not a video object'
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
        # TODO: needed by peertube in version 4 exactly - ask peertube why is it for
        "uuid": stable_uuid(video.id, 4),
        # TODO
        # "category": {"identifier": "11", "name": "News & Politics & shit"},  # video.type
        # needed by peertube
        "views": video.viewcount,
        "waitTranscoding": video.encoding_in_progress,
        "commentsEnabled": not video.disable_comment,
        "downloadEnabled": video.allow_downloading,
        # needed by peertube
        "published": video.date_added.isoformat(),
        # needed by peertube
        "updated": video.date_added.isoformat(),
        # TODO:
        # ask for tags to be optional (it is OK when it is empty)
        # https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/helpers/custom-validators/activitypub/videos.ts#L148-L157
        "tag": [
#            {"type": "Hashtag", "name": slugify(tag)} for tag in video.tags.split(" ")
        ],
        "url": (
            [
                {
                    # Webpage
                    "type": "Link",
                    "mediaType": "text/html",
                    "href": ap_url(reverse("video:video", args=(video.slug,))),
                },
            ]
            + [
                {
                    # MP4 link
                    "type": "Link",
                    "mediaType": mp4["type"],
                    "href": ap_url(mp4["src"]),
                    "height": mp4["height"],
                    # TODO: uncomment and check
#                    "size": mp4["size"],
                    # fps is not available - TODO: check if it is really needed by peertube
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
                        "activitypub:account", kwargs={"username": video.owner.username}
                    )
                ),
            },
        ]
        + [
            # needed by peertube
            # TODO: ask peertube to make this optional
            # https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/lib/activitypub/videos/shared/abstract-builder.ts#L47-L52
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
        # needed by peertube - TODO: ask for a default value?
        "sensitive": False,
        # TODO: ask to make likes/dislikes/shares/comments optional
        # needed by peertube
        "likes": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        # needed by peertube
        "dislikes": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        # needed by peertube
        "shares": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        # needed by peertube
        "comments": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        #        "state": 1,
        #        "originallyPublishedAt": null,
        #        "support": null,
        #        "subtitleLanguage": [
        #    {
        #      "identifier": "ca",
        #      "name": "Catalan",
        #      "url": "https://peertube2.cpy.re/lazy-static/video-captions/...-ca.vtt"
        #    }
        #                ],
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
    # TODO: uncomment and debug
    # if video.licence:
    #    response["licence"] = {"identifier": video.licence, "name": video.get_licence()}

    # TODO: uncomment and debug
    # if video.main_lang:
    #    response["language"] = {
    #        "identifier": video.main_lang,
    #        "name": video.get_main_lang(),
    #    }

    #if video.description:
        # peertube only supports one language : ask for several descriptions in several languages
        # peertube only supports markdown and not text/html
        # TODO: ask peertube for text/html support, and in the meantime use python-markdownify to convert in markdown
    #    response["mediaType"] = "text/markdown"
     #   response["content"] = video.description

    if video.thumbnail:
        # https://github.com/Chocobozzz/PeerTube/blob/8da3e2e9b8229215e3eeb030b491a80cf37f889d/server/core/helpers/custom-validators/activitypub/videos.ts#L185-L198
        response["icon"] = [
            {
                "type": "Image",
                "url": video.get_thumbnail_url(scheme=True),
                # only image/jpeg is supported on peertube
                # TODO: open a ticket to add support for other formats
                "mediaType": video.thumbnail.file_type,
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
    instance_actor_url = ap_url(reverse("activitypub:account"))
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
                    reverse("activitypub:account", kwargs={"username": owner.username})
                ),
            }
            for owner in channel.owners.all()
        ],
    }

    # TODO: This is hard to debug, add custom error messages for everything or doc
    # https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/helpers/custom-validators/activitypub/videos.ts#L72-L87

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
        "id": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)


@csrf_exempt
def dislikes(request, slug):
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
    video = get_object_or_404(Video, slug=slug)
    # TODO: video.notecomments
    response = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(reverse("activitypub:comments", kwargs={"slug": video.slug})),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    return JsonResponse(response, status=200)
