from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .consumers import camera_dict, update_camera_list
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
    global camera_dict
    camera_dict = update_camera_list()
    camera_ids = list(camera_dict.keys())
    if len(camera_ids) < 1:
        camera_ids = ["---------"]
    return JsonResponse({'cameras': camera_ids})


@login_required
@api_view(['POST'])
def camera_grab(request):
    camera_id = request.data.get("camera_id")
    # directory = request.data.get("dir")
    quality = request.data.get("quality", 100)
    if "handle" not in camera_dict[camera_id]:
        camera_res = initialize_cam(camera_dict[camera_id]['dev_info'])
        camera_dict[camera_id].update(dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                               camera_res)))
    pFrameBuffer, FrameHead = get_one_frame(camera_dict[camera_id]['handle'],
                                            camera_dict[camera_id]['pb'])
    directory = Path(settings.MEDIA_ROOT) / 'grab' / camera_id
    directory.mkdir(parents=True, exist_ok=True)
    img_path = directory / f"{datetime.now().strftime('%y%m%d%H%M%S')}.bmp"
    success = save_image(camera_dict[camera_id]['handle'], pFrameBuffer, FrameHead,
                         str(img_path), quality, img_type='bmp')
    if success:
        return Response({"message": "save image success"})
    else:
        return Response({"message": "save image failed"})


