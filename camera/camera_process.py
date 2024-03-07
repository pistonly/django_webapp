import asyncio
import multiprocessing
import websockets
from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image, softTrigger

from multiprocessing import shared_memory
import numpy as np
import json


async def read_register_value(register):
    await asyncio.sleep(1)  # 模拟IO操作
    return register % 2  # 示例：模拟寄存器值

async def send_photo_request(websocket):
    await websocket.send("拍照请求")
    print("已发送拍照请求")

# 监控寄存器并在接收到终止信号时停止
async def monitor_registers(websocket):
    should_stop = False
    
    async def listen_for_stop_signal():
        nonlocal should_stop
        while not should_stop:
            message = await websocket.recv()
            if message == "STOP":
                print("收到停止信号，准备终止监控任务。")
                should_stop = True
    
    listen_task = asyncio.create_task(listen_for_stop_signal())

    while not should_stop:
        for register in range(18):
            value = await read_register_value(register)
            if value == 1:
                await send_photo_request(websocket)
        await asyncio.sleep(1)  # 检查间隔

    listen_task.cancel()

# 异步主函数
async def main(uri: str, camera: dict, frame_buffer: np.ndarray):
    # uri = "ws://example.com/connect-0"  # WebSocket服务器地址
    plc_trigger_task = None
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            cmd_dict = json.loads(message)
            if "stop" in cmd_dict:
                close_camera(camera['handle'], camera['pb'])
                await websocket.send(json.dumps({'stop': 1}))
                break

            if 'set' in cmd_dict:
                print(cmd_dict)
                set_camera_parameter(camera['handle'], **cmd_dict['set'])
                parameters = get_camera_parameters(camera['handle'], camera['cap'])
                await websocket.send(json.dumps(parameters))
                continue

            if 'get' in cmd_dict:
                parameters = get_camera_parameters(camera['handle'], camera['cap'])
                await websocket.send(json.dumps(parameters))
                continue

            if 'frame' in cmd_dict:
                pb, FH = get_one_frame(camera['handle'], camera['pb'])
                frame = image_to_numpy(pb, FH)
                h, w, c = frame.shape
                frame = frame.flatten()
                frame_buffer[0:len(frame)] = frame
                await websocket.send(json.dumps({'shape': [h, w, c]}))
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
                await websocket.send(json.dumps({'shape': [h, w, c]}))
                continue

            if 'grab' in cmd_dict:
                PB, FH = get_one_frame(camera['handle'], camera['pb'])
                save_image(camera['handle'], PB, FH, cmd_dict['path'], cmd_dict['quality'], img_type='bmp')
                await websocket.send(json.dumps({"grab": 1}))
                continue

            if "plc_trigger" in cmd_dict:
                if plc_trigger_task is not None:
                    message = {"plc_trigger": 0, "message": "plc_trigger is already on"}
                else:
                    plc_trigger_task = asyncio.create_task(monitor_registers(websocket))
                    message = {"plc_trigger": 1}
                await websocket.send(json.dumps(message))
                continue

            if "close_plc_trigger" in cmd_dict:
                if plc_trigger_task is None:
                    message = {"close_plc_trigger": 0, "message": "plc_trigger is already closed"}
                else:
                    plc_trigger_task.cancel()



def start_process():
    proc = multiprocessing.Process(target=run_asyncio_loop)
    proc.start()
    return proc

def run_asyncio_camera_loop(camera_sn: str, shm_name: str, uri: str):
    camera = None
    try:
        camera_list = get_devInfo_list()
        for camera_info in camera_list:
            if camera_info.acSn.decode('utf8') == camera_sn:
                camera_res = initialize_cam(camera_info)
                camera = dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                  camera_res))

                existing_shm = shared_memory.SharedMemory(name=shm_name)
                frame_buffer = np.ndarray((camera['bs'], ), dtype=np.uint8, buffer=existing_shm.buf)
                break
        asyncio.run(main(uri, camera, frame_buffer))
    except Exception as e:
        print(f"camera process error: {e}")

    finally:
        if camera:
            close_camera(camera['handle'], camera['pb'])

