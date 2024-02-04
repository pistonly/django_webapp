from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .mindvision.camera_utils import get_camera_parameters, set_camera_parameter
from .consumers import camera_dict
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
        camera_info = camera_dict.get(camera_id)

        # get gamma range

        if not camera_info:
            return Response({"error": f"Camera: {camera_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        hCamera = camera_info.get('handle')
        if not hCamera:
            return Response({"error": f"Camera: {camera_id} is not initialized"}, status=status.HTTP_404_NOT_FOUND)

        parameters = get_camera_parameters(hCamera)
        if parameters:
            return Response(parameters)
        else:
            return Response({"error": "get parameter error!"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        data = dict(request.data)
        camera_id = data.get("camera_id")
        if not camera_id:
            return Response({"error": f"Camera: {camera_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        camera_info = camera_dict.get(camera_id[0])

        if not camera_info:
            return Response({"error": f"Camera: {camera_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        hCamera = camera_info.get('handle')

        if 'resolution' in data:
            ret, (w, h) = get_resolution_from_text(data['resolution'][0])
            if ret:
                data['resolution'] = dict(zip(['w', 'h'], [w, h]))
            else:
                return Response({"error": f"resoluton format error!"}, status=status.HTTP_404_NOT_FOUND)


        if set_camera_parameter(hCamera, **data):
            return Response({"success": "Parameter updated"})
        else:
            return Response({"error": "Failed to update parameter"}, status=status.HTTP_400_BAD_REQUEST)
