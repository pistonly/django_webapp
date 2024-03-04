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
from django.contrib.auth.models import User
import io
from .plc_scripts import background_task


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


@login_required
def production_view(request):
    # get latest production
    user_name = request.user.username
    data = {"user_name": user_name}
    print(data)
    return render(request, "productionImages/gallery.html", context=data)


def camera_trigger_background(batch_number, stop_event):
    print("here0")
    camera_list = list(camera_manager.camera_dict.keys())
    print(f"camera_list: {camera_list}")
    while not stop_event.is_set():
        # simulate trigger
        time.sleep(1)
        img_buf = None
        print("here")
        if len(camera_list):
            camera_id = random.randint(0, len(camera_list) - 1)
            success, img_buf = camera_manager.soft_trigger(camera_list[camera_id])
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
    global stop_event, trigger_process
    batch_number = request.data.get('batch_number')
    if trigger_process is None or not trigger_process.is_alive():
        stop_event.clear()
        uri = "ws://localhost:8000/ws/camera/"
        camera_list = list(camera_manager.camera_dict.keys())
        # trigger_process = Process(target=camera_trigger_background, args=(batch_number, stop_event))
        trigger_process = Process(target=background_task, args=(uri, batch_number, stop_event, camera_list))
        trigger_process.start()
        return Response({"processing is started"})
    else:
        return Response({"processing is running"})


@login_required
@api_view(['POST'])
def stop_camera_background(request):
    global stop_event
    if trigger_process is not None and trigger_process.is_alive():
        stop_event.set()
        trigger_process.join()
        return Response({"processing is stopped"})
    else:
        return Response({"processing is not running"})


@login_required
@api_view(['POST'])
def productionImages(request):
    batch_number = request.data.get("batch_number")
    if batch_number == "-1":
        batch = ProductBatch.objects.latest("production_date")
    else:
        batch = ProductBatch.objects.get(batch_number=batch_number)
    photos = batch.gallery.photos.all()
    urls = [{"url": photo.image.url, "thumbnail": photo.get_display_url(), "title": photo.title} for photo in photos]
    return Response(urls)

@login_required
@api_view(['POST'])
def latest_product(request):
    batch = ProductBatch.objects.latest("production_date")
    photos = batch.gallery.photos.all()
    urls = [{"url": photo.image.url, "thumbnail": photo.get_display_url(), "title": photo.title} for photo in photos]
    data = {'batch_number': batch.batch_number, 'urls': urls}
    return Response(data)


@login_required
@api_view(['GET'])
def batchNumberSearch(request):
    query = request.GET.get('term', '')
    batches = ProductBatch.objects.filter(batch_number__icontains=query)
    if not len(batches):
        batches = ProductBatch.objects.all().order_by('-production_date')[:5]
    results = [batch.batch_number for batch in batches]

    return Response(results)

