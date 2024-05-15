"""Signal callbacks"""

from .tasks import task_broadcast_local_video_creation
from .tasks import task_broadcast_local_video_update
from .tasks import task_broadcast_local_video_deletion


def on_video_save(instance, created, **kwargs):
    if created:
        task_broadcast_local_video_creation.delay(instance.id)

    else:
        task_broadcast_local_video_update.delay(instance.id)


def on_video_delete(instance, **kwargs):
    task_broadcast_local_video_deletion.delay(instance.id)
