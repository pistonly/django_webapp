from multiprocessing import Process
import asyncio
import time
import random
from websockets.sync.client import connect
import json


def background_task(uri, batch_number, stop_event, camera_list):
    with connect(uri) as websocket:
        while not stop_event.is_set():
            print(f"camera_list: {camera_list}")
            time.sleep(1)
            if len(camera_list):
                camera_id = random.randint(0, len(camera_list) - 1)
                data = json.dumps({'camera_id': camera_id, 'batch_number': batch_number})
                websocket.send(data)


