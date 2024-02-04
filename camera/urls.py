from django.urls import path
from . import views, camera_setting

urlpatterns = [
    path("camera/", views.camera_view, name="camera"),
    path('camera_list/', views.camera_list, name='camera_list'),
    path('api/camera/parameters/', camera_setting.CameraParameters.as_view(), name='camera-parameters'),
]


