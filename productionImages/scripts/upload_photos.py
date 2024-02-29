import os
import django
import sys
from pathlib import Path

django_root = Path(__file__).resolve().parents[2]
sys.path.append(str(django_root))

# 设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# 初始化Django
django.setup()

from django.core.files import File
from photologue.models import Photo
import uuid

def upload_photos_from_directory(directory_path):
    for filename in os.listdir(directory_path):
        if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            continue  # Skip non-image files

        try:
            file_path = os.path.join(directory_path, filename)
            print(f"filename: {filename}")
            unique_slug = uuid.uuid4().hex
            with open(file_path, 'rb') as file:
                photo = Photo(title=filename, slug=unique_slug, image=File(file, name=filename))
                photo.save()
                print(f'Uploaded {filename}')
        except Exception as e:
            print(f"error: {e}")

if __name__ == '__main__':
    directory_path = 'c:/Users/Administrator/Pictures/Saved Pictures/solar panels.v2-release.yolov8/valid/images'
    upload_photos_from_directory(directory_path)
