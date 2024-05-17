# ActivityPub implementation

Pod implements a minimal set of ActivityPub that allows video sharing between Pod instances.
The ActivityPub implementation is also compatible with Peertube.

## Federation

Here is what happens when two instances, say *Node A* and *Node B* (being Pod or Peertube) federate with each other, in a one way federation.

### Federation

- An administrator asks for Node A to federate with Node B
- Node A reaches the [NodeInfo](https://github.com/jhass/nodeinfo/blob/main/PROTOCOL.md) endpoint (`/.well-known/nodeinfo`) on Node B and discover the root application endpoint URL.
- Node A reaches the root application endpoint (for Pod this is `/ap/`) and get the `inbox` URL.
- Node A sends a `Create` activity for a `Follow` object on the Node B root application `inbox`.
- Node B reads the Node A root application endpoint URL in the `Follow` objects, reaches this endpoint and get the Node A root application `inbox` URL.
- Node B creates a `Follower` objects and stores it locally
- Node B sends a `Accept` activity for the `Follower` object on Node A root application enpdoint.

### Video discovery

- Node A reaches the Node B root application `outbox`.
- Node B browse the pages of the `outbox` and look for announces about `Videos`
- Node B reaches the `Video` endpoints and store locally the information about the videos.

### Video creation and update sharing

#### Creation

- A user of Node B publishes a `Video`
- Node B sends a `Announce` activity on the `inbox` of all its `Followers`, including Node A with the ID of the new video.
- Node A reads the information about the new `Video` on Node B video endpoint.

#### Edition

- A user of Node B edits a `Video`
- Node B sends a `Update` activity on the `inbox` of all its `Followers`, including Node A with the ID of the new video, containing the details of the `Video`.

#### Deletion

- A user of Node B deletes a `Video`
- Node B sends a `Delete` activity on the `inbox` of all its `Followers`, including Node A with the ID of the new video.

## Implementation

The ActivityPub implementation tries to replicate the network messages of Peertube.
There may be things that could have been done differently while still following the ActivityPub specs, but changing the network exchanges would require checking if the Peertube compatibility is not broken.
This is due to Peertube having a few undocumented behaviors that are not exactly part of the AP specs.

## Limitations

- Peertube instance will only be able to federate with a Pod instance if the video thumbnails are in JPG format.
  png thumbnails are not supported at the moment (but that may come in the future).
  [More details here](https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215).
- The pod default `Site` must be exactly the URL accessed for ActivityPub endpoint to work as expected.
  This is notably due to the fact some absolute URLs are built within celery tasks, with no possibility to guess a request domain.

## Configuration

A RSA keypair is needed for ActivityPub to work, and passed as
`ACTIVITYPUB_PUBLIC_KEY` and `ACTIVITYPUB_PRIVATE_KEY` configuration settings.
They can be generated with python:

```python
from Crypto.PublicKey import RSA

activitypub_key = RSA.generate(2048)

# Generate the private key
# Add the content of this command in 'pod/custom/settings_local.py'
# in a variable named ACTIVITYPUB_PRIVATE_KEY
print(activitypub_key.export_key().decode())

# Generate the public key
# Add the content of this command in 'pod/custom/settings_local.py'
# in a variable named ACTIVITYPUB_PUBLIC_KEY
print(activitypub_key.publickey().export_key().decode())
```

The federation also needs celery to be configured with `ACTIVITYPUB_CELERY_BROKER_URL`.

Here is a sample working activitypub `pod/custom/settings_local.py`:

```python
ACTIVITYPUB_CELERY_BROKER_URL = "redis://redis:6379/5"

ACTIVITYPUB_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAxrwptdaacIRLFrYKvlBvLCM0ZziajLPRsf7C4FcSh6pGcRif
Q0dmgfy5I3exRmmbtvmNo5jAE2T8fQo4m2qPW9MZ7N9RDxVJbqFZ0FtJKG+bXB8o
JMVFutCBsL9R3Zoaqs16x+DnWajX38xQ+hl4ybgj7wojjRLauBMnAUQqg9cf0v5u
++4kLi9MVs5dzS4npc5HgTJIOwkryH27NUEz1vIohuuLL/LEffBfb07lw4pNePkW
SD1X0tj/9yLONjTEFG/smr1Ita1l/5/GbchmKtd49xubqM0pp9cJd8pBl0nT7DpY
hT+6RDb8FUDGKKeBLVAbHgdH0KTtd3IMzdJSQQIDAQABAoIBABkLDAyEgwiruxSd
EwSBeUjsFMXvHZaecE3IR0Fi54xd+it1SVh+jl3R/XiJNDclxsALeXxEmuu2vZR6
LcDz8CXHl8xAJeRLL+o3fexiHHlyevbkXDgp/cv5S2Z87XGJ4lNkulSmtDCZtL5Y
blndzNlKkYilU+6KkjJBA5jGwL7FK6fytNG5hP2t7Sknt+drN+QwEE89FFXIJqvW
QMl0UAHotuQ/PH0thHz2kScfVlVr6BRit+RgNbj9rU3WLtN5oQqiyD044NaqigWX
wJSzPnbJmed5xc82+vxI0dlLxZa9cAQok/IJnCsGwJqpHfmiL6Cm2oEOyP27fM7P
N0+uStMCgYEA1XK/pLpPYhdg4FXU0YVsVWC4ZvzN9KuPqB3EVmSlSDDSbRm9ij7c
Noa5oibG1NqQidb7HBARBC8546v39vk+XnUgl04tiJV7/jEz3jRa8Br9CvrNdkYR
XGT3Bwd9SPzMm6Jvv1kW4HSPrAVhQWTP4U7dxN0b5a7/R/3kDqQcrbsCgYEA7lqH
xHY2wICDaSo4zF17sYXjkRcIedkEyptl2XCWqt730/KH3FHhWzDic4RP6fPdNvQB
KWFpzxV7TFstrA1xgabw4pLwjncJ6GIqrmIChvh2hBXD0o71k5iXcC9PEStX+58Y
kk2DGKAG7FPUhoYueUvnBoNXCgSeJL6yHiAcwjMCgYEAnWZo/EiHkYY74jJpJbiG
Es+oLAnwtqRs40RQLIU7fOjDw8BfjTqdmXfwHCsMJJqoS31E34TZh4Rr5ABEctOJ
so4c4na8DSRusxwFa66gAL9mKlqYeMditgeeQoi7Ur9ZAsveK/S+cfaCnA+7kEWP
Jk7KKwoCMHXDuor3SfSrUVECgYAaaGNUa/iC+XoVw7zJP649q+TbpV6mCVpTjEYL
gkLfKZbxn5RX36aFMPRV8hnchM1EkmIykH1lmS6w9gUoY9DomXNk1vzZ++xYF9A8
w9Ud2RdgaPzqLjadJLHalxM+hrvXv/e79eSJbOl3c44/XUx22eb9vL1++aX/0jTv
y4UEKwKBgGHCQ43SI74OdLYTGt0QatZ6sqyMls2oXyCrn22iIe8hzdjX7lxdDtcK
N3OivsoU3pCD0KMGvULhnP0GkD4zCeIXF2ZvBdL104NPLxp+1CcwrYKiJCI+O5Xa
AX6/PrSdr5U1r0YK4h24wMQt4HJwdYI6KJxGRHzf3Y3ivVQKX0st
-----END RSA PRIVATE KEY-----"""

ACTIVITYPUB_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxrwptdaacIRLFrYKvlBv
LCM0ZziajLPRsf7C4FcSh6pGcRifQ0dmgfy5I3exRmmbtvmNo5jAE2T8fQo4m2qP
W9MZ7N9RDxVJbqFZ0FtJKG+bXB8oJMVFutCBsL9R3Zoaqs16x+DnWajX38xQ+hl4
ybgj7wojjRLauBMnAUQqg9cf0v5u++4kLi9MVs5dzS4npc5HgTJIOwkryH27NUEz
1vIohuuLL/LEffBfb07lw4pNePkWSD1X0tj/9yLONjTEFG/smr1Ita1l/5/Gbchm
Ktd49xubqM0pp9cJd8pBl0nT7DpYhT+6RDb8FUDGKKeBLVAbHgdH0KTtd3IMzdJS
QQIDAQAB
-----END PUBLIC KEY-----"""
```

## Development

The `DOCKER_ENV` environment var should be set to `full` so a peertube instance and a ActivityPub celery worker are launched.

The pod `Site` must be set on `pod.localhost:9090` in the [admin pannel](http://pod.localhost:9090/admin/sites/site/1/change/) (instead of `localhost:9090`).

Then peertube is available at http://peertube.localhost:9000, and the address to be used for pod is http://pod.localhost:9090

### Federate Peertube with Pod

- Sign in with the `root` account
- Go to [Main menu > Administration > Federation](http://peertube.localhost:9000/admin/follows/following-list) > Follow
- Open the *Follow* modal and type `pod.localhost:9090`

### Federate Pod with Peertube

- Sign in with `admin`
- Go to the [Administration pannel > Followings](http://pod.localhost:9090/admin/activitypub/following/) > Add following
- Type `http://peertube.localhost:9000` in *Object* and save
- On the [Followings list](http://pod.localhost:9090/admin/activitypub/following/) select the new object, and select `Send the federation request` in the action list, refresh.
- If the status is *Following request accepted* then select the object again, and choose `Reindex instance videos` in the action list.
