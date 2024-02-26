# cameraapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
import base64
import time
from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image
import asyncio
from PIL import Image
import numpy as np
import io
import cv2
from multiprocessing import Process, Pipe, shared_memory
import time


def camera_process(camera_sn: str, conn_in, conn_out, shm_name):
    empty_loop_start = time.time()
    camera_list = get_devInfo_list()
    for camera_info in camera_list:
        if camera_info.acSn.decode('utf8') == camera_sn:
            camera_res = initialize_cam(camera_info)
            camera = dict(zip(["handle", "cap", "mono", "bs", "pb"],
                              camera_res))
            
            existing_shm = shared_memory.SharedMemory(name=shm_name)
            frame_buffer = np.ndarray((camera['bs'], ), dtype=np.uint8, buffer=existing_shm.buf)
            break

    while True:
        if conn_in.poll():  # 检查管道是否有待读取的消息
            empty_loop_start = time.time()
            cmd_dict = conn_in.recv()  # 接收命令
            if "stop" in cmd_dict:
                close_camera(camera['handle'], camera['pb'])
                continue
            if 'set' in cmd_dict:
                print(cmd_dict)
                set_camera_parameter(camera['handle'], **cmd_dict['set'])
                parameters = get_camera_parameters(camera['handle'], camera['cap'])
                conn_out.send(parameters)
                continue
            if 'get' in cmd_dict:
                parameters = get_camera_parameters(camera['handle'], camera['cap'])
                conn_out.send(parameters)
                continue
            if 'frame' in cmd_dict:
                pb, FH = get_one_frame(camera['handle'], camera['pb'])
                frame = image_to_numpy(pb, FH)
                h, w, c = frame.shape
                frame = frame.flatten()
                frame_buffer[0:len(frame)] = frame
                conn_out.send((h, w, c))
                continue
            if 'grab' in cmd_dict:
                PB, FH = get_one_frame(camera['handle'], camera['pb'])
                save_image(camera['handle'], PB, FH, cmd_dict['path'], cmd_dict['quality'], img_type='bmp')
                conn_out.send(1)
                continue
        time.sleep(0.03)  # 模拟工作负载
        if time.time() - empty_loop_start > 120:
            close_camera(camera['handle'], camera['pb'])
            break

class cameraManager:

    def __init__(self) -> None:
        self.camera_dict = {}
        self.camera_process = {}
        self.conn_in_dict, self.conn_out_dict = {}, {}

    def update_camera_list(self):

        camera_list = get_devInfo_list()
        for camera_info in camera_list:
            sn = camera_info.acSn.decode('utf8')
            name = camera_info.acFriendlyName.decode('utf8')
            if sn not in self.camera_dict:
                self.camera_dict[sn] = {'name': name}
                bs = 3000 * 3000 * 3
                self.shm = shm = shared_memory.SharedMemory(create=True, size=bs)
                self.camera_dict[sn]['buffer'] = np.ndarray((bs, ), dtype=np.uint8, buffer=shm.buf)

                # start process
                parent_conn_in, child_conn_in = Pipe() 
                parent_conn_out, child_conn_out = Pipe() 
                p = Process(target=camera_process,
                            args=(sn, child_conn_in, parent_conn_out, self.shm.name))
                p.start()
                self.camera_dict[sn].update({'process': p, 'conn_in': parent_conn_in,
                                             'conn_out': child_conn_out})

    def close_all_cameras(self):
        for _, camera_i in self.camera_dict.items():
            camera_i['conn_in'].send({'stop': 1})
            camera_i['process'].join()

    def get_one_frame(self, camera_id: str):
        camera = self.camera_dict.get(camera_id)
        if camera is None:
            return False, f"camera_id: {camera_id} is wrong"
        camera['conn_in'].send({'frame': 1})
        h, w, c = camera['conn_out'].recv()

        frame = camera['buffer'][:(h * w * c)].reshape(h, w, c)
        frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
        frame = Image.fromarray(frame.astype(np.uint8))
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG')
        return True, buffer

    def grab(self, camera_id: str, path: str, quality=100):
        camera = self.camera_dict.get(camera_id)
        if camera is None:
            return False, f"camera_id: {camera_id} is wrong"
        camera['conn_in'].send({'grab': 1, 'path': path, 'quality': quality})
        success = camera['conn_out'].recv()
        return True, success

    def get_camera_info(self, camera_id: str):
        camera = self.camera_dict.get(camera_id)
        if camera is None:
            return False, f"camera_id: {camera_id} is wrong"

        camera['conn_in'].send({"get": 1})
        camera_info = camera['conn_out'].recv()
        return True, camera_info

    def set_camera(self, camera_id: str, parameters: dict):
        camera = self.camera_dict.get(camera_id)
        if camera is None:
            return False, f"camera_id: {camera_id} is wrong"

        camera['conn_in'].send({"set": parameters})
        camera_info = camera['conn_out'].recv()
        return True, camera_info



camera_manager = cameraManager()


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
            print("send frame error")

    async def camera_feed(self, camera_id):
        try:
            frame_num = 0
            t0 = time.time()
            while True:
                # t0_ = time.time()
                frame = await self.get_camera_frame(camera_id)  # 假设这个方法获取最新的相机帧
                # print(f"get frame cost: {time.time() - t0_}")
                await self.send_frame(frame)  # 调用send_frame发送图像数据
                if frame_num % 100 == 99:
                    print(f"frame rate: {100 / (time.time() - t0)}")
                    t0 = time.time()
                frame_num += 1
                await asyncio.sleep(0.08)  # 模拟等待时间，这里假设是10帧/秒
        except asyncio.CancelledError:
            print("camera feed cancelled")
            pass

    async def disconnect(self, close_code):
        # 取消之前创建的任务
        self.camera_feed_task.cancel()
        # 等待任务被取消，确保资源被适当清理
        try:
            await self.camera_feed_task
        except asyncio.CancelledError:
            print('error from disconnect')

    async def get_camera_frame(self, camera_id):
        success, buffer = camera_manager.get_one_frame(camera_id)
        if not success:
            frame = np.random.randint(0, 255, (640, 640), dtype=np.uint8)
            frame = Image.fromarray(frame)
            buffer = io.BytesIO()
            frame.save(buffer, format='JPEG')

        return base64.b64encode(buffer.getvalue()).decode('utf-8')
