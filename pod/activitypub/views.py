import logging
import json


from django.conf import settings
from django.http import JsonResponse
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .constants import ACTIVITYPUB_CONTEXT
from .constants import PEERTUBE_ACTOR_ID
from .utils import ap_url
from .tasks import send_accept_request

logger = logging.getLogger(__name__)


def nodeinfo(request):
    return JsonResponse(
        {
            "links": [
                {
                    "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                    "href": ap_url("/nodeinfo/2.0.json"),
                },
                {
                    "rel": "https://www.w3.org/ns/activitystreams#Application",
                    #"href": f"http://localhost:9000/accounts/{PEERTUBE_ACTOR_ID}",
                    "href": ap_url(reverse("activitypub:instance_account")),
                },
            ]
        },
        status=200,
    )


@csrf_exempt
def webfinger(request):
    logger.info("webfinger")
    # TODO: reject accounts that are not peertube@THISDOMAIN

    resource = request.GET.get("resource", "")
    if resource:
        info = {
            "subject": resource,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": ap_url(reverse("activitypub:instance_account")),
                }
            ],
        }
        return JsonResponse(info, status=200)


@csrf_exempt
def instance_account(request):
    logger.info("instance_account")
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
    logger.warning(f"inbox data: {data}")
    # TODO: reject invalid objects
    # TODO: test double follows
    # TODO: test HTTP signature

    # TODO: make an async call from this
    if data["type"] == "Follow":
        send_accept_request(actor=data["actor"], object=data["object"])

    return HttpResponse(204)


@csrf_exempt
def outbox(request):
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"outbox data: {data}")
    # list all current instance videos
    return JsonResponse({}, status=200)


@csrf_exempt
def following(request):
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"following data: {data}")
    # list all followed instances
    return JsonResponse({}, status=200)


@csrf_exempt
def followers(request):
    data = json.loads(request.body.decode()) if request.body else None
    logger.warning(f"followers data: {data}")
    # list all current instance followers
    return JsonResponse({}, status=200)
