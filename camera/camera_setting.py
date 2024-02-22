from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .mindvision.camera_utils import get_camera_parameters, set_camera_parameter, initialize_cam
from .consumers import camera_manager
import re


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
            return Response(camera_info)

    def post(self, request):
        data = dict(request.data)
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

