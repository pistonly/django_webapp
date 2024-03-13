from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio
import json
from plc.plc_control import plcControl
from channels.layers import get_channel_layer


channel_layer = get_channel_layer()

class PLCControlConsumer(AsyncWebsocketConsumer):
    connected_clients = {}
    plc_check_task = None

    async def connect(self):
        if self.plc_check_task is None:
            self.plc_check_task = asyncio.create_task(self.check_plc_reg())

    async def disconnect(self, close_code):
        for client_id, client in list(self.connected_clients.items()):
            if client == self:
                del self.connected_clients[client_id]
                break

        # remove from group
        if gallery_id < 9:
            group_name = "front"
        else:
            group_name = "back"

        await self.channel_layer.group_discard(
            group_name,
            self.channel_name
        )

        # task
        if self.plc_check_task is not None:
            self.plc_check_task.cancel()

    async def receive(self, text_data):
        data = json.loads(text_data)

        if 'client_id' in data:
            self.client_id = data['client_id']
            self.connected_clients[self.client_id] = self
            if self.client_id not in self.connected_clients:
                # add group
                gallery_id = int(self.client_id.split("_")[-1])
                if gallery_id < 9:
                    group_name = "front"
                    await self.channel_layer.group_add(
                        group_name,
                        self.channel_name
                    )
                else:
                    group_name = "back"
                    await self.channel_layer.group_add(
                        group_name,
                        self.channel_name
                    )

                await self.accept()
                await self.send(text_data=json.dumps({"status": "connected", "client_id": self.client_id}))
            else:
                await self.send(text_data=json.dumps({"status": "wrong id"}))
            return 

        if "stop_signal" in data:
            for client_id, client in self.connected_clients.items():
                if client_id == self.client_id:
                    continue
                await client.send(text_data="stop")


    async def check_plc_reg(self):
        plc = plcControl()
        while True:
            M1_val = plc.get_M("M1")
            if M1_val:
                plc.set_M("M1", 0)
                await channel_layer.group_send(
                    "front",
                    {
                        "type": "group_message",
                        "message": "trig"
                    }
                )
            M4_val = plc.get_M("M4")
            if M4_val:
                plc.set_M("M4", 0)
                await channel_layer.group_send(
                    "back",
                    {
                        "type": "group_message",
                        "message": "trig"
                    }
                )
            await asyncio.sleep(0.02)


    async def group_message(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))
