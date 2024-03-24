from camera import views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.production_view, name="gallery"),
    path("production_view/", views.production_view, name="gallery"),
    path("production_images/", views.productionImages, name="productioin_images"),
    path("start_camera_background", views.start_camera_background, name="start_camera_background"),
    path("stop_camera_background", views.stop_camera_background, name="stop_camera_background"),
    path('search-batch/', views.batchNumberSearch, name='search_batch_number'),
    path('latest_product/', views.latest_product, name="latest_product"),
    path('api/gallery/upload/', views.GalleryImageUploadAPIView.as_view(),
         name='gallery-photo-upload'),
    path("update_noNGrate", views.update_noNGrate, name="update_noNGrate"),

]
