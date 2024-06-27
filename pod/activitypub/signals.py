"""Signal callbacks."""

from django.db import transaction
from .tasks import (
    task_broadcast_local_video_creation,
    task_broadcast_local_video_deletion,
    task_broadcast_local_video_update,
)


def on_video_save(instance, sender, **kwargs):
    """Celery tasks are triggered after commits and not just after .save() calls,
    so we are sure the database is really up to date at the moment we send data accross the network,
    and that any federated instance will be able to read the updated data.

    Without this, celery tasks could have been triggered BEFORE the data was actually written to the database,
    leading to old data being broadcasted.
    """

    def is_new_and_visible(previous_state, current_state):
        return (
            current_state
            and not previous_state
            and not current_state.is_draft
            and not current_state.encoding_in_progress
            and not current_state.is_restricted
            and not current_state.password
        )

    def has_changed_to_visible(previous_state, current_state):
        return (
            current_state
            and previous_state
            and previous_state.is_draft
            and not current_state.is_draft
            and not current_state.encoding_in_progress
            and not current_state.is_restricted
            and not current_state.password
        )

    def has_changed_to_invisible(previous_state, current_state):
        return (
            current_state
            and previous_state
            and (
                (not previous_state.is_draft and current_state.is_draft)
                or (not previous_state.is_restricted and current_state.is_restricted)
                or (not previous_state.password and current_state.password)
            )
        )

    def is_still_visible(previous_state, current_state):
        return (
            current_state
            and previous_state
            and not previous_state.is_draft
            and not current_state.is_draft
            and not current_state.encoding_in_progress
            and not current_state.is_restricted
            and not current_state.password
        )

    def trigger_save_task():
        try:
            previous_video = sender.objects.get(id=instance.id)
        except sender.DoesNotExist:
            previous_video = None

        if is_new_and_visible(
            previous_state=previous_video, current_state=instance
        ) or has_changed_to_visible(
            previous_state=previous_video, current_state=instance
        ):
            task_broadcast_local_video_creation.delay(instance.id)

        elif has_changed_to_invisible(
            previous_state=previous_video, current_state=instance
        ):
            task_broadcast_local_video_deletion.delay(
                video_id=instance.id, owner_username=instance.owner.username
            )
        elif is_still_visible(previous_state=previous_video, current_state=instance):
            task_broadcast_local_video_update.delay(instance.id)

    transaction.on_commit(trigger_save_task)


def on_video_delete(instance, **kwargs):
    """At the moment the celery task will be triggered,
    the video MAY already have been deleted.
    Thus, we avoid to pass a Video id to read in the database,
    and we directly pass pertinent data."""

    task_broadcast_local_video_deletion.delay(
        video_id=instance.id, owner_username=instance.owner.username
    )
