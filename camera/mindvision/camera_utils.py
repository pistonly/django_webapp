try:
    from . import mvsdk
except:
    import mvsdk
import numpy as np

roi0 = [0, 0, 1280, 720]
roi1 = [0, 0, 1920, 1080]
roi0_disabled = 1
roi1_disabled = 1
default_name = 'camera_00'
rotation = 0  # 0, 1, 2, 3, -1, -2, -3  # 1 means 90 degrees, -1 means -90 degrees

imgType_dict = {'bmp': mvsdk.FILE_BMP}

camera_get_functions = {
    func[len("CameraGet"):].lower(): getattr(mvsdk, func)
    for func in dir(mvsdk)
    if callable(getattr(mvsdk, func)) and func.startswith("CameraGet")
}

camera_set_functions = {
    func[len("CameraSet"):].lower(): getattr(mvsdk, func)
    for func in dir(mvsdk)
    if callable(getattr(mvsdk, func)) and func.startswith("CameraSet")
}


def get_devInfo_list() -> list:
    return mvsdk.CameraEnumerateDevice()


def image_to_numpy(pFrameBuffer, FrameHead):
    frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
    frame = np.frombuffer(frame_data, dtype=np.uint8)
    frame = frame.reshape(
        (FrameHead.iHeight, FrameHead.iWidth,
         1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))
    return frame

def rotate_image(image, rotation):
    '''
    rotation = 0, 1, 2, 3, -1, -2, -3
    '''
    if rotation == 0:
        return image
    image = image[:, :, 0]
    if rotation == 1:
        image = np.flipud(image.T)
    if rotation == 2 or rotation == -2:
        image = np.flip(image)
    if rotation == 3:
        image = np.fliplr(image.T)
    if rotation == -3:
        image = np.flipud(image.T)
    if rotation == -1:
        image = np.fliplr(image.T)
    h, w = image.shape[0:2]
    image = np.reshape(image, (h, w, 1))
    return image


class mvCamera:

    def __init__(self,
                 DevInfo: mvsdk.tSdkCameraDevInfo,
                 name: str = default_name) -> None:
        self.name = name
        self.rotation = 0
        # name = camera_info.acFriendlyName.decode('utf8')
        self.roi0, self.roi1 = roi0, roi1
        self.roi0_disabled, self.roi1_disabled = 1, 1
        self.hCamera = hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
        self.cap = cap = mvsdk.CameraGetCapability(hCamera)
        self.sn = DevInfo.acSn.decode("utf8")
        # configure 
        self.configure_f = None
        self.default_config = {}
        self.configure_name = None
        selected_parameters = [
            "ImageResolution", "TriggerMode", "Sharpness", "Mirror",
            "Sharpness", "Gamma", "Contrast", "FrameSpeed", "AeTarget",
            "TriggerDelayTime", "TriggerCount", "AeState", "AnalogGain",
            "ExposureTime",
        ]
        self.selected_parameters = [p.lower() for p in selected_parameters]

        selected_parameters = [
            "TriggerMode", "Sharpness", "hMirror", "vMirror", "Sharpness",
            "Gamma", "Contrast", "FrameSpeed", "AeTarget", "TriggerDelayTime",
            "TriggerCount", "AeState", "AnalogGain", "ExposureTime",
            "antiFlick",
        ]
        self.selected_parameters_for_set = [
            p.lower() for p in selected_parameters
        ]

        self.monoCamera = monoCamera = (cap.sIspCapacity.bMonoSensor != 0)
        # 黑白相机让ISP直接输出MONO数据，而不是扩展成R=G=B的24位灰度
        if monoCamera:
            mvsdk.CameraSetIspOutFormat(hCamera, mvsdk.CAMERA_MEDIA_TYPE_MONO8)

        # 相机模式切换成连续采集
        mvsdk.CameraSetTriggerMode(hCamera, 0)

        # 手动曝光，曝光时间30ms
        mvsdk.CameraSetAeState(hCamera, 0)
        mvsdk.CameraSetExposureTime(hCamera, 30 * 1000)

        # 让SDK内部取图线程开始工作
        mvsdk.CameraPlay(hCamera)

        # 计算RGB buffer所需的大小，这里直接按照相机的最大分辨率来分配
        self.FrameBufferSize = FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (
            1 if monoCamera else 3)

        # 分配RGB buffer，用来存放ISP输出的图像
        # 备注：从相机传输到PC端的是RAW数据，在PC端通过软件ISP转为RGB数据（如果是黑白相机就不需要转换格式，但是ISP还有其它处理，所以也需要分配这个buffer）
        self.pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)

    def __enter__(self):
        # 返回对象自身，以便可以在上下文管理器内使用
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理资源，例如关闭相机和释放内存
        self.close_camera()

    def set_configure_file(self, configure_f, default_config, configure_name):
        self.configure_f = configure_f
        self.default_config = default_config
        self.configure_name = configure_name

    def get_one_frame(self):
        try:
            pRawData, FrameHead = mvsdk.CameraGetImageBuffer(
                self.hCamera, 2000)
            mvsdk.CameraImageProcess(self.hCamera, pRawData, self.pFrameBuffer,
                                     FrameHead)
            mvsdk.CameraReleaseImageBuffer(self.hCamera, pRawData)
            return self.pFrameBuffer, FrameHead
        except:
            return None, None

    def softTrigger(self):
        return mvsdk.CameraSoftTrigger(self.hCamera)

    def save_image(self, FrameHead, path, quality=100, img_type='bmp'):
        status = mvsdk.CameraSaveImage(self.hCamera, path, self.pFrameBuffer,
                                       FrameHead, imgType_dict[img_type],
                                       quality)
        if status == mvsdk.CAMERA_STATUS_SUCCESS:
            return True
        else:
            return False

    def close_camera(self):
        # 关闭相机
        mvsdk.CameraUnInit(self.hCamera)
        # 释放帧缓存
        mvsdk.CameraAlignFree(self.pFrameBuffer)
        print(
            f"-------------------- camera:{self.name} closed--------------------"
        )
        return

    def trigger_mode(self):
        return mvsdk.CameraGetTriggerMode(self.hCamera)

    def get_camera_roi(self):
        return self.roi0, self.roi1, self.roi0_disabled, self.roi1_disabled

    def get_camera_parameters(self):
        """
        # antiflick: 0: false, 1: true
        # lightFrequency: 0: 50HZ, 1: 60HZ
        # AnalogGain: default: 10
        # ExposureTime: unit: us
        # ExposureTimeRange: (min, max, step)us
        # mirror: 0: false, 1: true
        # sharpness: int 0-100
        # FrameSpeed: 0: low, 1: middle, 2: high
        # toggle mode: 0, 1, 2; 0:continue, 1: soft trigger, 2: hard trigger
        # triggerDelayTiem: unit: us
        # ae: 0: false, 1: true

        """

        hCamera, cap = self.hCamera, self.cap
        parameters = {}
        # get roi & name
        parameters.update(dict(zip(['roi0', 'roi1', 'roi0_disabled', 'roi1_disabled'],
                                   self.get_camera_roi())))
        parameters['name'] = self.name
        parameters['rotation'] = self.rotation

        for k in self.selected_parameters:
            if k == "mirror":
                hMirror = camera_get_functions[k](hCamera, 0)
                vMirror = camera_get_functions[k](hCamera, 1)
                v = {"hMirror": hMirror, "vMirror": vMirror}
            elif k == "imageresolution":
                v = camera_get_functions[k](hCamera)
                v = {"w": v.iWidth, "h": v.iHeight}
            else:
                v = camera_get_functions[k](hCamera)

            parameters.update({k: v})

        # 0-cameraGetCapability
        ae_target_range = (cap.sExposeDesc.uiTargetMin,
                           cap.sExposeDesc.uiTargetMax)
        parameters.update({"ae_target_range": ae_target_range})
        expose_range = (cap.sExposeDesc.uiExposeTimeMin,
                        cap.sExposeDesc.uiExposeTimeMax)
        parameters.update({"expose_range": expose_range})
        gamma_range = (cap.sGammaRange.iMin, cap.sGammaRange.iMax)
        parameters.update({"gamma_range": gamma_range})
        contrast_range = (cap.sContrastRange.iMin, cap.sContrastRange.iMax)
        parameters.update({"contrast_range": contrast_range})
        analogGain_range = (cap.sExposeDesc.uiAnalogGainMin,
                            cap.sExposeDesc.uiAnalogGainMax)
        parameters.update({"analoggain_range": analogGain_range})

        return parameters

    def set_camera_roi(self, **kwargs):
        if "roi0" in kwargs:
            self.roi0 = [int(v) for v in kwargs['roi0']]

        if "roi0_disabled" in kwargs:
            self.roi0_disabled = int(kwargs['roi0_disabled'])

        if "roi1" in kwargs:
            self.roi1 = [int(v) for v in kwargs['roi1']]

        if "roi1_disabled" in kwargs:
            self.roi1_disabled = int(kwargs['roi1_disabled'])

    def set_camera_rotation(self, **kwargs):
        if "rotation" in kwargs:
            if kwargs['rotation'].lower() == "plus":
                rotation = self.rotation + 1
            elif kwargs['rotation'].lower() == "minus":
                rotation = self.rotation - 1
            else:
                try:
                    rotation = int(kwargs['rotation'])
                except:
                    rotation = self.rotation
            sign = -1 if rotation < 0 else 1
            self.rotation = rotation % (sign * 4)

    def set_camera_parameter(self, **kwargs):
        hCamera = self.hCamera
        # print(kwargs)
        if "name" in kwargs:
            self.name = kwargs['name']

        self.set_camera_roi(**kwargs)
        self.set_camera_rotation(**kwargs)
        # # set resolution
        # if "resolution" in kwargs:
        #     resolution = mvsdk.tSdkImageResolution()
        #     resolution.iWidth = kwargs['resolution']['w']
        #     resolution.iHeight = kwargs['resolution']['h']
        #     mvsdk.CameraSetImageResolution(hCamera, resolution)

        for k, v in kwargs.items():
            k = k.lower()
            if k in self.selected_parameters_for_set:
                if k == "hMirror".lower():
                    mvsdk.CameraSetMirror(hCamera, 0, int(v))
                elif k == "vMirror".lower():
                    mvsdk.CameraSetMirror(hCamera, 1, int(v))
                else:
                    camera_set_functions[k.lower()](hCamera, int(v))
        return True


def PrintCapbility(cap):
    for i in range(cap.iTriggerDesc):
        desc = cap.pTriggerDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iImageSizeDesc):
        desc = cap.pImageSizeDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iClrTempDesc):
        desc = cap.pClrTempDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iMediaTypeDesc):
        desc = cap.pMediaTypeDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iFrameSpeedDesc):
        desc = cap.pFrameSpeedDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iPackLenDesc):
        desc = cap.pPackLenDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iPresetLut):
        desc = cap.pPresetLutDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iAeAlmSwDesc):
        desc = cap.pAeAlmSwDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iAeAlmHdDesc):
        desc = cap.pAeAlmHdDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iBayerDecAlmSwDesc):
        desc = cap.pBayerDecAlmSwDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))
    for i in range(cap.iBayerDecAlmHdDesc):
        desc = cap.pBayerDecAlmHdDesc[i]
        print("{}: {}".format(desc.iIndex, desc.GetDescription()))


if __name__ == "__main__":
    device_list = get_devInfo_list()
    if len(device_list):
        devInfo = device_list[0]

        with mvCamera(devInfo) as camera:
            PrintCapbility(camera.cap)

            # #################### ops save-image ####################
            # t0 = time.time()
            # n = 50
            # for i in range(n):
            #    pFrameBuffer, FrameHead = get_one_frame(hCamera, pFrameBuffer)
            #    frame = image_to_numpy(pFrameBuffer, FrameHead)
            #    print(frame.shape)
            # print(f"frame rate: {n / (time.time() - t0)}")
            # ##################################################

            # #################### ops set ####################
            parameters = camera.get_camera_parameters()
            print(parameters)

            param = {"triggerMode": 1, "triggerDelayTime": 20, "aeState": 1}
            camera.set_camera_parameter(**param)

            parameters = camera.get_camera_parameters()
            print(parameters)
