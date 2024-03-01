from camera import views
from django.urls import path
from . import views

urlpatterns = [
    path("production_view/", views.production_view, name="image_list"),
    path("production_images/", views.productionImages, name="productioin_images"),
    path("start_camera_background", views.start_camera_background, name="start_camera_background"),
    path("stop_camera_background", views.stop_camera_background, name="stop_camera_background"),
]
