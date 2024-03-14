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
import time
from pathlib import Path
from productionImages.models import ProductBatchV2
from photologue.models import Gallery



current_dir = Path(__file__).resolve().parent
configure_dir = current_dir / 'configure'
class cameraManager:
    def __init__(self) -> None:
        self.camera_process = {}
        self.current_camera = {}
        self.camera_sn_list = []
        self.camera_dict = {}

    def init_camera_configure(self, sn):
        camera_config_dir = configure_dir / sn
        camera_config_dir.mkdir(parents=True, exist_ok=True)
        # 4 configures
        for i in range(4):
            config_f = camera_config_dir / f"configure_{i:03d}.json"
            if not config_f.is_file():
                json.dump({}, open(str(config_f), "w"))

        configures = [str(f) for f in camera_config_dir.iterdir() if f.with_suffix(".json")]
        configures.sort()
        # default config
        success, default_configure = self.get_camera_info()

        # load setted_configure
        setted_config_f = camera_config_dir / f"setted_configure.json"
        if setted_config_f.is_file():
            setted_config = json.load(open(str(setted_config_f), 'r'))
            self.set_camera(setted_config)

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

    def _start_camera(self, sn):
        self.current_camera = {"sn": sn}
        # start
        camera_info = self.camera_dict.get(sn)
        if camera_info:
            name = camera_info.acFriendlyName.decode('utf8')
            camera_res = initialize_cam(camera_info)
            self.current_camera.update(dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                                camera_res)))
            self.current_camera.update({'name': name})
            print(f"camera: {sn} start success!")
            return
        else:
            print(f"camera: {sn} start failed!")

    def start_camera(self, sn):
        if sn not in self.camera_dict:
            return False, f"{sn} is not right sn"
        if self.current_camera.get("sn") is None:
            self._start_camera(sn)
        elif self.current_camera["sn"] != sn:
            self.close_camera()
            self._start_camera(sn)
        else:
            print(f"camera: {sn} started!")

        # confiugre
        self.init_camera_configure(sn)
        return True, f"{sn} started"

    def save_configure(self, config_f: str, config_dict = None):
        '''
        configure file start with "configure_"
        '''
        sn = self.current_camera.get('sn')
        if sn is None:
            return False, "please update camera list"

        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        config_f_path = configure_dir / sn / config_f
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
        config_f_path = configure_dir / sn / config_f
        if config_f_path.is_file():
            config_dict = json.load(open(str(config_f_path), "r"))
            success, message = self.set_camera(config_dict)
            return success, message
        else:
            return False, f"{str(config_f_path)} is not file"

    def update_camera_list(self, start_default=True):
        camera_list = get_devInfo_list()
        self.camera_dict = {camera_info.acSn.decode('utf8'): camera_info for camera_info in camera_list}
        self.camera_sn_list = list(self.camera_dict.keys())
        # set default camera
        if start_default and len(self.camera_sn_list):
            self.start_camera(self.camera_sn_list[0])

    def close_camera(self):
        if self.current_camera.get("sn") is not None:
            close_camera(self.current_camera['handle'], self.current_camera['pb'])
            print(f"{self.current_camera['sn']} closed")
            self.current_camera = {}

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
        frame = Image.fromarray(frame.astype(np.uint8))
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG')
        return True, buffer

    def get_camera_info(self):
        camera = self.current_camera
        try:
            camera_info = get_camera_parameters(camera['handle'], camera['cap'])
            return True, camera_info
        except Exception as e:
            return False, str(e)

    def set_camera(self, parameters: dict):
        camera = self.current_camera
        if camera.get("sn") is None:
            return False, "please update camera list"
        set_camera_parameter(camera['handle'], **parameters)
        camera_info = self.get_camera_info()
        return True, camera_info


camera_manager = cameraManager()



class CameraStreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("connected")
        self.camera_feed_task = None
        self.preview = False
        self.product_show = False
        self.camera_last_photo = []
        self.gallerys = []
        self.product_show_task = None

    async def init_product_show(self, batch_number):
        self.product_show = True
        self.gallerys = []
        productureBatch = ProductBatchV2.objects.get(batch_number=batch_number)
        camera_num = productureBatch.camera_num
        for i in range(camera_num):
            gallery = Gallery.objects.get(title=f"{batch_number}_{i}")
            self.gallerys.append(gallery)
            self.camera_last_photo.append(None)



    async def receive(self, text_data=None, bytes_data=None):
        # 这里可以根据需要处理接收到的数据
        print(f"received data: {text_data}, bytes: {bytes_data}")
        text_data_json = json.loads(text_data)
        self.trigger_mode = text_data_json.get('trigger_mode')

        product_show = text_data_json.get("product_show")
        if product_show is not None:
            batch_number = text_data_json.get("batch_number")
            if batch_number is None:
                print("batch_number can't be found")
                return
            await self.init_product_show(batch_number)
            asyncio.create_task(self.product_feed())
            return

        if camera_manager.current_camera.get('sn') is None:
            print(f"current camera is None")
            return 

        if "start_preview" in text_data_json and (self.trigger_mode is not None):
            if int(self.trigger_mode) == 0 and self.camera_feed_task is None:
                self.preview = True
                self.camera_feed_task = asyncio.create_task(self.camera_feed())
                print("ws task started")

        elif "stop_preview" in text_data_json:
            self.preview = False
            if self.camera_feed_task is not None:
                await self.camera_feed_task
                self.camera_feed_task = None

        elif self.trigger_mode and int(self.trigger_mode) == 1:
            if self.camera_feed_task:
                # close task
                self.preview = False
                if self.camera_feed_task is not None:
                    await self.camera_feed_task
                    self.camera_feed_task = None

            # trigger
            if "soft_trigger" in text_data_json:
                success, buffer = camera_manager.soft_trigger()
                if not success:
                    print("ws:: soft_trigger failed: ", buffer)
                else:
                    await self.send_frame(buffer)

    async def send_frame(self, frame):
        if isinstance(frame, io.BytesIO):
            frame = base64.b64encode(frame.getvalue()).decode('utf-8')
        try:
            await self.send(text_data=json.dumps({"frame": frame}))
        except:
            print("send frame error")

    async def camera_feed(self):
        try:
            frame_num = 0
            t0 = time.time()
            while self.preview:
                t0_p = time.time()
                frame = await self.get_camera_frame()
                # print(f"get frame cost: {time.time() - t0_}")
                await self.send_frame(frame)  # 调用send_frame发送图像数据
                if frame_num % 100 == 99:
                    print(f"frame rate: {100 / (time.time() - t0)}")
                    t0 = time.time()
                frame_num += 1
                wait_time = 0.05 - (time.time() - t0_p)  # 20fps
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            print("camera feed cancelled")
            pass

    async def product_feed(self):
        try:
            while self.product_show:
                for i, gallery in enumerate(self.gallerys):
                    try:
                        photo = gallery.photos.latest("date_added")
                        if photo.title != self.camera_last_photo[i]:
                            row, col = i % 3, i // 3
                            data = {"url": photo.image.url, "thumbnail": photo.get_display_url(), "title": photo.title, "img_id": f"r-{row}-c-{col}"}
                            self.camera_last_photo[i] = photo.title
                            await self.send(text_data=json.dumps(data))
                    except Exception as e:
                        print(f"product feed error: {e}")
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("product feed cancelled")

    async def disconnect(self, close_code):
        self.product_show = False

        # 取消之前创建的任务
        if self.camera_feed_task:
            self.preview = False
            self.camera_feed_task.cancel()
            # 等待任务被取消，确保资源被适当清理
            try:
                await self.camera_feed_task
            except asyncio.CancelledError:
                print('error from disconnect')

        # close camera
        camera_manager.close_camera()

    async def get_camera_frame(self):
        success, buffer = camera_manager.get_one_frame()
        if not success:
            print(f"ws:: get_camera_frame failed: ", buffer)
            frame = np.random.randint(0, 255, (640, 640), dtype=np.uint8)
            frame = Image.fromarray(frame)
            buffer = io.BytesIO()
            frame.save(buffer, format='JPEG')
        return buffer

