# cameraapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
from pathlib import Path
import random
import cv2
import base64
import time
from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera
import asyncio
from PIL import Image
import numpy as np
import io

camera_lock = asyncio.Lock()
camera_dict = {}


def update_camera_list():
    global camera_dict
    camera_list = get_devInfo_list()
    camera_list = [{'dev_info': dev_info} for dev_info in camera_list]
    camera_ids = [f'camera_{i}' for i in range(len(camera_list))]
    for camera_id, camera_info in zip(camera_ids, camera_list):
        if camera_id not in camera_dict:
            camera_dict[camera_id] = camera_info
    return camera_dict

update_camera_list()

class CameraStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("connected")

    async def receive(self, text_data=None, bytes_data=None):
        # 这里可以根据需要处理接收到的数据
        print(f"received data: {text_data}, bytes: {bytes_data}")
        text_data_json = json.loads(text_data)
        self.camera_id = camera_id = text_data_json['camera_id']
        self.camera_feed_task = asyncio.create_task(self.camera_feed(camera_id))

    async def send_frame(self, frame):
        try:
            await self.send(text_data=json.dumps({"frame": frame}))
        except:
            print("camera feed cancelledError")
            pass

    async def camera_feed(self, camera_id):
        try:
            frame_num = 0
            t0 = time.time()
            while True:
                frame = await self.get_camera_frame(camera_id)  # 假设这个方法获取最新的相机帧
                await self.send_frame(frame)  # 调用send_frame发送图像数据
                if frame_num % 100 == 99:
                    print(f"frame rate: {100 / (time.time() - t0)}")
                    t0 = time.time()
                frame_num += 1
                await asyncio.sleep(0.01)  # 模拟等待时间，这里假设是10帧/秒
        except asyncio.CancelledError:
            print("camera feed cancelledError")
            pass

    async def disconnect(self, close_code):
        # 取消之前创建的任务
        self.camera_feed_task.cancel()
        # 等待任务被取消，确保资源被适当清理
        try:
            await self.camera_feed_task
        except asyncio.CancelledError:
            pass

    async def get_camera_frame(self, camera_id):
        frame = None
        if camera_id not in camera_dict:
            print(f"{camera_id} not in camera_dict: {list(camera_dict.keys())}")
            frame = np.random.randint(0, 255, (640, 640))
        else:
            if "handle" not in camera_dict[camera_id]:
                camera_res = initialize_cam(camera_dict[camera_id]['dev_info'])
                camera_dict[camera_id].update(dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                                       camera_res)))
                self.camera_handle = camera_dict[camera_id]['handle']
            frame = image_to_numpy(*get_one_frame(camera_dict[camera_id]['handle'],
                                                  camera_dict[camera_id]['pb']))
            if frame.shape[-1] == 1:
                frame = frame[:, :, 0]
        img = Image.fromarray(frame.astype('uint8'))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
