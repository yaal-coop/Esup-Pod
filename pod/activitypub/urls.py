from django.urls import path
from . import views

app_name = "progressive_web_app"


urlpatterns = [
    path(".well-known/webfinger", views.webfinger, name="webfinger"),
    path("accounts/instance_name", views.instance_account, name='instance_account'),
    path("account/instance_name/inbox", views.inbox, name='inbox'),
    path("account/instance_name/outbox", views.outbox, name='outbox'),
    path("account/instance_name/following", views.following, name='following'),
    path("account/instance_name/followers", views.followers, name='followers'),
]
