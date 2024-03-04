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


current_dir = Path(__file__).resolve().parent
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

    try:
        while True:
            if conn_in.poll():  # 检查管道是否有待读取的消息
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
                if 'trigger' in cmd_dict:
                    # TODO:
                    error_code = softTrigger(camera['handle'])
                    # get one frame
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
    except Exception as e:
        print(f"camera process error: {e}")

    finally:
        if camera:
            close_camera(camera['handle'], camera['pb'])

class cameraManager:

    def __init__(self) -> None:
        self.camera_dict = {}
        self.camera_process = {}
        self.conn_in_dict, self.conn_out_dict = {}, {}
        self.pipe_lock = asyncio.Lock()
        self.configure_dir = current_dir / 'configure'

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
        success, default_configure = self.get_camera_info(sn)

        self.camera_dict[sn].update({"configure_f": configures, 'default_config': default_configure})

    def reset_configure(self, sn, config_f):
        success, _ = self.save_configure(sn, config_f, self.camera_dict[sn]['default_config'])
        if success:
            return True, "reset OK"
        else:
            return False, "reset failed"


    def start_process(self, sn, name):
        self.camera_dict[sn] = {'name': name}
        bs = 3000 * 3000 * 3
        self.shm = shm = shared_memory.SharedMemory(create=True, size=bs)
        self.camera_dict[sn]['buffer'] = np.ndarray((bs, ), dtype=np.uint8, buffer=shm.buf)
        self.camera_dict[sn]['roi'] = []

        # start process
        parent_conn_in, child_conn_in = Pipe() 
        parent_conn_out, child_conn_out = Pipe() 
        p = Process(target=camera_process,
                    args=(sn, child_conn_in, parent_conn_out, self.shm.name))
        p.start()
        self.camera_dict[sn].update({'process': p, 'conn_in': parent_conn_in,
                                     'conn_out': child_conn_out})
        # confiugre
        self.init_camera_configure(sn)

    def save_configure(self, sn: str, config_f: str, config_dict = None):
        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        config_f_path = self.configure_dir / sn / config_f
        if config_dict is None:
            success, config_dict = self.get_camera_info(sn)
        else:
            success = True

        if success:
            json.dump(config_dict, open(str(config_f_path, "w")))
            return True, "saved success"
        else:
            return success, "save configure failed"

    def load_configure(self, sn: str, config_f: str):
        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        config_f_path = self.configure_dir / sn / config_f
        if config_f_path.is_file():
            config_dict = json.load(open(str(config_f_path, "r")))
            success, message = self.set_camera(sn, config_dict)
            self.camera_dict[sn].update({'roi': config_dict['roi']})
            return success, message
        else:
            return False, f"{str(config_f_path)} is not file"

    def update_camera_list(self):
        camera_list = get_devInfo_list()
        for camera_info in camera_list:
            sn = camera_info.acSn.decode('utf8')
            name = camera_info.acFriendlyName.decode('utf8')
            if sn not in self.camera_dict or (not self.camera_dict[sn]['process'].is_alive()):
                self.start_process(sn, name)

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

    def soft_trigger(self, camera_id: str):
        camera = self.camera_dict.get(camera_id)
        if camera is None:
            return False, f"camera_id: {camera_id} is wrong"
        camera['conn_in'].send({'trigger': 1})
        
        h, w, c = camera['conn_out'].recv()
        frame = camera['buffer'][:(h * w * c)].reshape(h, w, c)
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

    def get_camera_info(self, camera_id: str):
        camera = self.camera_dict.get(camera_id)
        if camera is None:
            return False, f"camera_id: {camera_id} is wrong"

        camera['conn_in'].send({"get": 1})
        camera_info = camera['conn_out'].recv()
        camera_info.update({"roi": camera['roi']})
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
        self.camera_feed_task = None

    async def receive(self, text_data=None, bytes_data=None):
        # 这里可以根据需要处理接收到的数据
        print(f"received data: {text_data}, bytes: {bytes_data}")
        text_data_json = json.loads(text_data)
        self.camera_id = camera_id = text_data_json['camera_id']
        self.batch_num = text_data_json.get("batch_number")
        if self.batch_num is not None:
            print(f"receive batch number: {self.batch_num}")
            return
            
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
