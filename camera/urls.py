from django.urls import path
from . import views

urlpatterns = [
    path("camera/", views.camera_view, name="camera"),
    path('camera_list/', views.camera_list, name='camera_list'),
    path('camera_grab/', views.camera_grab, name='camera_grab'),
    path('api/camera/parameters/', views.CameraParameters.as_view(), name='camera-parameters'),
    path('set_roi', views.set_roi, name='set_roi'),
    path('save_configure', views.save_configure, name='save_configure'),
    path('load_configure', views.load_configure, name='load_configure'),
    path('reset_configure', views.reset_configure, name='reset_configure'),
]


