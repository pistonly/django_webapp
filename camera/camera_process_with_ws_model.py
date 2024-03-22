import asyncio
import websockets
import io
from PIL import Image, ImageDraw, ImageFont
import uuid
from datetime import datetime
from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image, softTrigger
from websockets.exceptions import ConnectionClosed
import numpy as np
import aiohttp
import json
from pathlib import Path
import django
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os
from asgiref.sync import sync_to_async
from concurrent.futures import ThreadPoolExecutor


sys.path.insert(0, "..")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from photologue.models import Gallery, Photo
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



current_dir = Path(__file__).resolve().parent
configure_dir = current_dir / 'configure'

def get_one_image(camera):
    # softTrigger
    error_code = softTrigger(camera['handle'])
    # get one frame
    pb, FH = get_one_frame(camera['handle'], camera['pb'])
    frame = image_to_numpy(pb, FH)
    frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
    frame = Image.fromarray(frame.astype(np.uint8))
    buffer = io.BytesIO()
    frame.save(buffer, format='JPEG')
    return buffer

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
    
    text_x, text_y, text_width, text_height = draw.textbbox((0,0), text, font=font)
    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2
    draw.text((text_x, text_y), text, fill=(255, ), font=font)

    buffer = io.BytesIO()
    frame.save(buffer, format='JPEG')
    return buffer


def prepare_one_image(img_io, gallery_title, camera_info):
    img_io.seek(0)
    unique_slug = uuid.uuid4().hex

    formatted_time = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:17]  # 使用微秒的前两位来表示0.01秒
    roi0 = camera_info['roi0']
    roi1 = camera_info['roi1']
    roi_str = ""
    if not camera_info['roi0_disabled']:
        roi_str += f"{roi0[0]:04d}{roi0[1]:04d}{roi0[2]:04d}{roi0[3]:04d}"
    if not camera_info['roi1_disabled']:
        if len(roi_str):
            roi_str += "-"
        roi_str += f"{roi1[0]:04d}{roi1[1]:04d}{roi1[2]:04d}{roi1[3]:04d}"
    file_title = f"{gallery_title}_{formatted_time}_{roi_str}.jpg"
    uploaded_image = InMemoryUploadedFile(
        img_io,
        None,
        file_title,
        "img/jpeg",
        img_io.getbuffer().nbytes,
        None
    )

    # files = {"image": (file_title, img_io.getvalue(), 'image/jpeg')}
    data = {
        "image": uploaded_image,
        "title": file_title, 
        "caption": "a bottle image",
        'slug': unique_slug,
    }
    return data


def capture_and_upload(camera, gallery_title):
    if camera['handle'] is None:
        img_io = get_random_image(gallery_title)
    else:
        img_io = get_one_image(camera)
    data = prepare_one_image(img_io, gallery_title, camera['camera_info'])
    # logging.info(f"{gallery_title}: get one immage")
    gallery = Gallery.objects.get(title=gallery_title)
    photo = Photo(**data)
    photo.save()
    gallery.photos.add(photo)
    gallery.save()
    img_info = {"url": photo.image.url, "thumbnail": photo.get_display_url(), "title": photo.title}
    return img_info

async def capture_and_upload_async(camera, gallery_title):
    # 将同步函数转换为异步函数并调用
    img_info = await sync_to_async(capture_and_upload)(camera, gallery_title)
    return img_info


async def websocket_client(camera, gallery_title, uri):
    try:
        async with websockets.connect(uri) as websocket:
            # send id
            if camera['handle'] is None:
                message = {"client_id": gallery_title, "update": 1}
            else:
                message = {"client_id": gallery_title}
            await websocket.send(json.dumps(message))
            response = await websocket.recv()
            logging.info(f"0< {response}")

            try:
                # get camera_id from ws server
                response = json.loads(response)
                gallery_title = response['client_id']
                logging.info(f"client_id updated: {gallery_title}")
            except Exception as e:
                logging.info(f"init connect error: {e}")


            while True:
                message = await websocket.recv()
                logging.info(f"< {message}")

                if message == "stop":
                    logging.info("Stopping as per 'stop' signal.")
                    break

                elif message == "trig":
                    # logging.info("Capturing and uploading image.")
                    loop = asyncio.get_running_loop()
                    img_info = await loop.run_in_executor(None, capture_and_upload, camera, gallery_title)

                    img_info.update({"target": "web",
                                     "gallery_id": gallery_title,
                                     "updated": 1
                                     })
                    await websocket.send(json.dumps(img_info));
    except ConnectionClosed:
        logging.info("ws closed")
    except Exception as e:
        logging.info(f"An unexpected error: {e}")


async def main(camera:dict, gallery_title:str, ws_uri: str):
    await websocket_client(camera, gallery_title, ws_uri)


def run_asyncio_camera_loop(camera_sn: str, batch_number:str, ws_uri:str):
    # start camera, and load configure
    camera = {}
    if len(camera_sn) == 0:
        camera = {"handle": None, 'camera_info': {"roi0": [], "roi1": [], "roi0_disabled": True, "roi1_disabled": True}}
        gallery_title = batch_number
        asyncio.run(main(camera, gallery_title, ws_uri))
        logging.info("============================process close ======================")

    else:

        try:
            camera_list = get_devInfo_list()
            for camera_info in camera_list:
                if camera_info.acSn.decode('utf8') == camera_sn:
                    camera_res = initialize_cam(camera_info)
                    camera = dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                      camera_res))
                    break
            # load default configure
            configure_file = configure_dir / camera_sn / "setted_configure.json"
            if configure_file.is_file():
                config_dict = json.load(open(str(configure_file), "r"))
                set_camera_parameter(camera['handle'], **config_dict)
            camera_info = get_camera_parameters(camera['handle'], camera['cap'])
            camera.update({'camera_info': camera_info})

            camera_name = camera['camera_info']['name']
            camera_ord = int(camera_name.split("_")[-1])
            camera_ord = 0 if (camera_ord > 18 or camera_ord < 0) else camera_ord
            gallery_title = f"{batch_number}_{camera_ord}"

            asyncio.run(main(camera, gallery_title, ws_uri))
        except Exception as e:
            logging.info(f"camera process error: {str(e)}")

        finally:
            logging.info("==================process quit=====================")
            if camera['handle'] is not None:
                close_camera(camera['handle'], camera['pb'])

