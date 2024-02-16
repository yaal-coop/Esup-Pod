from django.contrib import admin

from .models import Follower
from .models import Following


@admin.register(Follower)
class FollowerAdmin(admin.ModelAdmin):
    pass


@admin.register(Following)
class FollowingAdmin(admin.ModelAdmin):
    pass
