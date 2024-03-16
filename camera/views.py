from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .consumers import camera_manager
from datetime import datetime
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from rest_framework.views import APIView
import re

def is_admin(user):
    return user.is_superuser or user.is_staff

@login_required
@user_passes_test(is_admin)
def camera_view(request):
    print("camera view")
    return render(request, "camera/camera.html", {"camera_names": [f"camera_{i:02d}" for i in range(18)]})


@login_required
def camera_list(request):
    print("camera list")
    camera_manager.update_camera_list()
    camera_ids = camera_manager.camera_sn_list
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
    img_path = str(directory / f"{datetime.now().strftime('%y%m%d%H%M%S')}.bmp")
    success, message = camera_manager.grab(camera_id, img_path, quality)
    if success:
        _status = status.HTTP_200_OK
    else:
        _status = status.HTTP_400_BAD_REQUEST
    return Response({"message": message}, status=_status)

@login_required
@api_view(['POST'])
def change_camera(request):
    camera_id = request.data.get("camera_id")
    success, message = camera_manager.start_camera(camera_id)
    if success:
        _status = status.HTTP_200_OK
    else:
        _status = status.HTTP_400_BAD_REQUEST
    return Response({"message": message}, status=_status)


@login_required
@api_view(['POST'])
def save_configure(request):
    camera_id = request.data.get("camera_id")
    config_f = request.data.get("config_f")
    success, message = camera_manager.save_configure(camera_id, config_f)
    if success:
        _status = status.HTTP_200_OK
    else:
        _status = status.HTTP_400_BAD_REQUEST
    return Response({"message": message}, status=_status)

@login_required
@api_view(['POST'])
def load_configure(request):
    camera_id = request.data.get("camera_id")
    config_f = request.data.get("config_f")
    success, message = camera_manager.load_configure(camera_id, config_f)
    if success:
        _status = status.HTTP_200_OK
    else:
        _status = status.HTTP_400_BAD_REQUEST
    return Response({"message": message}, status=_status)


@login_required
@api_view(['POST'])
def reset_configure(request):
    camera_id = request.data.get("camera_id")
    config_f = request.data.get("config_f")
    success, message = camera_manager.reset_configure(camera_id, config_f)
    if success:
        _status = status.HTTP_200_OK
    else:
        _status = status.HTTP_400_BAD_REQUEST
    return Response({"message": message}, status=_status)


def get_resolution_from_text(content):
    pattern = r"(\d+)x(\d+)"
    match = re.search(pattern, content)
    if match:
        # 分别获取匹配的两个数字
        w, h = match.groups()
        return True, (int(w), int(h))
    else:
        return False, (None, None)

class CameraParameters(APIView):
    def get(self, request):
        success, camera_info = camera_manager.get_camera_info()
        print(camera_info)

        if not success:
            return Response({"error": camera_info}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(camera_info, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data.dict()
        data_append = {}
        for k, v in data.items():
            if "[]" in k:
                data_append[k[:-2]] = request.data.getlist(k)
        data.update(data_append)

        if 'resolution' in data:
            ret, (w, h) = get_resolution_from_text(data['resolution'][0])
            if ret:
                data['resolution'] = dict(zip(['w', 'h'], [w, h]))
            else:
                return Response({"error": f"resoluton format error!"}, status=status.HTTP_404_NOT_FOUND)

        print(data)
        success, camera_info = camera_manager.set_camera(data)
        print(camera_info)
        if success:
            return Response({"success": "Parameter updated"})
        else:
            return Response({"error": "Failed to update parameter"}, status=status.HTTP_400_BAD_REQUEST)

