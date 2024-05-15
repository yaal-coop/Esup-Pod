import json
import httmock
from unittest import mock

from pod.activitypub.models import Follower
from . import ActivityPubTestCase


class ActivityPubViewTest(ActivityPubTestCase):
    def test_webfinger_view(self):
        """Test for webfinger view."""
        account = "acct:instance@instance_domain"
        response = self.client.get("/.well-known/webfinger", {"resource": account})
        self.assertEqual(response.status_code, 200)

        expected = {
            "subject": account,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": "http://localhost:9090/ap",
                },
            ],
        }
        self.assertJSONEqual(response.content, expected)

    def test_instance_account_view(self):
        """Test for instance_account view."""
        response = self.client.get("/ap", **self.headers)
        self.assertEqual(response.status_code, 200)
        expected = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
                {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
            ],
            "type": "Application",
            "id": "http://localhost:9090/ap",
            "following": "http://localhost:9090/ap/following",
            "followers": "http://localhost:9090/ap/followers",
            "inbox": "http://localhost:9090/ap/inbox",
            "outbox": "http://localhost:9090/ap/outbox",
            "url": "http://localhost:9090/ap",
            "name": "pod",
            "preferredUsername": "pod",
            'endpoints': {'sharedInbox': 'http://localhost:9090/ap/inbox'},
            "publicKey": {
                "id": "http://localhost:9090/ap#main-key",
                "owner": "http://localhost:9090/ap",
                "publicKeyPem": mock.ANY,
            },
        }
        self.assertJSONEqual(response.content, expected)

    def test_follow_accept(self):
        """Test that a Follow request returns a 204, and post an Accept response in the follower's inbox."""
        self.assertEqual(Follower.objects.all().count(), 0)

        @httmock.all_requests
        def follower_ap_url(url, request):
            return httmock.response(
                200,
                {
                    "@context": [
                        "https://www.w3.org/ns/activitystreams",
                        "https://w3id.org/security/v1",
                        {
                            "RsaSignature2017": "https://w3id.org/security#RsaSignature2017"
                        },
                    ],
                    "type": "Application",
                    "id": "http://peertube.test/accounts/peertube",
                    "following": "http://peertube.test/accounts/peertube/following",
                    "followers": "http://peertube.test/accounts/peertube/followers",
                    "inbox": "http://peertube.test/accounts/peertube/inbox",
                    "outbox": "http://peertube.test/accounts/peertube/outbox",
                    "url": "http://peertube.test/accounts/peertube",
                    "name": "pod",
                    "preferredUsername": "pod",
                    "publicKey": {
                        "id": "http://peertube.test/accounts/peertube#main-key",
                        "owner": "http://peertube.test/accounts/peertube",
                        "publicKeyPem": "foobar",
                    },
                },
            )

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
                {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
            ],
            "type": "Follow",
            "id": "http://peertube.test/accounts/peertube/follows/4",
            "actor": "http://peertube.test/accounts/peertube",
            "object": "http://localhost:9090/.well-known/peertube",
            "signature": {
                "type": "RsaSignature2017",
                "creator": "http://peertube.test/accounts/peertube",
                "created": "2024-02-15T09:54:14.188Z",
                "signatureValue": "Cnh40KpjP7p0o1MBiTHkEHY4vXQnBOTVEkONurdlpGAvV8OAQgOCACQD8cHPE9E5W00+X7SrbzP76PTUpwCbRbxFXHiDq+9Y1dTQs5rLkDS2XSgu75XW++V95glIUUP1jxp7MfqMllxwPYjlVcM6x8jFYNVst2/QTm+Jj0IocSs=",
            },
        }

        with httmock.HTTMock(follower_ap_url), mock.patch("requests.post") as post:
            response = self.client.post(
                "/ap/inbox",
                json.dumps(payload),
                content_type="application/json",
                **self.headers,
            )
            self.assertEqual(response.status_code, 204)

            expected = {
                "@context": [
                    "https://www.w3.org/ns/activitystreams",
                    "https://w3id.org/security/v1",
                    {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
                ],
                "id": "http://localhost:9090/accepts/follows/1",
                "type": "Accept",
                "actor": "http://localhost:9090/.well-known/peertube",
                "object": {
                    "type": "Follow",
                    "id": "http://peertube.test/accounts/peertube/follows/4",
                    "actor": "http://peertube.test/accounts/peertube",
                    "object": "http://localhost:9090/.well-known/peertube",
                },
            }
            inbox_url = "http://peertube.test/accounts/peertube/inbox"
            post.assert_called_with(inbox_url, json=expected, headers=mock.ANY)

        follower = Follower.objects.get()
        assert follower.actor == "http://peertube.test/accounts/peertube"
