import base64
import email.utils
import hashlib
import json
import random
import uuid
from collections import namedtuple
from urllib.parse import urlencode, urlparse, urlunparse

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse

URLComponents = namedtuple(
    typename="URLComponents",
    field_names=["scheme", "netloc", "url", "path", "query", "fragment"],
)


def make_url(scheme=None, netloc=None, params=None, path="", url="", fragment=""):
    if scheme is None:
        scheme = "https" if getattr(settings, "SECURE_SSL_REDIRECT") else "http"

    if netloc is None:
        current_site = Site.objects.get_current()
        netloc = current_site.domain

    if params is not None:
        tuples = [(key, value) for key, values in params.items() for value in values]
        params = urlencode(tuples, safe=":")

    return urlunparse(
        URLComponents(
            scheme=scheme,
            netloc=netloc,
            query=params or {},
            url=url,
            path=path,
            fragment=fragment,
        )
    )


def ap_url(suffix=""):
    """Returns a full URL to be used in activitypub context."""
    return make_url(url=suffix)


def signed_payload_headers(payload, url):
    """Signs JSON-LD payload according to the 'Signing HTTP Messages' RFC draft.
    This brings compatibility with peertube (and mastodon for instance).

    More information here:
        - https://datatracker.ietf.org/doc/html/draft-cavage-http-signatures-12
        - https://framacolibri.org/t/rfc9421-replaces-the-signing-http-messages-draft/20911/2
    """
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


def stable_uuid(seed, version=None):
    """Always returns the same UUID given the same input string."""
    full_seed = str(seed) + settings.SECRET_KEY
    m = hashlib.md5()
    m.update(full_seed.encode("utf-8"))
    return uuid.UUID(m.hexdigest(), version=version)


def make_magnet_url(video, mp4):
    uuid = stable_uuid(video.title, version=4)
    fake_hash = "".join(
        random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(40)
    )
    payload = {
        "dn": [video.slug],
        "tr": [
            make_url(url="/tracker/announce"),
            make_url(scheme="ws", url="/tracker/announce"),
        ],
        "ws": [
            make_url(
                url=f"/static/streaming-playlists/hls/{uuid}-{mp4.height}-fragmented.mp4"
            )
        ],
        "xs": [
            make_url(url=f"/lazy-static/torrents/{uuid}-{mp4.height}-hls.torrent")
        ],
        "xt": [f"urn:btih:{fake_hash}"],
    }
    return make_url(
        scheme="magnet",
        netloc="",
        params=payload,
    )
