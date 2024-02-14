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
                    "href": f"{'localhost:9090'}/instance/{'instance_name'}",
                }
            ]
        }
        return JsonResponse(info, status=200)


def boxes(request):
    boxes = {
        "inbox": f"{'localhost:9090'}/instance/{'instance_name'}/inbox",
        "outbox": f"{'localhost:9090'}/instance/{'instance_name'}/outbox",
    }
    return JsonResponse(boxes, status=200)


def inbox(request):
    # get new external video
    pass


def outbox(request):
    # list of instance videos
    pass


def follow_request(request):
    # answer accept
    pass
