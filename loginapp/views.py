from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import LoginForm


def login_view(request):
    if request.method == "POST":
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("image_list")
    else:
        form = LoginForm()
    return render(request, "loginapp/login.html", {"form": form})
