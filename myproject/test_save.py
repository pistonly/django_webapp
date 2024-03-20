from photologue.models import Gallery, Photo
from .serializers import PhotoUploadSerializer
import numpy as np
import os
import django
from django.core.files.uploadedfile import InMemoryUploadedFile
import io
from PIL import Image
import sys

# sys.path.insert(0, "..")
# # 设置Django环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

image = np.random.randint(0, 255, (640, 640), dtype=np.uint8)
image = Image.fromarray(image)
image_io = io.BytesIO()
image.save(image_io, format="JPEG")

uploaded_image = InMemoryUploadedFile(
    image_io,  # 文件流
    None,  # 字段名称(这里不需要，因为我们直接操作模型)
    "test.jpg",  # 文件名
    "img/jpeg",  # MIME类型
    image_io.getbuffer().nbytes,  # 文件大小
    None  # 其他参数
)

gallery = Gallery.objects.create(title="test_gallery", description="This is a new gallery.")

# 创建Photo实例并保存
photo = Photo(image=uploaded_image, title="Random Image", caption="This is a random image.")
photo.save()

# 将照片添加到图库
gallery.photos.add(photo)
gallery.save()
