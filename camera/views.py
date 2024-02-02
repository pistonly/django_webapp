from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def camera_view(request):
    return render(request, 'camera/camera.html')
