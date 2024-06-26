# cameraapp/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
import base64
import time
import asyncio
from PIL import Image
import numpy as np
import io
import time
from plc.plc_control import plcControl
from .camera_manager import cameraManager



class CameraStreamConsumer(AsyncWebsocketConsumer):

    camera_manager = cameraManager()
    async def connect(self):
        await self.accept()
        print("connected")
        self.camera_feed_task = None
        self.preview = False
        self.product_show = False
        self.camera_last_photo = []
        self.gallerys = []
        self.product_show_task = None
        self.plc_trigger_task = None
        self.batch_number = None
        self.plc_check_task = None
        self.plc_checking = False
        self.plc_trigger_checking = False
        self.plc_reg_vals = {}
        self.plc = plcControl()

    async def init_product_show(self, batch_number):
        self.product_show = True
        self.gallerys = []
        # productureBatch = ProductBatchV2.objects.get(batch_number=batch_number)
        # camera_num = productureBatch.camera_num
        camera_num = 18
        for i in range(camera_num):
            gallery = Gallery.objects.get(title=f"{batch_number}_{i}")
            self.gallerys.append(gallery)
            self.camera_last_photo.append(None)

    async def init_plc_check(self):
        self.plc.connect()
        self.plc_checking = True
        self.plc_reg_vals.update({"m": {}, "d": {}})
        for m in ['M202', 'M1', 'M11', 'M212', 'M4', 'M14']:
            self.plc_reg_vals['m'][m] = None

        for d in ['D850', 'D864', 'D856', 'D870', 'D814', 'D812']:
            self.plc_reg_vals['d'][d] = None


    async def stop_product_show(self):
        self.product_show = False
        if self.product_show_task is not None:
            self.product_show_task.cancel()
            await self.product_show_task
            self.product_show_task = None

    def check_sn(self, camera_sn):
        current_sn = self.camera_manager.get_sn()
        success, message = True, "success"
        if current_sn != camera_sn:
            success, message = self.camera_manager.start_camera(camera_sn)
        return success, message

    async def stop_plc_check(self):
        self.plc_checking = False
        if self.plc_check_task:
            self.plc_check_task.cancel()
            try:
                await self.plc_check_task
            except asyncio.CancelledError:
                print("plc cancelled")

    async def receive(self, text_data: str, bytes_data=None):
        print(f"received data: {text_data}, bytes: {bytes_data}")
        text_data_json = json.loads(text_data)
        camera_sn = text_data_json.get("sn")

        if "plc_trigger" in text_data_json:
            if self.plc_trigger_task is None:
                self.plc_trigger_task = asyncio.create_task(self.check_plc_trigger(camera_sn))

        if "get_camera_list" in text_data_json:
            self.camera_manager.update_camera_list(False)
            camera_ids = self.camera_manager.camera_sn_list
            camera_ids = ["---------"] if len(camera_ids) < 1 else camera_ids
            await self.send(json.dumps({"cameras": camera_ids}))
            return

        if "save_configure" in text_data_json:
            success, message = self.check_sn(camera_sn)
            if not success: print(message); return;
            config_f = text_data_json.get("config_f")
            success, message = self.camera_manager.save_configure(config_f)
            await self.send(json.dumps({"message": message}))
            return 

        if "load_configure" in text_data_json:
            success, message = self.check_sn(camera_sn)
            if not success: print(message); return;
            config_f = text_data_json.get("config_f")
            success, message = self.camera_manager.load_configure(config_f)
            await self.send(json.dumps({"message": message}))
            return

        if "reset_configure" in text_data_json:
            success, message = self.check_sn(camera_sn)
            if not success: print(message); return;
            config_f = text_data_json.get("config_f")
            success, message = self.camera_manager.reset_configure(config_f)
            await self.send(json.dumps({"message": message}))
            return

        if "get_camera_info" in text_data_json:
            success, message = self.check_sn(camera_sn)
            if not success: print(message); return;
            success, camera_info = self.camera_manager.get_camera_info()
            await self.send(json.dumps({"camera_info": camera_info}))
            return

        if "set_camera" in text_data_json:
            success, message = self.check_sn(camera_sn)
            if not success: print(message); return;
            params = text_data_json.get("params")
            success, camera_info = self.camera_manager.set_camera(params)
            await self.send(json.dumps({"message": camera_info}))
            return 

        plc_arb_w = text_data_json.get("plc-arb-w")
        if plc_arb_w and self.plc.client.connected:
            plc_arb_reg = text_data_json.get("plc-arb-reg")
            plc_arb_val = text_data_json.get("plc-arb-val")
            self.plc.set_reg(plc_arb_reg, plc_arb_val)
            return

        plc_arb_r = text_data_json.get("plc-arb-r")
        if plc_arb_r and self.plc.client.connected:
            plc_arb_reg = text_data_json.get("plc-arb-reg")
            success, val = self.plc.get_reg(plc_arb_reg)
            await self.send(json.dumps({"arb_success": success, "arb_val": val}))
            return

        check_plc = text_data_json.get("check_plc")
        if check_plc and not self.plc_checking:
            plc_reg = text_data_json.get("plc_reg")
            val = text_data_json.get("val")
            if plc_reg and self.plc.client.connected:
                self.plc.set_reg(plc_reg, val)
            self.plc_check_task = asyncio.create_task(self.check_plc_background())
            return

        plc_stop_check = text_data_json.get("plc_stop_check")
        if plc_stop_check:
            await self.stop_plc_check()
            return 

        trigger_mode = text_data_json.get('trigger_mode')
        trigger_mode = int(trigger_mode) if trigger_mode is not None else None
        if trigger_mode is not None:
            if trigger_mode != 2:
                # stop trigger checking
                if self.plc_trigger_task is not None:
                    self.plc_trigger_checking = False
                    await self.plc_trigger_task
                    self.plc_trigger_task = None

            if trigger_mode != 0:
                # stop
                if self.camera_feed_task is not None:
                    self.preview = False
                    await self.camera_feed_task
                    self.camera_feed_task = None

        if "soft_trigger" in text_data_json and trigger_mode == 1:
            message = ""
            success, buffer = self.camera_manager.soft_trigger(camera_sn)
            if not success:
                print("ws:: soft_trigger failed: ", buffer)
                message = buffer
            else:
                await self.send_frame(buffer)
                message = "soft trigger success"
            await self.send(json.dumps({"soft_trigger_return": 1, "message": message}))
            return

        if "soft_trigger" in text_data_json and trigger_mode == 2:
            print("plc trigger")
            if self.plc_trigger_task is None:
                print("plc trigger task")
                self.plc_trigger_task = asyncio.create_task(self.check_plc_trigger(camera_sn))
            return 

        if "start_preview" in text_data_json and trigger_mode == 0:
            if self.camera_feed_task is None:
                self.preview = True
                self.camera_feed_task = asyncio.create_task(self.camera_feed(camera_sn))
                print("ws task started")
            return


        if "stop_preview" in text_data_json:
            self.preview = False
            if self.camera_feed_task is not None:
                await self.camera_feed_task
                self.camera_feed_task = None



    async def send_frame(self, frame):
        if isinstance(frame, io.BytesIO):
            frame = base64.b64encode(frame.getvalue()).decode('utf-8')
        try:
            await self.send(text_data=json.dumps({"frame": frame}))
        except:
            print("send frame error")

    async def camera_feed(self, sn):
        try:
            frame_num = 0
            if sn != self.camera_manager.get_sn():
                success, message = self.camera_manager.start_camera(sn)
                if not success:
                    print(message)
                    return 
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
                else:
                    await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print("camera feed cancelled")
            pass

    async def check_plc_trigger(self, camera_sn):
        self.plc.connect()
        self.plc_trigger_checking = True
        message = ""
        while self.plc_trigger_checking:
            success, v = self.plc.get_M("M1")
            if success:
                if int(v) > 0:
                    self.plc_trigger_checking = False
                    success, buffer = self.camera_manager.soft_trigger(camera_sn)
                    if not success:
                        message = buffer
                        print("plc trigger failed: ", buffer)
                    else:
                        await self.send_frame(buffer)
                        message = "plc_trigger_success"
                    self.plc.set_M("M1", 0)
            await asyncio.sleep(0.01)
        await self.send(json.dumps({"plc_trigger_return":1, "message": message}))
        self.plc_trigger_task = None


    async def check_plc_background(self):
        await self.init_plc_check()
        while self.plc_checking:
            m_updated, d_updated = [], []
            plc_online = True
            for m in ['M202', 'M1', 'M11', 'M212', 'M4', 'M14']:
                old = self.plc_reg_vals['m'][m]
                success, v = self.plc.get_M(m)
                if success:
                    if old != v:
                        m_updated.append({"id": f"#{m}", "val": v})
                        self.plc_reg_vals['m'][m] = v
                else:
                    plc_online = False
                    break

            for d in ['D850', 'D864', 'D856', 'D870', 'D814', 'D812']:
                old = self.plc_reg_vals['d'][d]
                success, v = self.plc.read_D(d)
                if success:
                    if old != v:
                        d_updated.append({"id": f"#{d}", "val": v})
                        self.plc_reg_vals['d'][d] = v
                else:
                    plc_online = False
                    break
            if not plc_online or len(m_updated) or len(d_updated):
                await self.send(json.dumps({"plc_online": plc_online,
                                            "M_data": m_updated,
                                            "D_data": d_updated}))
            if not plc_online:
                print("stopping plc checking")
                self.plc_checking = False
            await asyncio.sleep(1.5)


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
        self.camera_manager.close_camera()

        # plc
        self.plc_checking = False
        if self.plc_check_task:
            self.plc_check_task.cancel()
            try:
                await self.plc_check_task
            except asyncio.CancelledError:
                print("plc cancelled")

        # plc trigger
        self.plc_trigger_checking = False
        if self.plc_trigger_task:
            self.plc_trigger_task.cancel()
            try:
                await self.plc_trigger_task
            except asyncio.CancelledError:
                print("plc trigger cancelled")

    async def get_camera_frame(self):
        success, buffer = self.camera_manager.get_one_frame()
        if not success:
            print(f"ws:: get_camera_frame failed: ", buffer)
            frame = np.random.randint(0, 255, (640, 640), dtype=np.uint8)
            frame = Image.fromarray(frame)
            buffer = io.BytesIO()
            frame.save(buffer, format='JPEG')
        return buffer

