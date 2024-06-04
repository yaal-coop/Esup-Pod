import json

import httmock
from django.test import TestCase


class ActivityPubTestCase(TestCase):
    """ActivityPub test case."""

    maxDiff = None
    fixtures = ["initial_data.json"]
    headers = {
        "HTTP_ACCEPT": "application/activity+json, application/ld+json",
    }

    @httmock.urlmatch(path=r"/accounts/peertube/inbox")
    def mock_inbox(self, url, request):
        return httmock.response(204, "")

    @httmock.urlmatch(path=r"/accounts/peertube")
    def mock_get_actor(self, url, request):
        with open("pod/activitypub/tests/fixtures/application_actor.json") as fd:
            payload = json.load(fd)

        return httmock.response(200, payload)

    @httmock.urlmatch(path=r"/videos/watch.*")
    def mock_get_video(self, url, request):
        with open("pod/activitypub/tests/fixtures/peertube_video.json") as fd:
            payload = json.load(fd)

        return httmock.response(200, payload)

    @httmock.urlmatch(path=r"/video-channels/.*")
    def mock_get_channel(self, url, request):
        with open("pod/activitypub/tests/fixtures/channel.json") as fd:
            payload = json.load(fd)

        return httmock.response(200, payload)
