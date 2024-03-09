import asyncio
import multiprocessing
from time import sleep
import websockets

from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image, softTrigger

from multiprocessing import shared_memory
import numpy as np
import json
import io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from camera.consumers import configure_dir
from datetime import datetime
import uuid
import requests
from django.core.files.base import ContentFile
import io
import uuid
from datetime import datetime
from django.core.files.base import ContentFile
import asyncio
import time

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # 配置日志级别
class AsyncTaskManager:
    def __init__(self):
        self.tasks = []

    async def add_task(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        try:
            await task
        except asyncio.CancelledError:
            # 处理任务取消
            pass
        finally:
            self.tasks.remove(task)

    async def stop_all(self):
        for task in self.tasks:
            if task is not asyncio.current_task():
                task.cancel()
            else:
                await task
        await asyncio.gather(*self.tasks, return_exceptions=True)

async_task_manager = AsyncTaskManager()

def prepare_one_image(batch_number, img_io, camera_info):
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
    file_title = f"{batch_number}_{formatted_time}_{roi_str}.jpg"

    files = {"image": (file_title, img_io.getvalue(), 'image/jpeg')}
    data = {
        "title": file_title, 
        "caption": "a solar image",
        "batch_number": batch_number, 
        'slug': unique_slug
    }
    return files, data

def upload_one_image(files, data):
    url = "http://127.0.0.1:8000/api/gallery/upload/"
    response = requests.post(url, files=files, data=data, timeout=1)
    return response

async def async_upload_one_image(files, data):
    url = "http://127.0.0.1:8000/api/gallery/upload/"

    # 使用httpx的异步客户端发送请求
    async with httpx.AsyncClient() as client:
        response = await client.post(url, files=files, data=data)
    return response


async def read_register_value(register):
    await asyncio.sleep(1)  # 模拟IO操作
    return 1  # 示例：模拟寄存器值

executor = ThreadPoolExecutor(max_workers=1)

async def check_event(stop_event):
    """在后台线程中检查事件状态，避免阻塞异步循环"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, stop_event.is_set)



async def monitor_registers(batch_number, camera, register, stop_event):
    # 使用asyncio.Event替代全局变量控制循环
    should_stop = asyncio.Event()

    async def check_event():
        while not stop_event.is_set():
            await asyncio.sleep(1)
        print("monitor stopping")
        should_stop.set()  # 设置事件，通知循环停止

    # 启动检查事件的任务
    asyncio.create_task(check_event())

    while not should_stop.is_set():  # 使用Event的状态来控制循环
        try:
            register_value = await read_register_value(register)
            if register_value == 1:
                # softTrigger
                error_code = softTrigger(camera['handle'])
                # get one frame
                pb, FH = get_one_frame(camera['handle'], camera['pb'])
                frame = image_to_numpy(pb, FH)
                frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
                frame = Image.fromarray(frame.astype(np.uint8))
                buffer = io.BytesIO()
                frame.save(buffer, format='JPEG')
                image, data = prepare_one_image(batch_number, buffer, camera['camera_info'])
                upload_one_image(image, data)
            await asyncio.sleep(0.01)  # sleep 10ms
        except Exception as e:
            logger.error(f"monitor error: {str(e)}")
            # logger.error(f"Exception type: {type(e).__name__}")
            # logger.error("Traceback:", exc_info=True)


# 异步主函数
async def main(batch_number, camera, register, stop_event):
    plc_trigger_task = asyncio.create_task(monitor_registers(batch_number, camera, register, stop_event))
    await plc_trigger_task


def run_asyncio_camera_loop(batch_number, camera_sn: str, stop_event):
    # start camera, and load configure
    camera = None
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

        asyncio.run(main(batch_number, camera, 0, stop_event))
    except Exception as e:
        print(f"camera process error: {str(e)}")

    finally:
        if camera:
            close_camera(camera['handle'], camera['pb'])

