import logging
from urllib.parse import urlparse

import requests
from django.urls import reverse

from .constants import ACTIVITYPUB_CONTEXT
from .constants import BASE_HEADERS
from .constants import PEERTUBE_ACTOR_ID
from .models import Follower
from .models import Following
from .utils import ap_url
from .utils import signed_payload_headers
from pod.main.celery import app


logger = logging.getLogger(__name__)
def get_peertube_account_url(url):
    parsed = urlparse(url)
    # TODO: handle exceptions
    webfinger_url = (
        f"{url}/.well-known/webfinger?resource=acct:{PEERTUBE_ACTOR_ID}@{parsed.netloc}"
    )
    response = requests.get(webfinger_url, headers=BASE_HEADERS)
    for link in response.json()["links"]:
        if link["rel"] == "self":
            return link["href"]


def get_peertube_account_metadata(domain):
    account_url = get_peertube_account_url(domain)
    response = requests.get(account_url, headers=BASE_HEADERS)
    return response.json()


def send_accept_request(actor, object):
    logging.warning(f"read {actor}")
    actor_account = requests.get(actor, headers=BASE_HEADERS).json()
    inbox = actor_account['inbox']

    follower, _ = Follower.objects.get_or_create(actor=actor)
    followers_url = ap_url(reverse("activitypub:followers"))
    payload = {
        "@context": ACTIVITYPUB_CONTEXT,
        "id": f"{followers_url}/{follower.id}",
        "type": "Accept",
        "actor": actor,
        "object": object,
    }
    logging.warning(f"send {inbox} {payload}")
    signature_headers = signed_payload_headers(payload, inbox)
    response = requests.post(
        inbox, json=payload, headers={**BASE_HEADERS, **signature_headers}
    )
    return response.status_code == 204

def send_follow_request(metadata):
    # TODO: handle rejects
    following, _ = Following.objects.get_or_create(object=metadata["id"])
    following_url = ap_url(reverse("activitypub:following"))
    payload = {
        "@context": ACTIVITYPUB_CONTEXT,
        "type": "Follow",
        "id": f"{following_url}/{following.id}",
        "actor": ap_url(reverse("activitypub:instance_account")),
        "object": metadata["id"],
    }
    signature_headers = signed_payload_headers(payload, metadata["inbox"])
    response = requests.post(
        metadata["inbox"], json=payload, headers={**BASE_HEADERS, **signature_headers}
    )
    return response.status_code == 204


@app.task(bind=True)
def task_follow(self, url):
    metadata = get_peertube_account_metadata(url)
    return send_follow_request(metadata)
