import base64
import email.utils
import json
from urllib.parse import urlparse

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse


def ap_url(suffix=""):
    scheme = "https" if getattr(settings, "SECURE_SSL_REDIRECT") else "http"
    current_site = Site.objects.get_current()
    return f"{scheme}://{current_site.domain}{suffix}"


def signed_payload_headers(payload, url):
    date = email.utils.formatdate(usegmt=True)
    private_key = RSA.import_key(settings.ACTIVITYPUB_PRIVATE_KEY)
    payload_json = json.dumps(payload)
    payload_hash = SHA256.new(payload_json.encode("utf-8"))
    payload_hash_base64 = base64.b64encode(payload_hash.digest()).decode()

    url = urlparse(url)
    to_be_signed_str = (
        f"(request-target): post {url.path}\n"
        f"host: {url.netloc}\n"
        f"date: {date}\n"
        f"digest: SHA-256={payload_hash_base64}"
    )
    to_be_signed_str_bytes = bytes(to_be_signed_str, "utf-8")
    to_be_signed_str_hash = SHA256.new(bytes(to_be_signed_str_bytes))
    sig = pkcs1_15.new(private_key).sign(to_be_signed_str_hash)

    public_key_url = ap_url(reverse("activitypub:account")) + "#main-key"
    sig_base64 = base64.b64encode(sig).decode()
    signature_header = f'keyId="{public_key_url}",algorithm="rsa-sha256",headers="(request-target) host date digest",signature="{sig_base64}"'
    request_headers = {
        "host": url.netloc,
        "date": date,
        "digest": f"SHA-256={payload_hash_base64}",
        "content-type": "application/activity+json",
        "signature": signature_header,
    }
    return request_headers
