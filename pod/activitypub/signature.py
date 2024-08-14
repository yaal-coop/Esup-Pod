import base64
from pyld import jsonld
import datetime
import email.utils
import json
from urllib.parse import urlparse

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from django.conf import settings
from django.urls import reverse


def payload_hash(payload):
    payload_json = json.dumps(payload) if isinstance(payload, dict) else payload
    payload_hash = SHA256.new(payload_json.encode("utf-8"))
    digest = payload_hash.digest()
    return digest


def base64_signature(private_key, string):
    to_be_signed_str_bytes = bytes(string, "utf-8")
    to_be_signed_str_hash = SHA256.new(bytes(to_be_signed_str_bytes))
    sig = pkcs1_15.new(private_key).sign(to_be_signed_str_hash)
    sig_base64 = base64.b64encode(sig).decode()
    return sig_base64


def payload_normalize(payload):
    return jsonld.normalize(
        payload, {"algorithm": "URDNA2015", "format": "application/n-quads"}
    )


def signed_payload_headers(payload, url):
    """Sign JSON-LD payload according to the 'Signing HTTP Messages' RFC draft.
    This brings compatibility with peertube (and mastodon for instance).

    More information here:
        - https://datatracker.ietf.org/doc/html/draft-cavage-http-signatures-12
        - https://framacolibri.org/t/rfc9421-replaces-the-signing-http-messages-draft/20911/2
    """
    from .utils import ap_url

    date = email.utils.formatdate(usegmt=True)
    url = urlparse(url)

    private_key = RSA.import_key(settings.ACTIVITYPUB_PRIVATE_KEY)
    payload_hash_raw = payload_hash(payload)
    payload_hash_base64 = base64.b64encode(payload_hash_raw).decode()

    to_be_signed_str = (
        f"(request-target): post {url.path}\n"
        f"host: {url.netloc}\n"
        f"date: {date}\n"
        f"digest: SHA-256={payload_hash_base64}"
    )
    sig_base64 = base64_signature(private_key, to_be_signed_str)

    public_key_url = ap_url(reverse("activitypub:account")) + "#main-key"
    signature_header = f'keyId="{public_key_url}",algorithm="rsa-sha256",headers="(request-target) host date digest",signature="{sig_base64}"'
    request_headers = {
        "host": url.netloc,
        "date": date,
        "digest": f"SHA-256={payload_hash_base64}",
        "content-type": "application/activity+json",
        "signature": signature_header,
    }
    return request_headers


def signature_payload(payload, url):
    """Sign JSON-LD payload according to the 'Linked Data Signatures 1.0' RFC draft.
    This brings compatibility with peertube (and mastodon for instance).

    More information here:
        - https://web.archive.org/web/20170717200644/https://w3c-dvcg.github.io/ld-signatures/
        - https://docs.joinmastodon.org/spec/security/#ld
    """
    private_key = RSA.import_key(settings.ACTIVITYPUB_PRIVATE_KEY)

    signature = {
        "type": "RsaSignature2017",
        "creator": payload["actor"],
        "created": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
    }
    options_payload = {
        "@context": [
            "https://w3id.org/security/v1",
            {"RsaSignature2017": "https://w3id.org/security#RsaSignature2017"},
        ],
        "creator": signature["creator"],
        "created": signature["created"],
    }
    options_normalized = payload_normalize(options_payload)
    options_hash = payload_hash(options_normalized)

    document_normalized = payload_normalize(payload)
    document_hash = payload_hash(document_normalized)

    to_sign = options_hash.hex() + document_hash.hex()
    signature["signatureValue"] = base64_signature(private_key, to_sign)

    return signature
