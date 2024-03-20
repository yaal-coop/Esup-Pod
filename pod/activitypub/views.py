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
    logger.warning(f"outbox query: {data}")
    # list all current instance videos
    response = {}
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


pod = {
    "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
    ],
    "id": "http://pod.local:8080/account/peertube/followers/2",
    "type": "Accept",
    "actor": "http://peertube.local:9000/accounts/peertube",
    "object": "http://pod.local:8080/account/peertube",
}

peertube = {
    "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://w3id.org/security/v1",
        {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
    ],
    "type": "Accept",
    "id": "http://peertube.local:9000/accepts/follows/37",
    "actor": "http://peertube.local:9000/accounts/peertube",
    "object": {
        "type": "Follow",
        "id": "http://pod.local:8080/account/peertube/following/2",
        "actor": "http://pod.local:8080/account/peertube",
        "object": "http://peertube.local:9000/accounts/peertube",
    },
    "signature": {
        "type": "RsaSignature2017",
        "creator": "http://peertube.local:9000/accounts/peertube",
        "created": "2024-03-20T13:09:17.178Z",
        "signatureValue": "HGLedQAXswjsp31xqfBsDFSrZ8QQx0k+nvheYtoDrb3sIZoEYJBOb4XQkl022dIBRN/OfcQjOoHVIoKgo56H6Twdj7F7EWP9B80jbOR2S6U2mp6jnNtrn6fWuf1mcS9GaM4F/O2WHo9oqpt/tkosNiSsrGDUQsSH0/Ml7Krn0eI=",
    },
}
