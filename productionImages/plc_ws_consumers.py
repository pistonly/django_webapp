from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
from plc.plc_control import plcControl
from channels.layers import get_channel_layer
from productionImages.models import ProductBatchV2
from asyncio import Lock
import time
import numpy as np
from asgiref.sync import sync_to_async
from concurrent.futures import ThreadPoolExecutor


async def get_correct_client_id(client_info: list,
                                connected_clients: dict,
                                camera_num=4):
    if client_info[-1] is not None:
        for i in range(camera_num):
            c_id = f"{client_info[1]}_{i}"
            if c_id not in connected_clients:
                connected_clients[c_id] = client_info[0]
                connected_clients[c_id].client_id = c_id
                await connected_clients[c_id].send(
                    text_data=json.dumps({
                        "status": "connected",
                        "client_id": c_id
                    }))
                return


def get_product(connected_clients: dict):
    for k in connected_clients.keys():
        if k != "web":
            _ind = k.rfind("_")
            return k[:_ind] if _ind > 0 else k


class PLCControlConsumer(AsyncWebsocketConsumer):
    '''
    NOTE: "web" is the only client_id of web page.
    '''
    connected_clients = {}
    camera_clients_list = []
    plc_check_task = None
    channel_layer = get_channel_layer()
    plc_checking = False
    _lock = Lock()
    camera_num = 4
    current_product = ""
    ng_dict = {}

    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        try:
            if self.client_id in self.connected_clients:
                self.connected_clients.pop(self.client_id)

            for _ in self.camera_clients_list:
                if _[0] == self:
                    self.camera_clients_list.remove(_)
            # task
            if len(self.camera_clients_list
                   ) == 0 and self.plc_check_task is not None:
                PLCControlConsumer.plc_checking = False
                self.plc_check_task.cancel()
                await self.plc_check_task

            if len(self.camera_clients_list
                   ) == 0 and "web" in self.connected_clients:
                await self.connected_clients['web'].send(
                    json.dumps({
                        "status":
                        "connected",
                        "plc_checking":
                        PLCControlConsumer.plc_checking,
                        "current_product":
                        PLCControlConsumer.current_product,
                    }))
                print("stop ok!")
        except Exception as e:
            print("disconnect error: ", str(e))

    async def receive(self, text_data):
        data = json.loads(text_data)
        # print("-----------------------------")
        # # print(data)
        # print("plc_checking", PLCControlConsumer.plc_checking)
        # print("-----------------------------")

        if 'client_id' in data:
            client_id = data['client_id']

            if "update" not in data:
                if client_id not in self.connected_clients:
                    self.client_id = client_id
                    self.connected_clients[client_id] = self
                    await self.send(text_data=json.dumps(
                        {
                            "status": "connected",
                            "client_id": client_id,
                            "plc_checking": PLCControlConsumer.plc_checking,
                            "current_product":
                            PLCControlConsumer.current_product,
                        }))
                elif client_id == "web":
                    await self.send(text_data=json.dumps(
                        {
                            "status": "duplicated",
                            "message": "other web client is running!"
                        }))
                    return

            if client_id != "web":
                async with self._lock:
                    self.camera_clients_list.append(
                        [self, client_id, data.get('update')])
                    # when all camera-client in camera_clients_list
                    if len(self.camera_clients_list) >= self.camera_num:
                        [
                            await
                            get_correct_client_id(c_i, self.connected_clients,
                                                  self.camera_num)
                            for c_i in self.camera_clients_list
                        ]

            return

        if "start" in data:
            if len(self.camera_clients_list) == self.camera_num:
                PLCControlConsumer.current_product = get_product(
                    self.connected_clients)
                PLCControlConsumer.plc_checking = True
                if self.plc_check_task is None:
                    self.plc_check_task = asyncio.create_task(
                        self.check_plc_reg())
                await self.send(text_data=json.dumps({
                    "message": "start success",
                    "start_status": "success"
                }))
            else:
                await self.send(text_data=json.dumps({
                    "message": "camera not started",
                    "start_status": "failed"
                }))

        if "stop_signal" in data:
            PLCControlConsumer.current_product = ""
            PLCControlConsumer.plc_checking = False
            for client_id, client in self.connected_clients.items():
                if client_id == self.client_id:
                    continue
                await client.send(json.dumps({"stop": 1}))
            try:
                if self.plc_check_task is not None:
                    self.plc_check_task.cancel()
                    await self.plc_check_task
                    self.plc_check_task = None
            except:
                print("plc check cancel error")
            finally:
                self.plc_check_task = None
                print(
                    "plc check cancelled++++++++++++++++++++++++++++++++++++++++"
                )

        # get data from camera process
        if "target" in data:
            target = data['target']
            client = self.connected_clients.get(target)
            if client:
                gallery_id = data['gallery_id']
                _id = int(gallery_id.split("_")[-1])
                row, col = _id % 2, _id // 2
                img_id = f"#r-{row}-c-{col}"
                data.update({"img_id": img_id})
                await client.send(text_data=json.dumps(data))
                # statistic ng
                async with self._lock:
                    loop = asyncio.get_running_loop()

                    complete, ng, noNG_num, noNG_rate = await loop.run_in_executor(
                        None, self.statistic_ng, data.get("trig_id"),
                        data.get("ng"))
                    if complete:
                        await client.send(
                            text_data=json.dumps({
                                "ng_full": ng,
                                "noNG_rate": noNG_rate,
                                "noNG_num": noNG_num
                            }))

            else:
                print(f"target: {target} not in clients")

    async def simulate_check(self):
        while PLCControlConsumer.plc_checking:
            M4_trigged = False
            for reg_ind, reg in enumerate(["sM1", "sM2", "sM3", "sM4"]):
                await asyncio.sleep(3)
                await self.plc_send(reg_ind * 3, (reg_ind + 1) * 3, reg)
                if reg == "sM4":
                    M4_trigged = True
            if M4_trigged:
                # calculate speed
                self.bottle_count += 1
                if self.bottle_count % 10 == 0:
                    self.speed = self.bottle_count / (time.time() -
                                                      self.start_time)
                    if "web" in self.connected_clients:
                        await self.connected_clients["web"].send(
                            text_data=json.dumps(
                                {"speed": f"{self.speed:.2f}"}))

    async def plc_send(self, id_start, id_end, plc_reg="M1"):
        timestamp = time.time()
        for _id, client in self.connected_clients.items():
            if _id == "web":
                continue
            try:
                if (int(_id.split("_")[-1]) < id_end) and (int(_id.split("_")[-1]) >= id_start):
                    await client.send(
                        json.dumps({
                            "trig": 1,
                            "trig_id": self.bottle_count,
                            "timestamp": timestamp
                        }))
                    print(f"{plc_reg} send timestamp: {time.time()}, target: {_id}")
            except Exception as e:
                print(f"send M1 trigger error: {e}")


    async def check_plc_reg(self):
        plc = plcControl()
        self.start_time = time.time()
        self.bottle_count = 0
        if not plc.connect():
            print("~~~~~~~~~~~~~~~~~~~~ check ~~~~~~~~~~~~~~~~~~~~")
            print("plc is offline")
            print("~~~~~~~~~~~~~~~~~~~~ check ~~~~~~~~~~~~~~~~~~~~")
            await self.simulate_check()

            return

        print("~~~~~~~~~~~~~~~~~~~~ check ~~~~~~~~~~~~~~~~~~~~")
        while PLCControlConsumer.plc_checking:
            M4_trigged = False
            for reg_ind, reg in enumerate(["M1", "M2", "M3", "M4"]):
                success, M_val = plc.get_M(reg)
                if success and int(M_val) > 0:
                    print(f"{reg}: {M_val} ")
                    await self.plc_send(reg_ind * 3, (reg_ind + 1) * 3, reg)
                    plc.set_M(reg, 0)
                    if reg == "M4":
                        M4_trigged = True
            if M4_trigged:  # last M trigged
                # calculate speed
                self.bottle_count += 1
                if self.bottle_count % 10 == 0:
                    self.speed = self.bottle_count / (time.time() -
                                                      self.start_time)
                    if "web" in self.connected_clients:
                        await self.connected_clients["web"].send(
                            text_data=json.dumps(
                                {"speed": f"{self.speed:.2f}"}))

            await asyncio.sleep(0.02)

    def statistic_ng(self, trig_id, ng):
        '''
        return complete, ng, noNG_num, noNGrate
        '''
        if trig_id is None:
            return False, ng, None, None

        ng = False if ng is None else ng
        if trig_id not in self.ng_dict:
            self.ng_dict[trig_id] = []
        self.ng_dict[trig_id].append(ng)

        complete = False
        if len(self.ng_dict[trig_id]) == self.camera_num:
            complete = True
            ng = False
            for _ in self.ng_dict[trig_id]:
                if _:
                    ng = True
                    break
            # remove
            self.ng_dict.pop(trig_id)

        # update noNGrate
        noNG_rate = None
        noNG_num = None
        if complete:
            try:
                product = ProductBatchV2.objects.get(
                    batch_number=self.current_product)
                product.bottle_num += 1
                if not ng:
                    product.noNG_num += 1
                product.noNG_rate = noNG_rate = product.noNG_num / product.bottle_num
                product.save()
                noNG_num = product.noNG_num

            except Exception as e:
                print(f"get product error: {e}")

        return complete, ng, noNG_num, noNG_rate
