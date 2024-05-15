"""Long-standing operations"""

import logging

import requests
from django.urls import reverse

from .constants import AP_DEFAULT_CONTEXT, BASE_HEADERS
from .models import Follower, Following
from .utils import ap_url, signed_payload_headers
from .serialization import ap_video_to_external_video
from pod.video.models import Video

logger = logging.getLogger(__name__)


def follow(following_id):
    following = Following.objects.get(id=following_id)

    metadata = get_instance_application_account_metadata(following.object)
    return send_follow_request(following, metadata)


def index_videos(following_id):
    following = Following.objects.get(id=following_id)

    metadata = get_instance_application_account_metadata(following.object)
    outbox_content = requests.get(metadata["outbox"], headers=BASE_HEADERS).json()
    if "first" in outbox_content:
        index_videos_page(following, outbox_content["first"])
    return True


def get_instance_application_account_url(url):
    """Read the instance nodeinfo well-known URL to get the main account URL."""
    # TODO: handle exceptions
    nodeinfo_url = f"{url}/.well-known/nodeinfo"
    response = requests.get(nodeinfo_url, headers=BASE_HEADERS)
    for link in response.json()["links"]:
        if link["rel"] == "https://www.w3.org/ns/activitystreams#Application":
            return link["href"]


def get_instance_application_account_metadata(domain):
    account_url = get_instance_application_account_url(domain)
    response = requests.get(account_url, headers=BASE_HEADERS)
    return response.json()


def send_accept_request(follow_actor, follow_object, follow_id):
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
    response = requests.post(
        inbox, json=payload, headers={**BASE_HEADERS, **signature_headers}
    )
    return response.status_code == 204


def send_follow_request(following, metadata):
    # TODO: handle rejects
    following_url = ap_url(reverse("activitypub:following"))
    payload = {
        "@context": AP_DEFAULT_CONTEXT,
        "type": "Follow",
        "id": f"{following_url}/{following.id}",
        "actor": ap_url(reverse("activitypub:account")),
        "object": metadata["id"],
    }
    logger.info(f"{payload}")
    signature_headers = signed_payload_headers(payload, metadata["inbox"])
    response = requests.post(
        metadata["inbox"], json=payload, headers={**BASE_HEADERS, **signature_headers}
    )

    following.status = Following.Status.REQUESTED
    following.save()

    return response.status_code == 204


def index_videos_page(following, page_url):
    """Parse a AP Video page payload, and handle each video."""
    content = requests.get(page_url, headers=BASE_HEADERS).json()
    for item in content["orderedItems"]:
        index_video(following, item["object"])

    if "next" in content:
        index_videos_page(following, content["next"])


def index_video(following, video_url):
    """Read a video payload and create an ExternalVideo object"""

    payload = requests.get(video_url, headers=BASE_HEADERS).json()
    logger.warning(f"TODO: Deal with video indexation {payload}")
    extvideo = ap_video_to_external_video(payload)
    extvideo.source_instance = following
    extvideo.save()


def read_announce(actor, object_id):
    actor_object = requests.get(actor, headers=BASE_HEADERS).json()
    obj = requests.get(object_id, headers=BASE_HEADERS).json()

    if obj["type"] != "Video":
        logger.debug(f"Ignoring announce about {obj['type']}")
        # TODO: Deal with other objects, like comments

    # Announce for a Video created by a user account
    if actor_object["type"] in ("Application", "Person"):
        # TODO: create an ExternalVideo
        logger.warning(f"TODO: Handle Video creation by {actor_object['type']}")

    # Announce for a Video added to a channel
    elif actor_object["type"] in ("Group"):
        # TODO: update the external video to add it to the matching channel
        logger.warning(f"TODO: Handle Video creation by {actor_object['type']}")

    else:
        logger.debug(f"Ignoring Video creation by {actor_object['type']}")


def external_video_update(video):
    # TODO: update the external video details
    logger.warning("TODO: Deal with Video updates")


def external_video_deletion(object_id):
    obj = requests.get(object_id, headers=BASE_HEADERS).json()

    if obj["type"] != "Video":
        logger.debug(f"Ignoring {obj['type']} deletion")

    # TODO: Delete the ExternalVideo
    logger.warning("TODO: Handle Video deletion")


def broadcast_local_video_creation(video_id):
    logger.warning("TODO: Broadcast Video creation")
    video = Video.objects.get(id=video_id)


def broadcast_local_video_update(video_id):
    logger.warning("TODO: Broadcast Video update")
    video = Video.objects.get(id=video_id)


def broadcast_local_video_deletion(video_id):
    logger.warning("TODO: Broadcast Video deletion")
    video = Video.objects.get(id=video_id)
