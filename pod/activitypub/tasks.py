from celery import Celery
from django.conf import settings

activitypub_app = Celery("activitypub", broker=settings.ACTIVITYPUB_CELERY_BROKER_URL)
activitypub_app.conf.task_routes = {"pod.activitypub.tasks.*": {"queue": "activitypub"}}


@activitypub_app.task(bind=True)
def task_follow(self, following_id):
    from .network import follow

    return follow(following_id)


@activitypub_app.task(bind=True)
def task_index_videos(self, following_id):
    from .network import index_videos

    return index_videos(following_id)
