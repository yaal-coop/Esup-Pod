import os
from Crypto.PublicKey import RSA

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

USE_PODFILE = True
EMAIL_ON_ENCODING_COMPLETION = False
SECRET_KEY = "A_CHANGER"
DEBUG = True
ES_VERSION = 8
ES_URL = ['http://elasticsearch.localhost:9200/']


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis.localhost:6379/3",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "pod"
    },
    "select2": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis.localhost:6379/2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}
SESSION_ENGINE = "redis_sessions.session"
SESSION_REDIS = {
    "host": "redis.localhost",
    "port": 6379,
    "db": 4,
    "prefix": "session",
    "socket_timeout": 1,
    "retry_on_timeout": False,
}

MIGRATION_MODULES = {'flatpages': 'pod.db_migrations'}

ACTIVITYPUB_CELERY_BROKER_URL = "redis://redis.localhost:6379/5"
USE_ACTIVITYPUB = True

# Dynamically create AP public keys if needed
if not os.path.exists("pod/activitypub/ap-pod-b.key"):
    activitypub_key = RSA.generate(2048)
    with open("pod/activitypub/ap-pod-b.key", "w") as fd:
        fd.write(activitypub_key.export_key().decode())

    with open("pod/activitypub/ap-pod-b.pub", "w") as fd:
        fd.write(activitypub_key.publickey().export_key().decode())


with open("pod/activitypub/ap-pod-b.key") as fd:
    ACTIVITYPUB_PRIVATE_KEY = fd.read()

with open("pod/activitypub/ap-pod-b.pub") as fd:
    ACTIVITYPUB_PUBLIC_KEY = fd.read()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "db-pod-b.sqlite3"),
    }
}

from pod.settings import *
