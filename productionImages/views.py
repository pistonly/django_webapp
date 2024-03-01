from django.shortcuts import get_object_or_404, render
from camera.consumers import camera_manager
import random
from PIL import Image
import numpy as np
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import ProductBatch
import time
import multiprocessing
from multiprocessing import Process
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.generic.list import ListView



def upload_one_image(image_io, img_name, batch_number, mime_type='img/jpeg'):
    uploaded_image = InMemoryUploadedFile(
        image_io,  # 文件流
        None,  # 字段名称(这里不需要，因为我们直接操作模型)
        img_name,  # 文件名
        mime_type,  # MIME类型
        image_io.getbuffer().nbytes,  # 文件大小
        None  # 其他参数
    )

    product_batch = ProductBatch.objects.get(batch_number=batch_number)

    # 假设你的Gallery模型有一个方法来处理图像上传
    # 这里的代码将根据你的Gallery模型和关联的字段进行调整
    product_batch.gallery.photos.add(uploaded_image)  # 假设gallery有一个photos字段

# def product_batch_gallery(request, batch_number):
#     batch = get_object_or_404(ProductBatch, batch_number=batch_number)
#     photos = batch.gallery.photos.all()
#     return render(request, 'gallery.html', {'batch': batch, 'photos': photos})

def production_view(request):
    
    return render(request, "productionImages/gallery.html")


def camera_trigger_background(batch_number, stop_event):
    camera_list = list(camera_manager.camera_dict.keys())
    while not stop_event.is_set():
        # simulate trigger
        time.sleep(1)
        img_buf = None
        camera_id = "00000"
        if len(camera_list):
            camera_id = random.randint(0, len(camera_list) - 1)
            success, message = camera_manager.soft_trigger(camera_id)
            if success:
                success, img_buf = camera_manager.get_one_frame(camera_id)
        if img_buf is None:
            _tmp = np.random.randint(0, 255, (640, 640))
            _tmp = Image.fromarray(_tmp)
            img_buff = io.BytesIO()
            _tmp.save(img_buff, format="JPEG")

        img_name = f"{camera_id}_{time.time()}.jpg"
        upload_one_image(img_buf, img_name, batch_number)


stop_event = multiprocessing.Event()
trigger_process = None
trigger_process_status = {"runing": None, "batch_num": None}

@login_required
@api_view(['POST'])
def start_camera_background(request):
    global stop_event
    batch_number = request.data.get('batch_number')
    if trigger_process is None or not trigger_process.is_alive():
        stop_event.clear()
        trigger_process = Process(target=camera_trigger_background, args=(batch_number, stop_event))
        return Response({"processing is started"})
    else:
        return Response({"processing is running"})


@login_required
@api_view(['POST'])
def stop_camera_background(request):
    global stop_event
    if trigger_process is not None and trigger_process.is_alive():
        stop_event.set()
        return Response({"processing is stopped"})
    else:
        return Response({"processing is not running"})


@login_required
@api_view(['POST'])
def productionImages(request):
    latest_batch = ProductBatch.objects.latest("production_date")
    photos = latest_batch.gallery.photos.all()
    urls = [{"url": photo.image.url, "thumbnail": photo.get_display_url(), "title": photo.title} for photo in photos]
    return Response(urls)


@login_required
@api_view(['GET'])
def batchNumberSearch(request):
    query = request.GET.get('term', '')
    batches = ProductBatch.objects.filter(batch_number__icontains=query)
    if not len(batches):
        batches = ProductBatch.objects.all().order_by('-production_date')[:5]
    results = [batch.batch_number for batch in batches]
    print(results)

    return Response(results)
