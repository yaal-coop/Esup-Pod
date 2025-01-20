import json
import httmock
from . import ActivityPubTestCase


class VideoUpdateTest(ActivityPubTestCase):
    def test_video_creation(self):
        """Test video creation activities on the inbox.

        When a Video is created on peertube, it sends two announces:
        - one for the video creation on the user profile;
        - one for the video addition on the user channel.

        This tests the situation where the account announce is received first.
        """

        with open(
            "pod/activitypub/tests/fixtures/video_creation_account_announce.json"
        ) as fd:
            account_announce_payload = json.load(fd)

        with httmock.HTTMock(self.mock_get_actor, self.mock_get_video):
            response = self.client.post(
                "/ap/inbox",
                json.dumps(account_announce_payload),
                content_type="application/json",
                **self.headers,
            )

        # TODO: assert ExternalVideo is created

        with open(
            "pod/activitypub/tests/fixtures/video_creation_channel_announce.json"
        ) as fd:
            channel_announce_payload = json.load(fd)

        with httmock.HTTMock(self.mock_get_channel, self.mock_get_video):
            response = self.client.post(
                "/ap/inbox",
                json.dumps(channel_announce_payload),
                content_type="application/json",
                **self.headers,
            )

        # TODO: assert ExternalVideo is added to the channel

    def test_video_view(self):
        """Test that View activities are ignored"""

        with open("pod/activitypub/tests/fixtures/video_view.json") as fd:
            payload = json.load(fd)

        self.client.post(
            "/ap/inbox",
            json.dumps(payload),
            content_type="application/json",
            **self.headers,
        )
