from django.shortcuts import get_object_or_404, render
from camera.consumers import camera_manager
from camera.camera_process import run_asyncio_camera_loop
import random
from PIL import Image
import numpy as np
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


@login_required
def production_view(request):
    # get latest production
    user_name = request.user.username
    data = {"user_name": user_name}
    print(data)
    return render(request, "productionImages/gallery.html", context=data)


stop_event = multiprocessing.Event()
trigger_process = None
trigger_process_status = {"runing": None, "batch_num": None}

@login_required
@api_view(['POST'])
def start_camera_background(request):
    global stop_event, trigger_process
    camera_manager.update_camera_list(start_default=False)
    camera_manager.close_camera()
    batch_number = request.data.get('batch_number')
    if trigger_process is None or not trigger_process.is_alive():
        stop_event.clear()
        camera_list = camera_manager.camera_sn_list
        trigger_process = Process(target=run_asyncio_camera_loop, args=(camera_list[0],
                                                                        stop_event))
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

