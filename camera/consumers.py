# cameraapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
import base64
import time
from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image, softTrigger
import asyncio
from PIL import Image
import numpy as np
import io
import cv2
from multiprocessing import Process, Pipe, shared_memory
import time
from pathlib import Path
from productionImages.models import upload_one_image


current_dir = Path(__file__).resolve().parent
class cameraManager:
    def __init__(self) -> None:
        self.camera_dict = {}
        self.camera_process = {}
        self.conn_in_dict, self.conn_out_dict = {}, {}
        self.pipe_lock = asyncio.Lock()
        self.configure_dir = current_dir / 'configure'
        self.current_camera = {}
        self.camera_list = []

    def init_camera_configure(self, sn):
        camera_config_dir = self.configure_dir / sn
        camera_config_dir.mkdir(parents=True, exist_ok=True)
        # 4 configures
        for i in range(4):
            config_f = camera_config_dir / f"configure_{i:03d}.json"
            if not config_f.is_file():
                with open(str(config_f), 'w') as f:
                    pass

        configures = [str(f) for f in camera_config_dir.iterdir() if f.with_suffix(".json")]
        configures.sort()
        # default config
        success, default_configure = self.get_camera_info()

        self.current_camera.update({"configure_f": configures, 'default_config': default_configure})

    def reset_configure(self, config_f):
        sn = self.current_camera.get('sn')
        if sn is None:
            return False, "please update camera list"

        success, _ = self.save_configure(config_f, self.current_camera['default_config'])
        if success:
            return True, "reset OK"
        else:
            return False, "reset failed"

    def _start_camera(self, sn, name):
        self.current_camera = {"sn": sn, "name": name}
        # start
        for camera_info in self.camera_list:
            if camera_info.acSn.decode('utf8') == sn:
                camera_res = initialize_cam(camera_info)
                self.current_camera.update(dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                                    camera_res)))
                return

    def start_camera(self, sn, name):
        if self.current_camera.get("sn") is None:
            self._start_camera(sn, name)
        elif self.current_camera["sn"] != sn:
            self.close_camera()
            self._start_camera(sn, name)
        else:
            print(f"camera: {sn} started!")

        # confiugre
        self.init_camera_configure(sn)

    def save_configure(self, config_f: str, config_dict = None):
        '''
        configure file start with "configure_"
        '''
        sn = self.current_camera.get('sn')
        if sn is None:
            return False, "please update camera list"

        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        config_f_path = self.configure_dir / sn / config_f
        if config_dict is None:
            success, config_dict = self.get_camera_info()
        else:
            success = True

        if success:
            json.dump(config_dict, open(str(config_f_path), "w"))
            return True, "saved success"
        else:
            return success, "save configure failed"

    def load_configure(self, config_f: str):
        sn = self.current_camera.get('sn')
        if sn is None:
            return False, "please update camera list"

        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        config_f_path = self.configure_dir / sn / config_f
        if config_f_path.is_file():
            config_dict = json.load(open(str(config_f_path), "r"))
            success, message = self.set_camera(config_dict)
            self.camera_dict[sn].update({'roi': config_dict['roi']})
            return success, message
        else:
            return False, f"{str(config_f_path)} is not file"

    def update_camera_list(self):
        self.camera_list = get_devInfo_list()
        # set default camera
        if len(self.camera_list):
            camera_info = self.camera_list[0]
            sn = camera_info.acSn.decode('utf8')
            name = camera_info.acFriendlyName.decode('utf8')
            self.start_camera(sn, name)

    def close_camera(self):
        if self.current_camera.get("sn") is not None:
            close_camera(self.current_camera['handle'], self.current_camera['pb'])

    def get_one_frame(self):
        if self.current_camera.get('sn') is None:
            return False, "please update camera list"
        pb, FH = get_one_frame(self.current_camera['handle'], self.current_camera['pb'])
        frame = image_to_numpy(pb, FH)
        frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
        frame = Image.fromarray(frame.astype(np.uint8))
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG')
        return True, buffer

    def grab(self, path: str, quality=100):
        if self.current_camera.get('sn') is None:
            return False, "please update camera list"
        PB, FH = get_one_frame(self.current_camera['handle'], self.current_camera['pb'])
        save_image(self.current_camera['handle'], PB, FH, path, quality, img_type='bmp')
        return True, True

    def soft_trigger(self):
        if self.current_camera.get('sn') is None:
            return False, "please update camera list"
        camera = self.current_camera
        error_code = softTrigger(camera['handle'])
        # get one frame
        pb, FH = get_one_frame(camera['handle'], camera['pb'])
        frame = image_to_numpy(pb, FH)
        frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
        if len(camera['roi']):
            mask = np.zeros(frame.shape[0:2], dtype=np.uint8)
            for roi in camera['roi']:
                x0, y0, x1, y1 = np.array(roi).astype(np.int32)
                mask[y0:y1, x0:x1] = 1
            frame[mask == 0] = 0
        frame = Image.fromarray(frame.astype(np.uint8))
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG')
        return True, buffer

    def get_camera_info(self):
        camera = self.current_camera
        camera_info = get_camera_parameters(camera['handle'], camera['cap'])
        camera_info.update({"roi": camera['roi']})
        return True, camera_info

    def set_camera(self, parameters: dict):
        camera = self.current_camera
        set_camera_parameter(camera['handle'], **parameters)
        camera_info = get_camera_parameters(camera['handle'], camera['cap'])
        return True, camera_info


camera_manager = cameraManager()



class CameraStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("connected")
        self.camera_feed_task = None

    async def receive(self, text_data=None, bytes_data=None):
        # 这里可以根据需要处理接收到的数据
        print(f"received data: {text_data}, bytes: {bytes_data}")
        text_data_json = json.loads(text_data)
        self.camera_id = camera_id = text_data_json['camera_id']

        self.trigger_mode = text_data_json['trigger_mode']
        if int(self.trigger_mode) == 0:
            self.camera_feed_task = asyncio.create_task(self.camera_feed(camera_id))
        elif int(self.trigger_mode) == 1:
            if self.camera_feed_task:
                # close task
                self.camera_feed_task.cancel()
                # 等待任务被取消，确保资源被适当清理
                try:
                    await self.camera_feed_task
                except asyncio.CancelledError:
                    print('error from disconnect')

            # trigger
            success, buffer = camera_manager.soft_trigger(camera_id)
            if not success:
                print("not success")
            else:
                await self.send(text_data=json.dumps(
                    {"frame": base64.b64encode(buffer.getvalue()).decode('utf-8')}))


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
        if self.camera_feed_task:
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
