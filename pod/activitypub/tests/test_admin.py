from . import ActivityPubTestCase
import httmock
from pod.activitypub.models import Following


class AdminActivityPubTestCase(ActivityPubTestCase):
    def test_send_federation_request(self):
        """Nominal case test for the admin 'send_federation_request' action."""

        following = Following.objects.create(
            object="http://peertube.test", status=Following.Status.NONE
        )

        with httmock.HTTMock(self.mock_inbox):
            response = self.client.post(
                "/admin/activitypub/following",
                {
                    "action": "send_federation_request",
                    "_selected_action": str(following.id),
                },
                follow=True,
            )
        self.assertEqual(response.status_code, 200)

        following.refresh_from_db()
        self.assertEqual(following.status, Following.Status.REQUESTED)
