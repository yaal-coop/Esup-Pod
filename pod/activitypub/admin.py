from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Follower, Following
from .tasks import task_follow
from .tasks import task_index_videos


@admin.register(Follower)
class FollowerAdmin(admin.ModelAdmin):
    pass


@admin.action(description=_("Send the federation request"))
def send_federation_request(modeladmin, request, queryset):
    for following in queryset:
        task_follow.apply_async((following.id,))
    modeladmin.message_user(request, _("The federation requests have been sent"))


@admin.action(description=_("Reindex the instance videos"))
def reindex_videos(modeladmin, request, queryset):
    for following in queryset:
        task_index_videos.apply_async((following.id,))
    modeladmin.message_user(request, _("The video indexations has started"))


@admin.register(Following)
class FollowingAdmin(admin.ModelAdmin):
    actions = [send_federation_request, reindex_videos]
