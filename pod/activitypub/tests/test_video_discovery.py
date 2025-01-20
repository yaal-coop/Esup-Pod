import json


from . import ActivityPubTestCase

from pod.activitypub.serialization.video import ap_video_to_external_video


class VideoDiscoveryTest(ActivityPubTestCase):
    def test_video_deserialization(self):
        """Test ExternalVideo creation from a AP Video."""
        with open("pod/activitypub/tests/fixtures/peertube_video.json") as fd:
            payload = json.load(fd)

        video = ap_video_to_external_video(payload, source_instance=self.peertube_test_following)

        assert (
            video.ap_id
            == "http://peertube.test/videos/watch/717c9d87-c912-4943-a392-49fadf2f235d"
        )
        assert len(video.videos) == 8

        # TODO: implement the rest of the test
