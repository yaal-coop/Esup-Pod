from django.test import TestCase


class ActivityPubViewTest(TestCase):
    """ActivityPub test case."""

    fixtures = ["initial_data.json"]

    def test_webfinger_view(self):
        """Test for webfinger view."""
        account = "acct:instance@instance_domain"
        response = self.client.get("/.well-known/webfinger", {"resource": account})
        self.assertEqual(response.status_code, 200)
        expected_json = {
            "subject": account,
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": "localhost:9090/accounts/instance_name",  # TODO: get the app domain
                },
            ]
        }
        self.assertJSONEqual(
            response.content,
            expected_json,
        )
        print(
            " ---> test_webfinger_view " +
            "of ActivityPubViewTest: OK!"
        )

    def test_instance_account_view(self):
        """Test for instance_account view."""
        headers = {
            "HTTP_ACCEPT": "application/activity+json, application/ld+json",
        }
        response = self.client.get("/accounts/instance_name", **headers)
        self.assertEqual(response.status_code, 200)
        expected_json = {
            "@context": [
                "https://www.w3.org/ns/activitystreams",
                "https://w3id.org/security/v1",
                {
                    "RsaSignature2017": "https://w3id.org/security#RsaSignature2017"
                },
            ],
            "type": "Application",
            "id": "localhost:9090/accounts/instance_name",  # TODO: get the app domain
            "following": "localhost:9090/accounts/instance_name/following",
            "followers": "localhost:9090/accounts/instance_name/followers",
            "inbox": "localhost:9090/accounts/instance_name/inbox",
            "outbox": "localhost:9090/accounts/instance_name/outbox",
            "preferredUsername": "instance_name",
            "url": "localhost:9090/accounts/instance_name",
            "name": "instance_name",
            "publicKey": {
                "id": "localhost:9090/accounts/instance_name#main-key",
                "owner": "localhost:9090/accounts/instance_name",
                "publicKeyPem": "thisisapublickey"  # TODO: Generate key pair
            },
            "published": "2018-07-01T11:59:04.556Z",
        }
        self.assertJSONEqual(
            response.content,
            expected_json,
        )
        print(
            " ---> test_instance_account_view " +
            "of ActivityPubViewTest: OK!"
        )
