from django.urls import path
from .plc_ws_consumers import PLCControlConsumer

websocket_urlpatterns = [
    path('ws/plc_check/', PLCControlConsumer.as_asgi()),
]
