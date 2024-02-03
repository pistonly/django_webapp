# cameraapp/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/camera/", consumers.CameraStreamConsumer.as_asgi()),
]
