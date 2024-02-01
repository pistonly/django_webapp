from django.shortcuts import render
from .models import Image
from django.contrib.auth.decorators import login_required
# from .utils import add_images_to_database
from pathlib import Path
from django.conf import settings
from PIL import Image as pil_img

# add_images_to_database(str(Path(settings.MEDIA_ROOT) / "test_images"))
# add_images_to_database()

@login_required
def image_list(request):
    images = Image.objects.all()
    return render(request, 'imageapp/image_list.html', {'images': images})
