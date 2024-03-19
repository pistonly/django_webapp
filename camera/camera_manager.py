from .mindvision.camera_utils import get_devInfo_list, get_one_frame, image_to_numpy, initialize_cam, close_camera, set_camera_parameter, get_camera_parameters, save_image, softTrigger
from pathlib import Path
import json
import numpy as np
from PIL import Image
import io




current_dir = Path(__file__).resolve().parent
configure_dir = current_dir / 'configure'

def get_camera_sn():
    camera_list = get_devInfo_list()
    camera_sn_list = [camera_info.acSn.decode('utf8') for camera_info in camera_list]
    return camera_sn_list

class cameraManager:
    def __init__(self) -> None:
        self.camera_process = {}
        self.current_camera = {}
        self.camera_sn_list = []
        self.camera_dict = {}

    def init_camera_configure(self, sn):
        camera_config_dir = configure_dir / sn
        camera_config_dir.mkdir(parents=True, exist_ok=True)
        # 4 configures
        for i in range(4):
            config_f = camera_config_dir / f"configure_配置{i}.json"
            if not config_f.is_file():
                json.dump({"configure_name": config_f.stem}, open(str(config_f), "w"))

        configures = [self.configure_name_to_show(f.stem) for f in camera_config_dir.iterdir() if f.with_suffix(".json") and f.stem.startswith("configure_")]
        configures.sort()
        # default config
        success, default_configure = self.get_camera_info()

        # load setted_configure
        setted_config_f = camera_config_dir / f"setted_configure.json"
        configure_name = None
        if setted_config_f.is_file():
            setted_config = json.load(open(str(setted_config_f), 'r'))
            self.set_camera(setted_config)
            configure_name = setted_config['configure_name']
        else:
            # default is configure_000
            configure_name = "configure_配置0"

        self.current_camera.update({"configure_f": configures, 'default_config': default_configure,
                                    "configure_name": configure_name})

    def reset_configure(self, config_f):
        sn = self.current_camera.get('sn')
        if sn is None:
            return False, "please update camera list"

        success, _ = self.save_configure(config_f, self.current_camera['default_config'])
        if success:
            return True, "reset OK"
        else:
            return False, "reset failed"

    def _start_camera(self, sn):
        self.current_camera = {"sn": sn}
        # start
        camera_info = self.camera_dict.get(sn)
        if camera_info:
            name = camera_info.acFriendlyName.decode('utf8')
            camera_res = initialize_cam(camera_info)
            self.current_camera.update(dict(zip(["handle", "cap", "mono", "bs", "pb"],
                                                camera_res)))
            self.current_camera.update({'name': name})
            print(f"camera: {sn} start success!")
            return
        else:
            print(f"camera: {sn} start failed!")

    def start_camera(self, sn):
        self.update_camera_list(start_default=False)
        if sn not in self.camera_dict:
            return False, f"{sn} is not right sn"
        if self.current_camera.get("sn") is None:
            self._start_camera(sn)
        elif self.current_camera["sn"] != sn:
            self.close_camera()
            self._start_camera(sn)
        else:
            print(f"camera: {sn} started!")

        # confiugre
        self.init_camera_configure(sn)
        return True, f"{sn} started"

    def save_configure(self, config_f: str, config_dict = None):
        '''
        configure file start with "configure_"
        '''
        sn = self.current_camera.get('sn')
        if sn is None:
            return False, "please update camera list"

        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        if not config_f.endswith(".json"):
            config_f = f"{config_f}.json"

        config_f_path = configure_dir / sn / config_f
        if config_dict is None:
            success, config_dict = self.get_camera_info()
            config_dict.update({'configure_name': config_f_path.stem})
        else:
            success = True

        if success:
            setted_config_f = config_f_path.parent / "setted_configure.json"
            json.dump(config_dict, open(str(config_f_path), "w"))
            json.dump(config_dict, open(str(setted_config_f), "w"))
            return True, "saved success"
        else:
            return success, "save configure failed"

    def load_configure(self, config_f: str):
        sn = self.current_camera.get('sn')
        if sn is None:
            return False, "please update camera list"

        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        if not config_f.endswith(".json"):
            config_f = f"{config_f}.json"

        config_f_path = configure_dir / sn / config_f
        if config_f_path.is_file():
            config_dict = json.load(open(str(config_f_path), "r"))
            success, message = self.set_camera(config_dict)
            if success:
                setted_config_f = config_f_path.parent / "setted_configure.json"
                json.dump(config_dict, open(str(setted_config_f), "w"))

            return success, message
        else:
            return False, f"{str(config_f_path)} is not file"

    def update_camera_list(self, start_default=True):
        camera_list = get_devInfo_list()
        self.camera_dict = {camera_info.acSn.decode('utf8'): camera_info for camera_info in camera_list}
        self.camera_sn_list = list(self.camera_dict.keys())
        # set default camera
        if start_default and len(self.camera_sn_list):
            self.start_camera(self.camera_sn_list[0])

    def close_camera(self):
        if self.current_camera.get("sn") is not None:
            close_camera(self.current_camera['handle'], self.current_camera['pb'])
            print(f"{self.current_camera['sn']} closed")
            self.current_camera = {}

    def get_one_frame(self):
        if self.current_camera.get('sn') is None:
            return False, "please update camera list"
        pb, FH = get_one_frame(self.current_camera['handle'], self.current_camera['pb'])
        frame = image_to_numpy(pb, FH)
        frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
        frame = Image.fromarray(frame.astype(np.uint8))
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG')
        return True, buffer

    def grab(self, path: str, quality=100):
        if self.current_camera.get('sn') is None:
            return False, "please update camera list"
        PB, FH = get_one_frame(self.current_camera['handle'], self.current_camera['pb'])
        save_image(self.current_camera['handle'], PB, FH, path, quality, img_type='bmp')
        return True, True

    def soft_trigger(self, sn=None):
        if sn is not None:
            if sn != self.current_camera.get('sn'):
                self.start_camera(sn)
        if self.current_camera.get('sn') is None:
            return False, "please update camera list"
        camera = self.current_camera
        error_code = softTrigger(camera['handle'])
        # get one frame
        pb, FH = get_one_frame(camera['handle'], camera['pb'])
        frame = image_to_numpy(pb, FH)
        frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
        frame = Image.fromarray(frame.astype(np.uint8))
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG')
        return True, buffer

    def configure_name_to_show(self, configure_name: str):
        if configure_name.startswith("configure_"):
            _from = len("configure_")
            configure_name = configure_name[_from:]
        if configure_name.endswith(".json"):
            _end = len(configure_name) - len(".json")
            configure_name = configure_name[:_end]
        return configure_name

    def get_camera_info(self):
        camera = self.current_camera
        try:
            camera_info = get_camera_parameters(camera['handle'], camera['cap'])
            camera_info.update({"configure_f": camera.get("configure_f"),
                                "configure_name": camera.get("configure_name")})
            if camera.get("configure_name"):
                camera_info.update({"configure_name_alias": self.configure_name_to_show(camera.get("configure_name"))})
            return True, camera_info
        except Exception as e:
            return False, str(e)

    def set_camera(self, parameters: dict):
        camera = self.current_camera
        if camera.get("sn") is None:
            return False, "please update camera list"
        print(parameters)
        set_camera_parameter(camera['handle'], **parameters)
        camera_info = self.get_camera_info()
        return True, camera_info
