from django.shortcuts import get_object_or_404, render
from camera.consumers import camera_manager
from camera.camera_process import run_asyncio_camera_loop
import random
from PIL import Image
import numpy as np
from .models import ProductBatchV2, create_new_productBatch_v2
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
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from photologue.models import Gallery, Photo
from django.core.files.base import ContentFile
from .serializers import PhotoUploadSerializer



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
    user_name = request.user.username
    ws_uri = request.data.get("uri")
    upload_url = request.data.get("upload_url")

    # check batch number or create new batch_number
    try:
        batch = ProductBatchV2.objects.get(batch_number=batch_number)
    except:
        create_new_productBatch_v2(batch_number, user_name)

    if trigger_process is None or not trigger_process.is_alive():
        camera_list = camera_manager.camera_sn_list
        for sn in camera_list:
            trigger_process = Process(target=run_asyncio_camera_loop, args=(
                sn,
                batch_number,
                ws_uri,
                upload_url))
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
        batch = ProductBatchV2.objects.latest("production_date")
    else:
        batch = ProductBatchV2.objects.get(batch_number=batch_number)
    if batch:
        camera_num = batch.camera_num
        photo_list = []
        for i in range(camera_num):
            gallery = Gallery.objects.get(title=f"{batch.batch_number}_{i}")
            photo = gallery.photos.latest("date_added")
            if photo:
                photo_list.append({"url": photo.image.url, "thumbnail": photo.get_display_url(), "title": photo.title})

        data = {'batch_number': batch.batch_number, 'urls': photo_list}
        return Response(data)
    else:
        return Response({'batch_number': "", "urls": []})

@login_required
@api_view(['POST'])
def latest_product(request):
    batch = ProductBatchV2.objects.latest("production_date")
    if batch: 
        camera_num = batch.camera_num
        photo_list = []
        for i in range(camera_num):
            gallery = Gallery.objects.get(title=f"{batch.batch_number}_{i}")
            photo = gallery.photos.latest("date_added")
            if photo:
                photo_list.append({"url": photo.image.url, "thumbnail": photo.get_display_url(), "title": photo.title})

        data = {'batch_number': batch.batch_number, 'urls': photo_list}
        return Response(data)
    else:
        return Response({'batch_number': "", "urls": []})


@login_required
@api_view(['GET'])
def batchNumberSearch(request):
    query = request.GET.get('term', '')
    batches = ProductBatchV2.objects.filter(batch_number__icontains=query)
    if not len(batches):
        batches = ProductBatchV2.objects.all().order_by('-production_date')[:5]
    results = [batch.batch_number for batch in batches]

    return Response(results)


class GalleryImageUploadAPIView(APIView):
    parser_classes = (MultiPartParser,)

    def post_old(self, request, *args, **kwargs):
        batch_number = request.data.get('batch_number') 
        serializer = PhotoUploadSerializer(data=request.data)
        
        if not batch_number:
            return Response({"error": "Missing gallery_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            batch = ProductBatch.objects.get(batch_number=batch_number)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        if serializer.is_valid():
            photo = serializer.save()
            batch.gallery.photos.add(photo)  # 将图片添加到指定的Gallery中
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def post(self, request, *args, **kwargs):
        gallery_title = request.data.get('gallery_title') 
        serializer = PhotoUploadSerializer(data=request.data)
        
        if not gallery_title:
            return Response({"error": "Missing gallery_title"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            gallery = Gallery.objects.get(title=gallery_title)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        if serializer.is_valid():
            photo = serializer.save()
            batch.gallery.photos.add(photo)  # 将图片添加到指定的Gallery中
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
