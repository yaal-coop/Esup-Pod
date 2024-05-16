from django.conf import settings
from django.urls import reverse

from pod.activitypub.constants import INSTANCE_ACTOR_ID
from pod.activitypub.utils import ap_url


def account_to_ap_payload(user):
    url_args = {"username": user.username} if user else {}
    response = {
        "id": ap_url(reverse("activitypub:account", kwargs=url_args)),
        **account_type(user),
        **account_url(user),
        **account_following(user),
        **account_followers(user),
        **account_inbox(user),
        **account_outbox(user),
        **account_endpoints(user),
        **account_public_key(user),
        **account_preferred_username(user),
        **account_name(user),
        **account_summary(user),
        **account_icon(user),
    }

    return response


def account_type(user):
    return {"type": "Person" if user else "Application"}


def account_url(user):
    url_args = {"username": user.username} if user else {}
    return {"url": ap_url(reverse("activitypub:account", kwargs=url_args))}


def account_following(user):
    url_args = {"username": user.username} if user else {}
    return {"following": ap_url(reverse("activitypub:following", kwargs=url_args))}


def account_followers(user):
    url_args = {"username": user.username} if user else {}
    return {"followers": ap_url(reverse("activitypub:followers", kwargs=url_args))}


def account_inbox(user):
    url_args = {"username": user.username} if user else {}
    return {"inbox": ap_url(reverse("activitypub:inbox", kwargs=url_args))}


def account_outbox(user):
    url_args = {"username": user.username} if user else {}
    return {"outbox": ap_url(reverse("activitypub:outbox", kwargs=url_args))}


def account_endpoints(user):
    """sharedInbox is needed by peertube to send video updates."""
    url_args = {"username": user.username} if user else {}
    return {
        "endpoints": {
            "sharedInbox": ap_url(reverse("activitypub:inbox", kwargs=url_args))
        }
    }


def account_public_key(user):
    instance_actor_url = ap_url(reverse("activitypub:account"))
    return {
        "publicKey": {
            "id": f"{instance_actor_url}#main-key",
            "owner": instance_actor_url,
            "publicKeyPem": settings.ACTIVITYPUB_PUBLIC_KEY,
        },
    }


def account_preferred_username(user):
    return {"preferredUsername": user.username if user else INSTANCE_ACTOR_ID}


def account_name(user):
    return {"name": user.username if user else INSTANCE_ACTOR_ID}


def account_summary(user):
    if user:
        return {"summary": user.owner.commentaire}
    return {}


def account_icon(user):
    if user and user.owner.userpicture:
        return {
            "icon": [
                {
                    "type": "Image",
                    "url": ap_url(user.owner.userpicture.file.url),
                    "height": user.owner.userpicture.file.width,
                    "width": user.owner.userpicture.file.height,
                    "mediaType": user.owner.userpicture.file_type,
                },
            ]
        }

    return {}
