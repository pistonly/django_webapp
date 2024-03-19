from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
from plc.plc_control import plcControl
from channels.layers import get_channel_layer



def get_client_id(data:dict, connected_clients:dict):
    '''
    return: client_id, gallery_id
    '''
    if data['client_id'] == "web":
        return "web", None
    else:
        if "update" in data:
            for i in range(17, -1, -1):
                client_id = f"{data['client_id']}_{i}"
                if client_id not in connected_clients:
                    return client_id, i
        else:
            gallery_id = int(data['client_id'].split("_")[-1])
            return data['client_id'], gallery_id


class PLCControlConsumer(AsyncWebsocketConsumer):
    connected_clients = {}
    plc_check_task = None
    channel_layer = get_channel_layer()
    plc_checking = False

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
            self.client_id, gallery_id = get_client_id(data, self.connected_clients)
            if self.client_id not in self.connected_clients:
                print("-------------------------------")
                print(self.client_id)
                print("-------------------------------")

                self.connected_clients[self.client_id] = self

                await self.send(text_data=json.dumps({"status": "connected", "client_id": self.client_id}))
            else:
                await self.send(text_data=json.dumps({"status": "wrong id"}))
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

                await client.send(text_data=json.dumps({"gallery_id": gallery_id, "img_id": img_id}))
                print(f"client:{client}, sending")
            else:
                print(f"target: {target} not in clients")


    async def check_plc_reg(self):
        plc = plcControl()
        if not plc.connect():
            print("~~~~~~~~~~~~~~~~~~~~ check ~~~~~~~~~~~~~~~~~~~~")
            print("plc is offline")
            print("~~~~~~~~~~~~~~~~~~~~ check ~~~~~~~~~~~~~~~~~~~~")
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
            await asyncio.sleep(0.01)

