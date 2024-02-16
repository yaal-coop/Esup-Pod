from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from pod.activitypub.models import Followers


ACTIVITYPUB_CONTEXT = [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
]


def webfinger(request):
    # TODO: reject accounts that are not peertube@THISDOMAIN

    resource = request.GET.get("resource", "")
    if resource:
        info = {
            "subject": resource,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": request.build_absolute_uri(
                        reverse("activitypub:instance_account")
                    ),
                }
            ],
        }
        return JsonResponse(info, status=200)


def instance_account(request):
    instance_name = "peertube"
    instance_actor_url = request.build_absolute_uri(
        reverse("activitypub:instance_account")
    )
    instance_data = {
        "@context": ACTIVITYPUB_CONTEXT,
        "type": "Application",
        "id": instance_actor_url,
        "following": request.build_absolute_uri(reverse("activitypub:following")),
        "followers": request.build_absolute_uri(reverse("activitypub:followers")),
        "inbox": request.build_absolute_uri(reverse("activitypub:inbox")),
        "outbox": request.build_absolute_uri(reverse("activitypub:outbox")),
        "preferredUsername": instance_name,
        "url": instance_actor_url,
        "name": instance_name,
        "publicKey": {
            "id": f"{instance_actor_url}#main-key",
            "owner": instance_actor_url,
            "publicKeyPem": settings.ACTIVITYPUB_PUBLIC_KEY,
        },
    }
    return JsonResponse(instance_data, status=200)


def inbox(request):
    # receive follow request by post
    # post an accept response to wannabe follower
    # receive followed instance new videos/updates activity by post
    actor = request.POST["actor"]
    object = request.POST["object"]
    # TODO: reject invalid objects
    # TODO: test double follows
    # TODO: test HTTP signature
    follower, _ = Followers.objects.get_or_create(actor=actor)
    followers_url = request.build_absolute_uri(reverse("activitypub:followers"))
    response = {
        "@context": ACTIVITYPUB_CONTEXT,
        "id": f"{followers_url}/{follower.id}",
        "type": "Accept",
        "actor": actor,
        "object": object,
    }
    return JsonResponse(response, status=200)


def outbox(request):
    # list all current instance videos
    return JsonResponse({}, status=200)


def following(request):
    # list all followed instances
    return JsonResponse({}, status=200)


def followers(request):
    # list all current instance followers
    return JsonResponse({}, status=200)
