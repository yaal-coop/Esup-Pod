"""Celery tasks configuration."""

from django.conf import settings

try:
    from ..custom import settings_local
except ImportError:
    from .. import settings as settings_local

from celery import Celery

ACTIVITYPUB_CELERY_BROKER_URL = getattr(
    settings_local, "ACTIVITYPUB_CELERY_BROKER_URL", ""
)
CELERY_TASK_ALWAYS_EAGER = getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)

activitypub_app = Celery("activitypub", broker=ACTIVITYPUB_CELERY_BROKER_URL)
activitypub_app.conf.task_routes = {"pod.activitypub.tasks.*": {"queue": "activitypub"}}
activitypub_app.conf.task_always_eager = CELERY_TASK_ALWAYS_EAGER


@activitypub_app.task(bind=True)
def task_follow(self, following_id):
    from .network import follow

    return follow(following_id)


@activitypub_app.task(bind=True)
def task_index_videos(self, following_id):
    from .network import index_videos

    return index_videos(following_id)


@activitypub_app.task(bind=True)
def task_send_accept_request(self, follow_actor, follow_object, follow_id):
    from .network import send_accept_request

    return send_accept_request(follow_actor, follow_object, follow_id)


@activitypub_app.task(bind=True)
def task_read_announce(self, actor, object_id):
    from .network import read_announce

    return read_announce(actor, object_id)
