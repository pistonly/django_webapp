from django.urls import path
from .views import camera_view

urlpatterns = [
    path('camera/', camera_view, name='camera'),
]
