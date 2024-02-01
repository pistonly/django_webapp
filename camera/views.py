from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# add_images_to_database(str(Path(settings.MEDIA_ROOT) / "test_images"))
# add_images_to_database()

@login_required
def camera_view(request):
    return render(request, 'camera/camera.html')
