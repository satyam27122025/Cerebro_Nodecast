from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path(r"^create-room/?$", views.create_room),
    re_path(r"^join-room/?$", views.join_room),
    re_path(r"^room-state/(?P<room_code>[^/]+)/?$", views.get_room_state),
]
