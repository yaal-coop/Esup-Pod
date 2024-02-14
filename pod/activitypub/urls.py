from django.urls import path
from . import views

app_name = "progressive_web_app"


urlpatterns = [
    path(".well-known/webfinger", views.webfinger, name="webfinger"),
    # path(fr"^{{'instance/instance_name'}}(?:\.(?P<format>json))?$", views.boxes, name='boxes'),
    path("instance/instance_name.json", views.boxes, name='boxes'),
    path("instance/instance_name/inbox", views.inbox, name='inbox'),
    path("instance/instance_name/outbox", views.outbox, name='outbox'),
]
