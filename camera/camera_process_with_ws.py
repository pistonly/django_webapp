import asyncio
import websockets
import aiohttp
import cv2
from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image, softTrigger
from websockets.exceptions import ConnectionClosed



def get_one_image(camera):
    # softTrigger
    error_code = softTrigger(camera['handle'])
    # get one frame
    pb, FH = get_one_frame(camera['handle'], camera['pb'])
    frame = image_to_numpy(pb, FH)
    frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
    frame = Image.fromarray(frame.astype(np.uint8))
    buffer = io.BytesIO()
    frame.save(buffer, format='JPEG')
    return buffer


def prepare_one_image(img_io, gallery_title, camera_info):
    img_io.seek(0)
    unique_slug = uuid.uuid4().hex

    formatted_time = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:17]  # 使用微秒的前两位来表示0.01秒
    roi0 = camera_info['roi0']
    roi1 = camera_info['roi1']
    roi_str = ""
    if not camera_info['roi0_disabled']:
        roi_str += f"{roi0[0]:04d}{roi0[1]:04d}{roi0[2]:04d}{roi0[3]:04d}"
    if not camera_info['roi1_disabled']:
        if len(roi_str):
            roi_str += "-"
        roi_str += f"{roi1[0]:04d}{roi1[1]:04d}{roi1[2]:04d}{roi1[3]:04d}"
    file_title = f"{gallery_title}_{formatted_time}_{roi_str}.jpg"

    files = {"image": (file_title, img_io.getvalue(), 'image/jpeg')}
    data = {
        "title": file_title, 
        "caption": "a solar image",
        "gallery_title": gallery_title, 
        'slug': unique_slug
    }
    return files, data


async def capture_and_upload(camera, gallery_title, url):
    img_buf = get_one_image(camera)
    files, data = prepare_one_image(img_io, gallery_title, camera['camera_info'])
    async with aiohttp.ClientSession() as session:
        async with session.post(url, files=files, data=data) as response:
            print(await response.text())

async def websocket_client(camera, gallery_title, uri, upload_url):
    try:
        async with websockets.connect(uri) as websocket:
            # send id
            await websocket.send(json.dumps({"client_id": gallery_title}))
            response = await websocket.recv()
            print(response)

            while True:
                message = await websocket.recv()
                print(f"< {message}")

                if message == "stop":
                    print("Stopping as per 'stop' signal.")
                    break
                elif message == "trig":
                    print("Capturing and uploading image.")
                    await capture_and_upload(camera, gallery_title, upload_url)
    except ConnectionClosed:
        print("ws closed")
    except Exception as e:
        print(f"An unexpected error: {e}")


async def main(camera:dict, gallery_title:str, ws_uri: str, upload_url: str):
    await websocket_client(uri, upload_url)


def run_asyncio_camera_loop(camera_sn: str, batch_number:str, ws_uri:str, upload_url: str):
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
        # load default configure
        configure_file = configure_dir / camera_sn / "setted_configure.json"
        if configure_file.is_file():
            config_dict = json.load(open(str(configure_file), "r"))
            set_camera_parameter(camera['handle'], **config_dict)
        camera_info = get_camera_parameters(camera['handle'], camera['cap'])
        camera.update({'camera_info': camera_info})

        camera_name = camera['name']
        camera_ord = int(camera_name.split("_")[-1])
        camera_ord = 0 if (camera_ord > 18 or camera_ord < 0) else camera_ord
        gallery_title = f"{batch_number}_{camera_ord}"

        asyncio.run(main(camera, gallery_title, ws_uri, upload_url))
    except Exception as e:
        print(f"camera process error: {str(e)}")

    finally:
        if camera:
            close_camera(camera['handle'], camera['pb'])

