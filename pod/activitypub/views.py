from django.http import JsonResponse


def webfinger(request):
    resource = request.GET.get("resource", "")
    if resource:
        info = {
            "subject": resource,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": f"{'localhost:9090'}/accounts/{'instance_name'}",  # TODO: get the app domain
                }
            ]
        }
        return JsonResponse(info, status=200)


def instance_account(request):
    header_accept = request.headers.get("ACCEPT", "")
    if header_accept:
        instance_data = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
                {
                    "RsaSignature2017": "https://w3id.org/security#RsaSignature2017"
                },
            ],
            "type": "Application",
            "id": f"{'localhost:9090'}/accounts/instance_name",  # TODO: get the app domain
            "following": "localhost:9090/accounts/instance_name/following",
            "followers": "localhost:9090/accounts/instance_name/followers",
            "inbox": "localhost:9090/accounts/instance_name/inbox",
            "outbox": "localhost:9090/accounts/instance_name/outbox",
            "preferredUsername": "instance_name",
            "url": "localhost:9090/accounts/instance_name",
            "name": "instance_name",  # TODO: get the app name
            "publicKey": {
                "id": "localhost:9090/accounts/instance_name#main-key",  # TODO: Find usage
                "owner": "localhost:9090/accounts/instance_name",
                "publicKeyPem": "thisisapublickey"  # TODO: Generate key pair
            },
            "published": "2018-07-01T11:59:04.556Z",  # TODO: Find which date it corresponds
        }
        return JsonResponse(instance_data, status=200)


def inbox(request):
    # receive follow request by post
    # post an accept response to wannabe follower
    # receive followed instance new videos/updates activity by post
    pass


def outbox(request):
    # list all current instance videos
    pass


def following(request):
    # list all followed instances
    pass


def followers(request):
    # list all current instance followers
    pass
