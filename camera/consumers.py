# cameraapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
from pathlib import Path
import random
import cv2
import base64
import time
from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image
import asyncio
from PIL import Image
import numpy as np
import io
from multiprocessing import Process, Pipe
import time


def camera_process(camera: dict, conn_in, conn_out):
    while True:
        if conn_in.poll():  # 检查管道是否有待读取的消息
            cmd_dict = conn_in.recv()  # 接收命令
            if "stop" in cmd_dict:
                close_camera(camera['handle'], camera['pb'])
                continue
            if 'set' in cmd_dict:
                set_camera_parameter(cmd_dict['set'])
                continue
            if 'get' in cmd_dict:
                parameters = get_camera_parameters(camera['handle'], camera['cap'])
                conn_out.send(parameters)
                continue
            if 'frame' in cmd_dict:
                frame = image_to_numpy(*get_one_frame(camera['handle'], camera['pb']))
                frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
                frame = Image.fromarray(frame.astype(np.uint8))
                buffer = io.BytesIO()
                frame.save(buffer, format='JPEG')
                conn_out.send(buffer)
                continue
            if 'grab' in cmd_dict:
                PB, FH = get_one_frame(camera['handle'], camera['pb'])
                save_image(camera['handle'], PB, FH, cmd_dict['path'], cmd_dict['quality'], img_type='bmp')
                conn_out.send(1)
        time.sleep(0.03)  # 模拟工作负载

class cameraManager:
    def __init__(self) -> None:
        self.update_camera_list()
        self.camera_process = {}
        self.conn_in_dict, self.conn_out_dict = {}, {}

    def update_camera_list(self):
        self.camera_dict = {} if self.camera_dict is None else self.camera_dict

        camera_list = get_devInfo_list()
        camera_list = [{'dev_info': dev_info} for dev_info in camera_list]
        camera_ids = [f'camera_{i}' for i in range(len(camera_list))]
        for camera_id, camera_info in zip(camera_ids, camera_list):
            if camera_id not in self.camera_dict:
                camera_res = initialize_cam(camera_info['dev_info'])
                camera_info.update(dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                            camera_res)))
                self.camera_dict[camera_id] = camera_info

    def start_camera_process(self):
        for camera_id in self.camera_dict:
            if camera_id not in self.camera_process:
                parent_conn_in, child_conn_in = Pipe() 
                parent_conn_out, child_conn_out = Pipe() 
                self.camera_process[camera_id] = Process(target=camera_process,
                                                         args=(self.camera_dict[camera_id],
                                                               child_conn_in, parent_conn_out))
                self.camera_process[camera_id].start()
                self.conn_in_dict[camera_id] = parent_conn_in
                self.conn_out_dict[camera_id] = child_conn_out

    def close_all_cameras(self):
        for _, conn_in in self.conn_in_dict.items():
            conn_in.send({'stop': 1})
        for _, p in self.camera_process.items():
            p.join()

    def get_one_frame(self, camera_id: str):
        camera = self.camera_dict.get(camera_id)
        if camera is None:
            print(f"camera_id: {camera_id} is wrong")
            return
        self.conn_in_dict[camera_id].send({'frame': 1})
        frame = self.conn_out_dict['camera_id'].recv()
        return frame

    def grab(self, camera_id: str, path: str, quality=100):
        camera = self.camera_dict.get(camera_id)
        if camera is None:
            print(f"camera_id: {camera_id} is wrong")
            return
        self.conn_in_dict[camera_id].send({'grab': 1, 'path': path, 'quality': quality})
        success = self.conn_out_dict['camera_id'].recv()
        return success


camera_manager = cameraManager()

camera_lock = asyncio.Lock()

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
        buffer = camera_manager.get_one_frame(camera_id)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
