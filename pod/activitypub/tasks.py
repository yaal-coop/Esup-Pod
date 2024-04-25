import logging
from urllib.parse import urlparse

import requests
from django.urls import reverse

from pod.main.celery import app

from .constants import AP_DEFAULT_CONTEXT, BASE_HEADERS, INSTANCE_ACTOR_ID
from .models import Follower, Following
from .utils import ap_url, signed_payload_headers

logger = logging.getLogger(__name__)


def get_peertube_account_url(url):
    parsed = urlparse(url)
    # TODO: handle exceptions
    webfinger_url = (
        f"{url}/.well-known/webfinger?resource=acct:{INSTANCE_ACTOR_ID}@{parsed.netloc}"
    )
    response = requests.get(webfinger_url, headers=BASE_HEADERS)
    for link in response.json()["links"]:
        if link["rel"] == "self":
            return link["href"]


def get_peertube_account_metadata(domain):
    account_url = get_peertube_account_url(domain)
    response = requests.get(account_url, headers=BASE_HEADERS)
    return response.json()


def send_accept_request(follow_actor, follow_object, follow_id):
    logging.warning(f"read {follow_actor}")
    actor_account = requests.get(follow_actor, headers=BASE_HEADERS).json()
    inbox = actor_account["inbox"]

    follower, _ = Follower.objects.get_or_create(actor=follow_actor)
    payload = {
        "@context": AP_DEFAULT_CONTEXT,
        "id": ap_url(f"/accepts/follows/{follower.id}"),
        "type": "Accept",
        "actor": follow_object,
        "object": {
            "type": "Follow",
            "id": follow_id,
            "actor": follow_actor,
            "object": follow_object,
        },
    }
    signature_headers = signed_payload_headers(payload, inbox)
    logging.warning(f"send {inbox}\n{signature_headers}\n{payload}")
    response = requests.post(
        inbox, json=payload, headers={**BASE_HEADERS, **signature_headers}
    )
    return response.status_code == 204


def send_follow_request(metadata):
    # TODO: handle rejects
    following, _ = Following.objects.get_or_create(object=metadata["id"])
    following_url = ap_url(reverse("activitypub:following"))
    payload = {
        "@context": AP_DEFAULT_CONTEXT,
        "type": "Follow",
        "id": f"{following_url}/{following.id}",
        "actor": ap_url(reverse("activitypub:account")),
        "object": metadata["id"],
    }
    signature_headers = signed_payload_headers(payload, metadata["inbox"])
    response = requests.post(
        metadata["inbox"], json=payload, headers={**BASE_HEADERS, **signature_headers}
    )
    return response.status_code == 204


@app.task(bind=True)
def task_follow(self, following_id):
    following = Following.objects.get(id=following_id)
    return True
    metadata = get_peertube_account_metadata(url)
    return send_follow_request(metadata)


@app.task(bind=True)
def task_index_videos(self, following_id):
    following = Following.objects.get(id=following_id)
    return True

