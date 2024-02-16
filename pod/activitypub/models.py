from django.db import models
from django.utils.translation import ugettext_lazy as _


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
