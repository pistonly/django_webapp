import asyncio
import websockets
import io
from PIL import Image, ImageDraw, ImageFont
import uuid
from datetime import datetime
from .mindvision.camera_utils import get_devInfo_list, image_to_numpy
from .camera_manager import cameraManager
from websockets.exceptions import ConnectionClosed
import numpy as np
import json
from pathlib import Path
import django
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os
from asgiref.sync import sync_to_async
from concurrent.futures import ThreadPoolExecutor
import time
from plc.plc_control import plcControl
from django.conf import settings

from .tensorrt_infer import YOLOv8

sys.path.insert(0, "..")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from photologue.models import Photo, Gallery
import logging

logger = logging.getLogger("django")

current_dir = Path(__file__).resolve().parent
configure_dir = current_dir / 'configure'

onnx_path = settings.ONNX_PATH
conf_thres = settings.CONF_THRES
iou_thres = settings.IOU_THRES
ng_ids = settings.NG_IDS
camera_num = settings.CAMERA_NUM
detection = YOLOv8(onnx_path, conf_thres, iou_thres)

# plc = plcControl()
# if not plc.connect():
#     logger.info("~~~~~~~~~~~~~~~~~~~~ ng signal camera process ~~~~~~~~~~~~~~~~~~~~")
#     logger.info("plc is offline")
#     logger.info("~~~~~~~~~~~~~~~~~~~~ ng signal camera process ~~~~~~~~~~~~~~~~~~~~")
#     plc = None


def get_random_image(text):
    text = text[-5:]
    height, width = 640, 640
    frame = np.random.randint(0, 255, (height, width), dtype=np.uint8)
    frame = Image.fromarray(frame.astype(np.uint8))
    # draw
    draw = ImageDraw.Draw(frame)
    font_size = int(height * 0.2)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    text_x, text_y, text_width, text_height = draw.textbbox((0, 0),
                                                            text,
                                                            font=font)
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2
    draw.text((text_x, text_y), text, fill=(255, ), font=font)

    buffer = io.BytesIO()
    frame.save(buffer, format='JPEG')
    return buffer


def prepare_one_image(img_io, gallery_title, camera_info, ng=False):
    img_io.seek(0)
    unique_slug = uuid.uuid4().hex

    gallery_title = "-".join(gallery_title.split("_"))
    formatted_time = datetime.now().strftime(
        '%Y%m%d-%H%M%S-%f')[:17]  # 使用微秒的前两位来表示0.01秒
    roi0 = camera_info['roi0']
    roi1 = camera_info['roi1']
    roi_str = ""
    if not camera_info['roi0_disabled']:
        roi_str += f"{roi0[0]:04d}{roi0[1]:04d}{roi0[2]:04d}{roi0[3]:04d}"
    if not camera_info['roi1_disabled']:
        if len(roi_str):
            roi_str += "-"
        roi_str += f"{roi1[0]:04d}{roi1[1]:04d}{roi1[2]:04d}{roi1[3]:04d}"
    file_title = f"{gallery_title}_{formatted_time}_{roi_str}_{0 if ng else 1}.jpg"
    uploaded_image = InMemoryUploadedFile(img_io, None, file_title, "img/jpeg",
                                          img_io.getbuffer().nbytes, None)

    # files = {"image": (file_title, img_io.getvalue(), 'image/jpeg')}
    data = {
        "image": uploaded_image,
        "title": file_title,
        "caption": "a bottle image",
        'slug': unique_slug,
    }
    return data


def get_AI_results(img_io):
    logger.info("AI infering .....")
    t0 = time.time()
    pred_img, pred_ids = detection.process_one_image(img_io)
    logger.info(f"AI finished:cost time: {time.time() - t0}s")
    pred_ids_s = set(pred_ids)
    pred_ng_ids = pred_ids_s.intersection(ng_ids)
    ng = True if len(pred_ng_ids) else False
    frame = Image.fromarray(pred_img)
    buffer = io.BytesIO()
    frame.save(buffer, format="JPEG")
    return ng, buffer

# def send_ng(gallery_id):
#     _id = int(gallery_id.split("_")[-1])
#     if plc is not None:
#         if camera_num != 4:
#             _id = _id // 3
#         plc.set_M(f"M1{_id + 1}")
#         logger.info(f"----------send ng: M1{_id + 1}===============")


def capture_and_upload(camera_manager: cameraManager, gallery_title, plc_timestamp, delay=0.02):
    target_time = plc_timestamp + delay
    while time.time() < target_time:
        time.sleep(0.0001)
    start_timestamp = time.time()
    if camera_manager.current_camera is None:
        img_io = get_random_image(gallery_title)
    else:
        success, img_io = camera_manager.get_one_frame()
        if not success:
            print("***************************************")
            img_io = get_random_image(gallery_title)
            print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    finish_timestamp = time.time()
    ng, img_io = get_AI_results(img_io)
    # if ng:
    #     send_ng(gallery_title)

    camera_roi_info = camera_manager.get_camera_roi()
    camera_roi_info = dict(zip(['roi0', 'roi1', 'roi0_disabled', 'roi1_disabled'],
                               camera_roi_info))
    data = prepare_one_image(img_io, gallery_title, camera_roi_info, ng)
    # logger.info(f"{gallery_title}: get one immage")
    gallery = Gallery.objects.get(title=gallery_title)
    photo = Photo(**data)
    photo.save()
    gallery.photos.add(photo)
    gallery.save()
    img_info = {
        "url": photo.image.url,
        "thumbnail": photo.get_display_url(),
        "title": photo.title,
        "ng": ng,
        "start_timestamp": start_timestamp,
        "finish_timestamp": finish_timestamp,
    }
    return img_info


async def websocket_client(camera_manager, gallery_title, uri):
    try:
        async with websockets.connect(uri) as websocket:
            # send id
            if camera_manager.current_camera is None:
                message = {"client_id": gallery_title, "update": 1}
            else:
                message = {"client_id": gallery_title}
            await websocket.send(json.dumps(message))
            response = await websocket.recv()
            logger.info(f"0< {response}")

            try:
                # get camera_id from ws server
                response = json.loads(response)
                gallery_title = response['client_id']
                logger.info(f"client_id updated: {gallery_title}")
            except Exception as e:
                logger.info(f"init connect error: {e}")

            # NG register
            _id = int(gallery_title.split("_")[-1])
            if camera_num != 4:
                _id = _id // 3
            NG_reg = f"M1{_id + 1}"
            logger.info(f"$$$$$$$$$$$$$$$$$$$$$$--NG_reg: {NG_reg}, camera_num: {camera_num}, {_id}")


            while True:
                message = await websocket.recv()
                logger.info(f"{gallery_title}:< {message}")
                message = json.loads(message)

                if "stop" in message:
                    logger.info("Stopping as per 'stop' signal.")
                    break

                elif "trig" in message:
                    loop = asyncio.get_running_loop()
                    plc_timestamp = message.get("timestamp")
                    img_info = await loop.run_in_executor(
                        None, capture_and_upload, camera_manager, gallery_title, plc_timestamp)
                    logger.info(f"{gallery_title}: Capturing image at timestamp: {img_info['start_timestamp']}, finish at: {img_info['finish_timestamp']}.")

                    img_info.update({
                        "target": "web",
                        "gallery_id": gallery_title,
                        "updated": 1,
                        "trig_id": message.get("trig_id"),
                        "NG_reg": NG_reg,
                    })
                    await websocket.send(json.dumps(img_info))
    except ConnectionClosed:
        logger.info("ws closed")
    except Exception as e:
        logger.info(f"An unexpected error: {e}")


async def main(camera_manager: cameraManager, gallery_title: str, ws_uri: str):
    await websocket_client(camera_manager, gallery_title, ws_uri)


def run_asyncio_camera_loop(camera_sn: str, batch_number: str, ws_uri: str):
    # start camera, and load configure
    try:
        camera_manager = cameraManager()
        camera_manager.start_camera(camera_sn)
        if camera_manager.current_camera is not None:
            camera_name = camera_manager.current_camera.name
            camera_ord = int(camera_name.split("_")[-1])
            if camera_ord > 4 or camera_ord < 0:
                logger.info("camera ord should in range(0, 4)")
                camera_ord = 0
            gallery_title = f"{batch_number}_{camera_ord}"
        else: 
            # ws server generate camera_ord
            gallery_title = batch_number

        asyncio.run(main(camera_manager, gallery_title, ws_uri))
    except Exception as e:
        logger.info(f"camera process error: {str(e)}")

    finally:
        logger.info("==================process quit=====================")
        camera_manager.close_camera()
