# cameraapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
from pathlib import Path
import random
import cv2
import base64
import time


class CameraStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # 启动一个后台任务模拟不断从相机获取数据并发送
        self.camera_feed_task = asyncio.create_task(self.camera_feed())
        print("connected")

    async def receive(self, text_data=None, bytes_data=None):
        # 这里可以根据需要处理接收到的数据
        print(f'received data: {text_data}, bytes: {bytes_data}')

    async def send_frame(self, frame):
        # 假设frame是已经处理好的图像数据
        await self.send(text_data=json.dumps({'frame': frame}))

    async def camera_feed(self):
        try:
            frame_num = 0
            t0 = time.time()
            while True:
                frame = self.get_camera_frame()  # 假设这个方法获取最新的相机帧
                await self.send_frame(frame)  # 调用send_frame发送图像数据
                if frame_num % 100 == 99:
                    print(f"frame rate: {100 / (time.time() - t0)}")
                    t0 = time.time()
                frame_num += 1
                await asyncio.sleep(0.01)  # 模拟等待时间，这里假设是10帧/秒
        except asyncio.CancelledError:
            print("camera feed cancelledError")
            pass

    def get_camera_frame(self):
        img_dir = Path("/home/liuyang/datasets/sod4bird/images_6x6/images/")
        img_list = [str(img_f) for img_f in img_dir.iterdir() if img_f.suffix.lower() in ['.jpg', '.bmp', '.png']]
        img_id = random.randint(0, len(img_list) - 1)
        with open(img_list[img_id], "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def disconnect(self, close_code):
        # 取消之前创建的任务
        self.camera_feed_task.cancel()
        # 等待任务被取消，确保资源被适当清理
        try:
            await self.camera_feed_task
        except asyncio.CancelledError:
            pass

