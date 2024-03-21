from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
from plc.plc_control import plcControl
from channels.layers import get_channel_layer
from asyncio import Lock 


async def get_correct_client_id(client_info: list, connected_clients: dict, camera_num=18):
    if client_info[-1] is not None:
        for i in range(camera_num):
            c_id = f"{client_info[1]}_{i}"
            if c_id not in connected_clients:
                connected_clients[c_id] = client_info[0]
                connected_clients[c_id].client_id = c_id
                await connected_clients[c_id].send(text_data=json.dumps({"status": "connected",
                                                                   "client_id": c_id}))
                return


class PLCControlConsumer(AsyncWebsocketConsumer):
    connected_clients = {}
    camera_clients_list = []
    plc_check_task = None
    channel_layer = get_channel_layer()
    plc_checking = False
    _lock = Lock()
    camera_num = 18

    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        for client_id, client in list(self.connected_clients.items()):
            if client == self:
                del self.connected_clients[client_id]
                break

        # task
        if self.plc_check_task is not None:
            self.plc_check_task.cancel()

    async def receive(self, text_data):
        data = json.loads(text_data)
        print("-----------------------------")
        print(data)
        print("-----------------------------")

        if 'client_id' in data:
            client_id = data['client_id']
            if "update" not in data:
                if client_id not in self.connected_clients:
                    self.client_id = client_id
                    self.connected_clients[client_id] = self
                    await self.send(text_data=json.dumps({"status": "connected", "client_id": client_id}))
                else:
                    await self.send(text_data=json.dumps({"status": "client_id error"}))

            if client_id != "web":
                async with self._lock:
                    self.camera_clients_list.append([self, client_id, data.get('update')])
                    if len(self.camera_clients_list) >= self.camera_num:
                        [await get_correct_client_id(c_i, self.connected_clients, self.camera_num) for c_i in self.camera_clients_list]


            return

        if "start" in data:
            self.plc_checking = True
            if self.plc_check_task is None:
                self.plc_check_task = asyncio.create_task(self.check_plc_reg())


        if "stop_signal" in data:
            self.plc_checking = False
            for client_id, client in self.connected_clients.items():
                if client_id == self.client_id:
                    continue
                await client.send(text_data="stop")
            try:
                if self.plc_check_task is not None:
                    self.plc_check_task.cancel()
                    await self.plc_check_task
                    self.plc_check_task = None
            except:
                print("plc check cancel error")
            finally:
                self.plc_check_task = None
                print("plc check cancelled++++++++++++++++++++++++++++++++++++++++")


        if "target" in data:
            target = data['target']
            client = self.connected_clients.get(target)
            if client:
                gallery_id = data['gallery_id']
                _id = int(gallery_id.split("_")[-1])
                row, col = _id % 3, _id // 3
                img_id = f"#r-{row}-c-{col}"
                data.update({"img_id": img_id})
                await client.send(text_data=json.dumps(data))
                print(f"client:{client}, sending")
            else:
                print(f"target: {target} not in clients")

    async def simulate_check(self):
        while self.plc_checking:
            await asyncio.sleep(3)
            M1_val = 1
            if M1_val:
                print("m1")
                M1_val = 0
                for _id, client in self.connected_clients.items():
                    if _id == "web":
                        continue
                    try:
                        if int(_id.split("_")[-1]) < 9:
                            await client.send("trig")
                    except:
                        pass
            await asyncio.sleep(3)
            M4_val = 1
            if M4_val:
                print("m4")
                for _id, client in self.connected_clients.items():
                    if _id == "web":
                        continue
                    try:
                        if int(_id.split("_")[-1]) >= 9:
                            await client.send("trig")
                    except:
                        pass



    async def check_plc_reg(self):
        plc = plcControl()
        if not plc.connect():
            print("~~~~~~~~~~~~~~~~~~~~ check ~~~~~~~~~~~~~~~~~~~~")
            print("plc is offline")
            print("~~~~~~~~~~~~~~~~~~~~ check ~~~~~~~~~~~~~~~~~~~~")
            await self.simulate_check()

            return

        print("~~~~~~~~~~~~~~~~~~~~ check ~~~~~~~~~~~~~~~~~~~~")
        while self.plc_checking:
            M1_val = plc.get_M("M1")
            if M1_val:
                print("m1")
                M1_val = 0
                for _id, client in self.connected_clients.items():
                    if _id == "web":
                        continue
                    try:
                        if int(_id.split("_")[-1]) < 9:
                            await client.send("trig")
                    except:
                        pass
                plc.set_M("M1", 0)
            M4_val = plc.get_M("M4")
            if M4_val:
                print("m4")
                for _id, client in self.connected_clients.items():
                    if _id == "web":
                        continue
                    try:
                        if int(_id.split("_")[-1]) >= 9:
                            await client.send("trig")
                    except:
                        pass
                plc.set_M("M4", 0)
            await asyncio.sleep(0.01)

