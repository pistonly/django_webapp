from django.urls import path
from .views import production_view

urlpatterns = [
    path("production_view/", production_view, name="image_list"),
]
