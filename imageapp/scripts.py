import os
from django.core.files import File
from django.conf import settings
from .models import Image  # 更改为你的实际模型和应用名
import tempfile


def add_images_to_database():
    # images_folder = os.path.join(settings.MEDIA_ROOT, 'images_folder')
    images_folder = os.path.join(settings.BASE_DIR, "images_folder")

    for filename in os.listdir(images_folder):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
            # 避免重复添加
            if not Image.objects.filter(title=filename).exists():
                image_path = os.path.join(images_folder, filename)
                with open(image_path, "rb") as file:
                    django_file = File(file)
                    image_instance = Image(title=filename)
                    image_instance.image.save(filename, File(file), save=True)
                    image_instance.save()
