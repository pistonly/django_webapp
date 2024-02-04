from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .consumers import camera_dict


@login_required
def camera_view(request):
    print("camera view")
    return render(request, "camera/camera.html")


@login_required
def camera_list(request):
    print("camera list")
    camera_ids = list(camera_dict.keys())
    if len(camera_ids) < 1:
        camera_ids = ["---------"]
    return JsonResponse({'cameras': camera_ids})

