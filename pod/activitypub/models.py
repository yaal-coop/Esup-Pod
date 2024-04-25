from django.db import models
from django.utils.translation import ugettext_lazy as _

from pod.video.models import Video


class Follower(models.Model):
    actor = models.CharField(
        _("Actor"),
        max_length=255,
        help_text=_("Actor who initiated the Follow activity"),
    )


class Following(models.Model):
    object = models.CharField(
        _("Object"),
        max_length=255,
        help_text=_("Followed object"),
    )


class ExternalVideo(Video):
    source_instance = models.ForeignKey(
        Following,
        on_delete=models.CASCADE,
        verbose_name=_("Source instance"),
        help_text=_("Video origin instance"),
    )
    stream = models.CharField(
        _("Stream url"),
        max_length=255,
        help_text=_("External instance video stream"),
    )
