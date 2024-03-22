from django.urls import path

from . import views

app_name = "activitypub"


urlpatterns = [
    path(".well-known/nodeinfo", views.nodeinfo, name="nodeinfo"),
    path(".well-known/webfinger", views.webfinger, name="webfinger"),
    path("ap", views.account, name="account"),
    path("ap/account/<str:username>", views.account, name="account"),
    path("ap/inbox", views.inbox, name="inbox"),
    path("ap/account/<str:username>/inbox", views.inbox, name="inbox"),
    path("ap/outbox", views.outbox, name="outbox"),
    path("ap/account/<str:username>/outbox", views.outbox, name="outbox"),
    path("ap/following", views.following, name="following"),
    path("ap/account/<str:username>/following", views.following, name="following"),
    path("ap/followers", views.followers, name="followers"),
    path("ap/account/<str:username>/followers", views.followers, name="followers"),
    path("ap/video/<slug:slug>", views.video, name="video"),
    path("ap/video/<slug:slug>/likes", views.likes, name="likes"),
    path("ap/video/<slug:slug>/dislikes", views.dislikes, name="dislikes"),
    path("ap/video/<slug:slug>/shares", views.shares, name="comments"),
    path("ap/video/<slug:slug>/comments", views.comments, name="shares"),
    path("ap/channel/<slug:slug>", views.channel, name="channel"),
]
