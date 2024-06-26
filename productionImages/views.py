from django.shortcuts import get_object_or_404, render
from camera.camera_manager import get_camera_sn
from camera.camera_process_with_ws_model import run_asyncio_camera_loop
import random
from PIL import Image
import numpy as np
from .models import ProductBatchV2, get_or_create_product
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
    batch_number = request.data.get('batch_number')
    user_name = request.user.username
    ws_uri = request.data.get("uri")
    upload_url = request.data.get("upload_url")

    # check batch number or create new batch_number
    batch = get_or_create_product(batch_number, user_name)

    camera_num = batch.camera_num

    if trigger_process is None or not trigger_process.is_alive():
        camera_list = get_camera_sn()
        for sn in camera_list:
            trigger_process = Process(target=run_asyncio_camera_loop,
                                      args=(sn, batch_number, ws_uri))
            trigger_process.start()
        # start random camera
        if len(camera_list) < camera_num:
            for _ in range(camera_num - len(camera_list)):
                trigger_process = Process(target=run_asyncio_camera_loop,
                                          args=("", batch_number, ws_uri))
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
    try:
        if batch_number == "-1":
            batch = ProductBatchV2.objects.latest("production_date")
        else:
            batch = ProductBatchV2.objects.get(batch_number=batch_number)
        camera_num = batch.camera_num
        photo_list = []
        for i in range(camera_num):
            gallery = Gallery.objects.get(title=f"{batch.batch_number}_{i}")
            photo = gallery.photos.latest("date_added")
            if photo:
                photo_list.append({
                    "url": photo.image.url,
                    "thumbnail": photo.get_display_url(),
                    "title": photo.title
                })

        data = {'batch_number': batch.batch_number, 'urls': photo_list}
        return Response(data)
    except Exception as e:
        return Response({'batch_number': "", "urls": [], 'message': str(e)})


@login_required
@api_view(['POST'])
def latest_product(request):
    try:
        batch = ProductBatchV2.objects.last()
        camera_num = batch.camera_num
        photo_list = []
        for i in range(camera_num):
            gallery = Gallery.objects.get(title=f"{batch.batch_number}_{i}")
            photo = gallery.photos.last()
            if photo is not None:
                row, col = i % 3, i // 3
                photo_list.append({
                    "url": photo.image.url,
                    "thumbnail": photo.get_display_url(),
                    "title": photo.title,
                    "img_id": f"#r-{row}-c-{col}"
                })

        data = {'batch_number': batch.batch_number, 'urls': photo_list}
        return Response(data)
    except Exception as e:
        return Response({'batch_number': "", "urls": [], "message": str(e)})


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
    # parser_classes = (MultiPartParser,)

    def get(self, request):
        try:
            gallery_title = request.query_params.get("gallery_title")
            gallery = Gallery.objects.get(title=gallery_title)
            photo = gallery.photos.last()
            if photo is not None:
                return Response({
                    "url": photo.image.url,
                    "thumbnail": photo.get_display_url(),
                    "title": photo.title
                })
        except Exception as e:
            return Response({"message": str(e)},
                            status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        gallery_title = request.data.get('gallery_title')
        serializer = PhotoUploadSerializer(data=request.data)

        if not gallery_title:
            return Response({"error": "Missing gallery_title"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            gallery = Gallery.objects.get(title=gallery_title)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_404_NOT_FOUND)

        if serializer.is_valid():
            photo = serializer.save()
            gallery.photos.add(photo)  # 将图片添加到指定的Gallery中
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def update_noNGrate(request):
    product_name = request.data.get("product_name")
    ng = request.data.get("ng")
    ng = False if ng is None else ng
    try:
        product = ProductBatchV2.objects.get(batch_number=product_name)
    except Exception as e:
        return Response(
            {"message": f"batch_name: {product_name} error, {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST)

    product.bottle_num = product.bottle_num + 1
    if not ng:
        product.noNG_num += 1
    product.noNG_rate = product.noNG_num / product.bottle_num
    product.save()
    return Response({"noNG_rate": f"{product.noNG_rate:.2f}", "noNG_num": product.noNG_num})
