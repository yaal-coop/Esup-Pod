"""Celery tasks configuration."""

try:
    from ..custom import settings_local
except ImportError:
    from .. import settings as settings_local

from celery import Celery

ACTIVITYPUB_CELERY_BROKER_URL = getattr(
    settings_local, "ACTIVITYPUB_CELERY_BROKER_URL", ""
)
activitypub_app = Celery("activitypub", broker=ACTIVITYPUB_CELERY_BROKER_URL)
activitypub_app.conf.task_routes = {"pod.activitypub.tasks.*": {"queue": "activitypub"}}


@activitypub_app.task(bind=True)
def task_follow(self, following_id):
    from .network import follow

    return follow(following_id)


@activitypub_app.task(bind=True)
def task_index_videos(self, following_id):
    from .network import index_videos

    return index_videos(following_id)
