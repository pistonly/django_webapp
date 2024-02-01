from django.urls import path
from .views import image_list

urlpatterns = [
    path('images/', image_list, name='image_list'),
]
