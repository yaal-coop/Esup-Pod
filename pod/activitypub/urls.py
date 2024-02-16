from django.urls import path

from . import views

app_name = "activitypub"


urlpatterns = [
    path(".well-known/webfinger", views.webfinger, name="webfinger"),
    path("account/peertube", views.instance_account, name="instance_account"),
    path("account/peertube/inbox", views.inbox, name="inbox"),
    path("account/peertube/outbox", views.outbox, name="outbox"),
    path("account/peertube/following", views.following, name="following"),
    path("account/peertube/followers", views.followers, name="followers"),
]
