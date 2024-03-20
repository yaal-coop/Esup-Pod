import logging
import json


from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .constants import ACTIVITYPUB_CONTEXT
from .constants import PEERTUBE_CONTEXT
from .constants import PEERTUBE_ACTOR_ID
from .utils import ap_url
from pod.video.models import Video
from .tasks import send_accept_request

logger = logging.getLogger(__name__)

AP_PAGE_SIZE = 25


def nodeinfo(request):
    logger.warning("nodeinfo")
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
    return JsonResponse(response, status=200)


@csrf_exempt
def webfinger(request):
    logger.warning("webfinger")
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
        return JsonResponse(response, status=200)


@csrf_exempt
def instance_account(request):
    logger.warning("instance_account")
    instance_actor_url = ap_url(reverse("activitypub:instance_account"))
    instance_data = {
        "@context": ACTIVITYPUB_CONTEXT,
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
    return JsonResponse(instance_data, status=200)


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
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"outbox query: \n{data}\n{request.POST}\n{request.GET}")
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
            "@context": ACTIVITYPUB_CONTEXT,
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
            "@context": ACTIVITYPUB_CONTEXT,
            "id": ap_url(reverse("activitypub:outbox")),
            "type": "OrderedCollection",
            "totalItems": nb_videos,
            "first": ap_url(reverse("activitypub:outbox")) + "?page=1",
        }

    else:
        response = {
            "@context": ACTIVITYPUB_CONTEXT,
            "id": ap_url(reverse("activitypub:outbox")),
            "type": "OrderedCollection",
            "totalItems": 0,
        }

    logger.warning(f"outbox response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def following(request):
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"following query: {data}")
    # list all followed instances
    response = {
        "@context": ACTIVITYPUB_CONTEXT,
        "id": ap_url(reverse("activitypub:following")),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    logger.warning(f"following response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def followers(request):
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"followers data: {data}")
    # list all current instance followers
    response = {
        "@context": ACTIVITYPUB_CONTEXT,
        "id": ap_url(reverse("activitypub:followers")),
        "type": "OrderedCollection",
        "totalItems": 0,
    }
    logger.warning(f"followers response: {response}")
    return JsonResponse(response, status=200)


@csrf_exempt
def video(request, slug):
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"video data: {data}")
    video = get_object_or_404(Video, slug=slug)
    response = {
        "@context": ACTIVITYPUB_CONTEXT + [PEERTUBE_CONTEXT],
        "id": ap_url(reverse("activitypub:video", kwargs={"slug": slug})),
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": ["https://tube.aquilenet.fr/accounts/user/followers"],
        "type": "Video",
        "name": video.title,
        # duration must fit the xsd:duration format
        # https://www.w3.org/TR/xmlschema11-2/#duration
        "duration": f"PT{video.duration}S",
        "uuid": "aad71797-78b9-4b5a-a3d6-f93fae80b7e7",
        "category": {"identifier": "11", "name": "News & Politics"},  # video.type
        "views": video.viewcount,
        #        "sensitive": false,
        "waitTranscoding": video.encoding_in_progress,
        #        "state": 1,
        "commentsEnabled": not video.disable_comment,
        "downloadEnabled": video.allow_downloading,
        "published": video.date_added.isoformat(),  # "2024-03-19T08:46:49.185Z",
        #        "originallyPublishedAt": null,
        #        "updated": "2024-03-19T08:46:49.185Z",
        "tag": [],  # video.type
        #        "mediaType": "text/markdown",
        #        "content": null,
        #        "support": null,
        #        "subtitleLanguage": [],
        #        "icon": [
        #            {
        #                "type": "Image",
        #                "url": "https://tube.aquilenet.fr/lazy-static/thumbnails/0d18ad55-f86d-4548-957c-fa0f26e3443b.jpg",
        #                "mediaType": "image/jpeg",
        #                "width": 280,
        #                "height": 157,
        #            },
        #        ],
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
        "url": [
            {
                "type": "Link",
                "mediaType": "text/html",
                "href": reverse("video:video", args=(video.slug,)),
            },
            {
                "type": "Link",
                "mediaType": "video/mp4",
                "href": video.get_video_mp4_json(),
                "height": 720,
                "size": 16555783,
                "fps": 24,
            },
        ],
        #        "likes": "https://tube.aquilenet.fr/videos/watch/aad71797-78b9-4b5a-a3d6-f93fae80b7e7/likes",
        #        "dislikes": "https://tube.aquilenet.fr/videos/watch/aad71797-78b9-4b5a-a3d6-f93fae80b7e7/dislikes",
        #        "shares": "https://tube.aquilenet.fr/videos/watch/aad71797-78b9-4b5a-a3d6-f93fae80b7e7/announces",
        #        "comments": "https://tube.aquilenet.fr/videos/watch/aad71797-78b9-4b5a-a3d6-f93fae80b7e7/comments",  # notecomments
        #        "hasParts": "https://tube.aquilenet.fr/videos/watch/aad71797-78b9-4b5a-a3d6-f93fae80b7e7/chapters",
        "attributedTo": [
            {
                "type": "Person",
                "id": ap_url(reverse("activitypub:instance_account")),  # video.owner
            },
            #            {
            #                "type": "Group",
            #                "id": "https://tube.aquilenet.fr/video-channels/channel",  # video.channel
            #            },
        ],
        #        "isLiveBroadcast": false,
        #        "liveSaveReplay": null,
        #        "permanentLive": null,
        #        "latencyMode": null,
        #        "peertubeLiveChat": false,
    }
    if video.licence:
        response["licence"] = {"identifier": video.licence, "name": video.get_licence()}

    if video.main_lang:
        response["language"] = {
            "identifier": video.main_lang,
            "name": video.get_main_lang(),
        }

    logger.warning(f"video response: {response}")
    return JsonResponse(response, status=200)
