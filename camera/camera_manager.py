from .mindvision.camera_utils import mvCamera, get_devInfo_list, image_to_numpy, rotate_image
from pathlib import Path
import json
import numpy as np
from PIL import Image
import io

current_dir = Path(__file__).resolve().parent
configure_dir = current_dir / 'configure'


def get_camera_sn():
    camera_list = get_devInfo_list()
    camera_sn_list = [
        camera_info.acSn.decode('utf8') for camera_info in camera_list
    ]
    return camera_sn_list


class cameraManager:

    def __init__(self) -> None:
        self.current_camera = None
        self.camera_sn_list = []
        self.camera_dict = {}

    def __enter__(self):
        return self

    def __exit__(self):
        self.close_camera()

    def get_sn(self):
        if self.current_camera is None:
            return None
        else:
            return self.current_camera.sn

    def init_camera_configure(self, sn):
        camera_config_dir = configure_dir / sn
        camera_config_dir.mkdir(parents=True, exist_ok=True)
        # 4 configures
        for i in range(4):
            config_f = camera_config_dir / f"configure_配置{i}.json"
            if not config_f.is_file():
                json.dump({"configure_name": config_f.stem},
                          open(str(config_f), "w"))

        configures = [
            self.configure_name_to_show(f.stem)
            for f in camera_config_dir.iterdir()
            if f.with_suffix(".json") and f.stem.startswith("configure_")
        ]
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

        self.current_camera.set_configure_file(configures, default_configure,
                                               configure_name)

    def reset_configure(self, config_f):
        if self.current_camera is None:
            return False, "please update camera list"

        success, _ = self.save_configure(config_f,
                                         self.current_camera.default_config)
        if success:
            return True, "reset OK"
        else:
            return False, "reset failed"

    def _start_camera(self, sn):
        # start
        camera_info = self.camera_dict.get(sn)
        if camera_info:
            self.current_camera = mvCamera(camera_info)
            print(f"camera: {sn} start success!")
            return
        else:
            print(f"camera: {sn} start failed!")

    def start_camera(self, sn):
        self.update_camera_list(start_default=False)
        if sn not in self.camera_dict:
            return False, f"{sn} is not right sn"
        if self.current_camera is None:
            self._start_camera(sn)
        elif self.current_camera.sn != sn:
            self.current_camera.close_camera()
            self._start_camera(sn)
        else:
            print(f"camera: {sn} started!")

        # confiugre
        self.init_camera_configure(sn)
        return True, f"{sn} started"

    def save_configure(self, config_f: str, config_dict=None):
        '''
        configure file start with "configure_"
        '''
        if self.current_camera is None:
            return False, "please update camera list"

        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        if not config_f.endswith(".json"):
            config_f = f"{config_f}.json"

        config_f_path = configure_dir / self.current_camera.sn / config_f
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
        if self.current_camera is None:
            return False, "please update camera list"

        if not config_f.startswith("configure_"):
            config_f = f"configure_{config_f}"
        if not config_f.endswith(".json"):
            config_f = f"{config_f}.json"

        config_f_path = configure_dir / self.current_camera.sn / config_f
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
        self.camera_dict = {
            camera_info.acSn.decode('utf8'): camera_info
            for camera_info in camera_list
        }
        self.camera_sn_list = list(self.camera_dict.keys())
        # set default camera
        if start_default and len(self.camera_sn_list):
            self.start_camera(self.camera_sn_list[0])

    def close_camera(self):
        if self.current_camera is not None:
            self.current_camera.close_camera()
            print(f"{self.current_camera.sn} closed")
            self.current_camera = None

    def get_one_frame(self, soft_trigger=None):
        if soft_trigger is None:
            soft_trigger = (self.current_camera.trigger_mode() == 1)

        if soft_trigger:
            return self.soft_trigger()

        if self.current_camera is None:
            return False, "please update camera list"
        pb, FH = self.current_camera.get_one_frame()
        frame = image_to_numpy(pb, FH)
        frame = rotate_image(frame, self.current_camera.rotation)
        frame = frame[:, :, 0] if frame.shape[-1] == 1 else frame
        frame = Image.fromarray(frame.astype(np.uint8))
        buffer = io.BytesIO()
        frame.save(buffer, format='JPEG')
        return True, buffer

    def grab(self, path: str, quality=100):
        if self.current_camera is None:
            return False, "please update camera list"
        PB, FH = self.current_camera.get_one_frame()
        self.current_camera.save_image(FH, path, quality)
        return True, True

    def soft_trigger(self, sn=None):
        if self.current_camera is None:
            return False, "please update camera list"

        if sn is not None and sn != self.current_camera.sn:
            self.start_camera(sn)

        self.current_camera.softTrigger()
        # get one frame
        pb, FH = self.current_camera.get_one_frame()
        frame = image_to_numpy(pb, FH)
        frame = rotate_image(frame, self.current_camera.rotation)
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
        try:
            if self.current_camera is not None:
                camera_info = self.current_camera.get_camera_parameters()
                camera_info.update({
                    "configure_f":
                    self.current_camera.configure_f,
                    "configure_name":
                    self.current_camera.configure_name
                })
                if self.current_camera.configure_name:
                    camera_info.update({
                        "configure_name_alias":
                        self.configure_name_to_show(
                            self.current_camera.configure_name)
                    })
            return True, camera_info
        except Exception as e:
            return False, str(e)

    def get_camera_roi(self):
        if self.current_camera is None:
            roi0, roi1 = [], []
            roi0_disabled, roi1_disabled = True, True
        else:
            roi0, roi1, roi0_disabled, roi1_disabled = self.current_camera.get_camera_roi()
        return roi0, roi1, roi0_disabled, roi1_disabled

    def set_camera(self, parameters: dict):
        if self.current_camera is None:
            return False, "please update camera list"
        self.current_camera.set_camera_parameter(**parameters)
        success, camera_info = self.get_camera_info()
        return success, camera_info
