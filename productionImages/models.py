from django.db import models
from photologue.models import Gallery
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.timezone import now


class ProductBatch(models.Model):
    batch_number = models.CharField(max_length=100, unique=True)
    gallery = models.OneToOneField(Gallery, on_delete=models.CASCADE, related_name='product_batch')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_batches')
    production_date = models.DateField()

    def __str__(self):
        return self.batch_number

class ProductBatchV2(models.Model):
    batch_number = models.CharField(max_length=100, unique=True)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_batches_op')
    production_date = models.DateField()
    camera_num = models.IntegerField()

    def __str__(self):
        return self.batch_number



def upload_one_image(image_io, img_name, batch_number, mime_type='img/jpeg'):
    print("upload one image")
    uploaded_image = InMemoryUploadedFile(
        image_io,  # 文件流
        None,  # 字段名称(这里不需要，因为我们直接操作模型)
        img_name,  # 文件名
        mime_type,  # MIME类型
        image_io.getbuffer().nbytes,  # 文件大小
        None  # 其他参数
    )
    product_batch = ProductBatch.objects.get(batch_number=batch_number)
    product_batch.gallery.photos.add(uploaded_image)  


def create_new_gallery(title, description="", is_public=True):
    # 创建Gallery实例
    new_gallery = Gallery.objects.create(
        title=title,
        slug=title.lower().replace(" ", "-"),  # 生成一个简单的slug，实际情况可能需要更复杂的处理以确保唯一性
        description=description,
        is_public=is_public,
        date_added=now()  # 使用当前时间作为添加日期
    )
    new_gallery.save()

    return new_gallery


def create_new_productBatch(batch_number, operator_name):
    try:
        gallery = Gallery.objects.get(title=batch_number)
    except:
        gallery = create_new_gallery(batch_number)

    operator = User.objects.get(username=operator_name)
    new_product = ProductBatch.objects.create(
        batch_number=batch_number,
        gallery=gallery,
        operator=operator,
        production_date=now())

    new_product.save()
    return new_product

def create_new_productBatch_v2(batch_number, operator_name, camera_num=18):
    
    operator = User.objects.get(username=operator_name)
    new_product = ProductBatchV2(batch_number=batch_number,
                                 operator=operator,
                                 production_date=now(),
                                 camera_num=camera_num)
    new_product.save()

    for i in range(camera_num):
        gallery_title = f"{batch_number}_{i}"
        try:
            gallery = Gallery.objects.get(title=gallery_title)
        except:
            gallery = create_new_gallery(gallery_title)
    return new_product
