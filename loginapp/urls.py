from django.urls import path
from .views import login_view

urlpatterns = [
    path("", login_view),
    path("login/", login_view, name="login"),
]
