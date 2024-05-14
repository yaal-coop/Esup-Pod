import json
from . import ActivityPubTestCase
from pod.activitypub.serialization import ap_video_to_external_video


class VideoDiscoveryTest(ActivityPubTestCase):
    def test_video_deserialization(self):
        """Test ExternalVideo creation from a AP Video."""
        with open("pod/activitypub/tests/fixtures/peertube_video.json") as fd:
            payload = json.load(fd)

        video = ap_video_to_external_video(payload)

        assert (
            video.ap_id
            == "http://peertube.localhost:9000/videos/watch/dc6d7e53-9acc-45ca-ac3e-adac05c4bb77"
        )
