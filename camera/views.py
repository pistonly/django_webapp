from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
import logging

logger = logging.getLogger("django")

def is_admin(user):
    return user.is_superuser or user.is_staff

camera_num = 4

@login_required
@user_passes_test(is_admin)
def camera_view(request):
    logger.info("camera view")
    return render(request, "camera/camera.html",
                  {"camera_names": [f"camera_{i:02d}" for i in range(camera_num)]})

