import os
from Crypto.PublicKey import RSA

ACTIVITYPUB_CELERY_BROKER_URL = "redis://redis.localhost:6379/5"
USE_ACTIVITYPUB = True

# Dynamically create AP public keys if needed
if not os.path.exists("pod/activitypub/ap.key"):
    activitypub_key = RSA.generate(2048)
    with open("pod/activitypub/ap.key", "w") as fd:
        fd.write(activitypub_key.export_key().decode())

    with open("pod/activitypub/ap.pub", "w") as fd:
        fd.write(activitypub_key.publickey().export_key().decode())


with open("pod/activitypub/ap.key") as fd:
    ACTIVITYPUB_PRIVATE_KEY = fd.read()

with open("pod/activitypub/ap.pub") as fd:
    ACTIVITYPUB_PUBLIC_KEY = fd.read()
