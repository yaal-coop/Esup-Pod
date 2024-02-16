from django.test import TestCase
from unittest import mock
from pod.activitypub.models import Following
from pod.activitypub.models import Follower


class ActivityPubViewTest(TestCase):
    """ActivityPub test case."""

    maxDiff = None
    fixtures = ["initial_data.json"]
    headers = {
        "HTTP_ACCEPT": "application/activity+json, application/ld+json",
    }

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
                    "href": "http://testserver/account/peertube",
                },
            ],
        }
        self.assertJSONEqual(response.content, expected)

    def test_instance_account_view(self):
        """Test for instance_account view."""
        response = self.client.get("/account/peertube", **self.headers)
        self.assertEqual(response.status_code, 200)
        expected = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
                {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
            ],
            "type": "Application",
            "id": "http://testserver/account/peertube",
            "following": "http://testserver/account/peertube/following",
            "followers": "http://testserver/account/peertube/followers",
            "inbox": "http://testserver/account/peertube/inbox",
            "outbox": "http://testserver/account/peertube/outbox",
            "url": "http://testserver/account/peertube",
            "name": "peertube",
            "publicKey": {
                "id": "http://testserver/account/peertube#main-key",
                "owner": "http://testserver/account/peertube",
                "publicKeyPem": mock.ANY,
            },
        }
        self.assertJSONEqual(response.content, expected)

    def test_accept_follows(self):
        self.assertEqual(Follower.objects.all().count(), 0)

        payload = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
                {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
            ],
            "type": "Follow",
            "id": "http://localhost:9000/accounts/peertube/follows/4",
            "actor": "http://localhost:9000/accounts/peertube",
            "object": "http://localhost:5000/.well-known/peertube",
            "signature": {
                "type": "RsaSignature2017",
                "creator": "http://localhost:9000/accounts/peertube",
                "created": "2024-02-15T09:54:14.188Z",
                "signatureValue": "Cnh40KpjP7p0o1MBiTHkEHY4vXQnBOTVEkONurdlpGAvV8OAQgOCACQD8cHPE9E5W00+X7SrbzP76PTUpwCbRbxFXHiDq+9Y1dTQs5rLkDS2XSgu75XW++V95glIUUP1jxp7MfqMllxwPYjlVcM6x8jFYNVst2/QTm+Jj0IocSs=",
            },
        }
        response = self.client.post("/account/peertube/inbox", payload, **self.headers)

        expected = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
                {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
            ],
            "id": "http://testserver/account/peertube/followers/1",
            "type": "Accept",
            "actor": "http://localhost:9000/accounts/peertube",
            "object": "http://localhost:5000/.well-known/peertube",
        }
        self.assertJSONEqual(response.content, expected)

        follower = Follower.objects.get()
        assert follower.actor == "http://localhost:9000/accounts/peertube"
