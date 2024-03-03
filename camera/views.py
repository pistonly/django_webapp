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
    img_path = str(directory / f"{datetime.now().strftime('%y%m%d%H%M%S')}.bmp")
    success, message = camera_manager.grab(camera_id, img_path, quality)
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
        camera_id = request.query_params.get("camera_id")
        success, camera_info = camera_manager.get_camera_info(camera_id)
        print(camera_info)

        if not success:
            return Response({"error": camera_info}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(camera_info, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data.dict()
        camera_id = data.get("camera_id")
        if not camera_id:
            return Response({"error": f"Camera: {camera_id} not found"}, status=status.HTTP_404_NOT_FOUND)
        if 'resolution' in data:
            ret, (w, h) = get_resolution_from_text(data['resolution'][0])
            if ret:
                data['resolution'] = dict(zip(['w', 'h'], [w, h]))
            else:
                return Response({"error": f"resoluton format error!"}, status=status.HTTP_404_NOT_FOUND)

        success, camera_info = camera_manager.set_camera(camera_id, data)
        print(camera_info)
        if success:
            return Response({"success": "Parameter updated"})
        else:
            return Response({"error": "Failed to update parameter"}, status=status.HTTP_400_BAD_REQUEST)

@login_required
@api_view(['POST'])
def set_roi(request):
    camera_id = request.data.get('camera_id')
    x0 = request.data.get('x0')
    x1 = request.data.get('x1')
    y0 = request.data.get('y0')
    y1 = request.data.get('y1')
    camera_manager.camera_dict[camera_id]['roi'].append((x0, y0, x1, y1))
    return Response({"message": "sucess"}, status=status.HTTP_200_OK)
