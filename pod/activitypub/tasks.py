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
activitypub_app.conf.task_eager_propagates = CELERY_TASK_ALWAYS_EAGER


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


@activitypub_app.task(bind=True)
def task_external_video_update(self, video):
    from .network import external_video_update

    return external_video_update(video)


@activitypub_app.task(bind=True)
def task_external_video_deletion(self, object_id):
    from .network import external_video_deletion

    return external_video_deletion(object_id)


@activitypub_app.task(bind=True)
def task_broadcast_local_video_creation(self, video_id):
    from .network import broadcast_local_video_creation

    return broadcast_local_video_creation(video_id)


@activitypub_app.task(bind=True)
def task_broadcast_local_video_update(self, video_id):
    from .network import broadcast_local_video_update

    return broadcast_local_video_update(video_id)


@activitypub_app.task(bind=True)
def task_broadcast_local_video_deletion(self, video_id):
    from .network import broadcast_local_video_deletion

    return broadcast_local_video_deletion(video_id)
