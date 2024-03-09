import asyncio
import multiprocessing
from time import sleep
import websockets
from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image, softTrigger

from multiprocessing import shared_memory
import numpy as np
import json
import io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor


async def read_register_value(register):
    await asyncio.sleep(1)  # 模拟IO操作
    return 1  # 示例：模拟寄存器值

async def send_photo_request(websocket):
    await websocket.send("拍照请求")
    print("已发送拍照请求")

executor = ThreadPoolExecutor(max_workers=1)

async def check_event(stop_event):
    """在后台线程中检查事件状态，避免阻塞异步循环"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, stop_event.is_set)

# 监控寄存器并在接收到终止信号时停止
async def monitor_registers(camera, register, stop_event):

    while True:
        event_set = await check_event(stop_event)
        if event_set:
            print("monitor stopping")
            break

        register_value = await read_register_value(register)
        if register_value == 1:
            # softTrigger
            error_code = softTrigger(camera['handle'])
            # get one frame
            pb, FH = get_one_frame(camera['handle'], camera['pb'])
            frame = image_to_numpy(pb, FH)
            frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
            frame = Image.fromarray(frame.astype(np.uint8))
            buffer = io.BytesIO()
            frame.save(buffer, format='JPEG')
            print("saved one image")
        await asyncio.sleep(0.01)


# 异步主函数
async def main(camera, register, stop_event):
    plc_trigger_task = asyncio.create_task(monitor_registers(camera, register, stop_event))
    await plc_trigger_task


def run_asyncio_camera_loop(camera_sn: str, stop_event):
    # start camera, and load configure
    camera = None
    try:
        camera_list = get_devInfo_list()
        for camera_info in camera_list:
            if camera_info.acSn.decode('utf8') == camera_sn:
                camera_res = initialize_cam(camera_info)
                camera = dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                  camera_res))
                break

        asyncio.run(main(camera, 0, stop_event))
    except Exception as e:
        print(f"camera process error: {e}")

    finally:
        if camera:
            close_camera(camera['handle'], camera['pb'])

