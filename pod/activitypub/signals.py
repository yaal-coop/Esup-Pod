"""Signal callbacks.

Signals are triggered after commits and not just after .save() or .delete() calls,
so we are sure that when we trigger the celery tasks, the database is really up to date,
and that any federated instance will be able to read the updated data.

Without this, celery tasks could have been triggered BEFORE the data was actually written to the database,
leading to old data being broadcasted."""

from django.db import transaction
from .tasks import (
    task_broadcast_local_video_creation,
    task_broadcast_local_video_deletion,
    task_broadcast_local_video_update,
)


def on_video_save(instance, created, **kwargs):
    def trigger_save_task():
        if created:
            task_broadcast_local_video_creation.delay(instance.id)

        else:
            task_broadcast_local_video_update.delay(instance.id)

    transaction.on_commit(trigger_save_task)


def on_video_delete(instance, **kwargs):
    def trigger_delete_task():
        task_broadcast_local_video_deletion.delay(instance.id)

    transaction.on_commit(trigger_delete_task)
