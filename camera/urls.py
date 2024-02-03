from django.urls import path
from . import views

urlpatterns = [
    path("camera/", views.camera_view, name="camera"),
    path('camera_list/', views.camera_list, name='camera_list'),
]
