from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .consumers import camera_manager
from .mindvision.camera_utils import initialize_cam, save_image, get_one_frame
from datetime import datetime
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings


@login_required
def camera_view(request):
    print("camera view")
    return render(request, "camera/camera.html")


@login_required
def camera_list(request):
    print("camera list")
    camera_manager.update_camera_list()
    camera_ids = list(camera_manager.camera_dict.keys())
    if len(camera_ids) < 1:
        camera_ids = ["---------"]
    return JsonResponse({'cameras': camera_ids})


@login_required
@api_view(['POST'])
def camera_grab(request):
    camera_id = request.data.get("camera_id")
    # directory = request.data.get("dir")
    quality = request.data.get("quality", 100)
    directory = Path(settings.MEDIA_ROOT) / 'grab' / camera_id
    directory.mkdir(parents=True, exist_ok=True)
    img_path = directory / f"{datetime.now().strftime('%y%m%d%H%M%S')}.bmp"
    success = camera_manager.grab(camera_id, img_path, quality)
    if success:
        return Response({"message": "save image success"})
    else:
        return Response({"message": "save image failed"})


