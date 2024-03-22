from django.urls import path

from . import views

app_name = "activitypub"


urlpatterns = [
    path(".well-known/nodeinfo", views.nodeinfo, name="nodeinfo"),
    path(".well-known/webfinger", views.webfinger, name="webfinger"),
    path("ap/account/peertube", views.instance_account, name="instance_account"),
    path("ap/account/<username>", views.user, name="user"),
    path("ap/account/peertube/inbox", views.inbox, name="inbox"),
    path("ap/account/peertube/outbox", views.outbox, name="outbox"),
    path("ap/account/peertube/following", views.following, name="following"),
    path("ap/account/peertube/followers", views.followers, name="followers"),
    path("ap/video/<slug:slug>", views.video, name="video"),
    path("ap/video/<slug:slug>/likes", views.likes, name="likes"),
    path("ap/video/<slug:slug>/dislikes", views.dislikes, name="dislikes"),
    path("ap/video/<slug:slug>/shares", views.shares, name="comments"),
    path("ap/video/<slug:slug>/comments", views.comments, name="shares"),
    path("ap/channel/<slug:slug>", views.channel, name="channel"),
]
