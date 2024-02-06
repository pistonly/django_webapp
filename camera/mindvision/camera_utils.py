from . import mvsdk
import numpy as np


def get_devInfo_list()-> list:
    return mvsdk.CameraEnumerateDevice()

# Initialize camera and get get capability info
def initialize_cam(DevInfo: mvsdk.tSdkCameraDevInfo):
    hCamera = mvsdk.CameraInit(DevInfo, -1, -1)
    cap = mvsdk.CameraGetCapability(hCamera)
    
    monoCamera = (cap.sIspCapacity.bMonoSensor != 0)
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
    FrameBufferSize = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if monoCamera else 3)

	# 分配RGB buffer，用来存放ISP输出的图像
	# 备注：从相机传输到PC端的是RAW数据，在PC端通过软件ISP转为RGB数据（如果是黑白相机就不需要转换格式，但是ISP还有其它处理，所以也需要分配这个buffer）
    pFrameBuffer = mvsdk.CameraAlignMalloc(FrameBufferSize, 16)
    return hCamera, cap, monoCamera, FrameBufferSize, pFrameBuffer


def get_one_frame(hCamera, pFrameBuffer):
    pRawData, FrameHead = mvsdk.CameraGetImageBuffer(hCamera, 2000)
    mvsdk.CameraImageProcess(hCamera, pRawData, pFrameBuffer, FrameHead)
    mvsdk.CameraReleaseImageBuffer(hCamera, pRawData)
    return pFrameBuffer, FrameHead

def image_to_numpy(pFrameBuffer, FrameHead):
    frame_data = (mvsdk.c_ubyte * FrameHead.uBytes).from_address(pFrameBuffer)
    frame = np.frombuffer(frame_data, dtype=np.uint8)
    frame = frame.reshape((FrameHead.iHeight, FrameHead.iWidth, 1 if FrameHead.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3) )
    return frame

imgType_dict = {'bmp': mvsdk.FILE_BMP}
def save_image(hCamera, pFrameBuffer, FrameHead, path, quality=100, img_type='bmp'):
    status = mvsdk.CameraSaveImage(hCamera, path, pFrameBuffer, FrameHead, imgType_dict[img_type],
                                   quality)
    if status == mvsdk.CAMERA_STATUS_SUCCESS:
        return True
    else:
        return False

def close_camera(hCamera, pFrameBuffer):
	# 关闭相机
    mvsdk.CameraUnInit(hCamera)
	# 释放帧缓存
    mvsdk.CameraAlignFree(pFrameBuffer)
    return

def get_camera_parameters(hCamera):
    parameters = {}
    # get resolution
    psCurVideoSize = mvsdk.CameraGetImageResolution(hCamera)
    parameters.update({"resolution": {"w": psCurVideoSize.iWidth, "h": psCurVideoSize.iHeight}})

    # get toggle mode
    # 0, 1, 2; 0:continue, 1: soft trigger, 2: hard trigger
    triggerMode = mvsdk.CameraGetTriggerMode(hCamera)
    parameters.update({"triggerMode": triggerMode})

    # ---------- exposure settings --------------------
    # ae
    # 0: false, 1: true
    ae_state = mvsdk.CameraGetAeState(hCamera)
    parameters.update({"ae_state": ae_state})

    # 0-cameraGetCapability
    ae_target = mvsdk.CameraGetAeTarget(hCamera)
    parameters.update({"ae_target": ae_target})

    # 0: false, 1: true
    antiflick = mvsdk.CameraGetAntiFlick(hCamera)
    parameters.update({"antiflick": antiflick})

    # 0: 50HZ, 1: 60HZ
    lightFrequency = mvsdk.CameraGetLightFrequency(hCamera)
    parameters.update({'lightFrequency': lightFrequency})

    # default: 10
    analogGain = mvsdk.CameraGetAnalogGain(hCamera)
    parameters.update({'analogGain': analogGain})

    # unit: us
    expose_time = mvsdk.CameraGetExposureTime(hCamera)
    parameters.update({"expose_time": expose_time})

    # (min, max, step)us
    expose_timerange = mvsdk.CameraGetExposureTimeRange(hCamera)
    parameters.update({"expose_timerange": expose_timerange})

    # -------------------- isp --------------------
    # 0: false, 1: true
    h_mirror = mvsdk.CameraGetMirror(hCamera, 0)
    v_mirror = mvsdk.CameraGetMirror(hCamera, 1)
    parameters.update({'h_mirror': h_mirror, 'v_mirror': v_mirror})

    # int 0-100
    sharpness = mvsdk.CameraGetSharpness(hCamera)
    parameters.update({'sharpness': sharpness})

    # -------------------- mapping table --------------------
    # get range from capbility
    lut_gamma = mvsdk.CameraGetGamma(hCamera)
    parameters.update({"lut_gamma": lut_gamma})
    lut_contrast = mvsdk.CameraGetContrast(hCamera)
    parameters.update({"lut_contrast": lut_contrast})

    # -------------------- snap --------------------
    # iWidth: 0 and iHeight: 0 means: the same with preview
    snap_resolution = mvsdk.CameraGetResolutionForSnap(hCamera)
    parameters.update({'snap_resolution': {'w': snap_resolution.iWidth, 'h': snap_resolution.iHeight}})

    # -------------------- speed --------------------
    # 0: low, 1: middle, 2: high
    frame_speed = mvsdk.CameraGetFrameSpeed(hCamera)
    parameters.update({'frame_speed': frame_speed})
    return parameters


def set_camera_parameter(hCamera, **kwargs):
    # set resolution
    if "resolution" in kwargs:
        resolution = mvsdk.tSdkImageResolution()
        resolution.iWidth = kwargs['resolution']['w']
        resolution.iHeight = kwargs['resolution']['h']
        mvsdk.CameraSetImageResolution(hCamera, resolution)

    # -------------------- toggle mode --------------------
    if "trigger_mode" in kwargs:
        mvsdk.CameraSetTriggerMode(hCamera, int(kwargs['trigger_mode']))

    # set lightingControllerMode
    if "light_controller_mode" in kwargs:
        mvsdk.CameraSetLightingControllerMode(hCamera, *kwargs['light_controller_mode'])

    if "light_controller_state" in kwargs:
        mvsdk.CameraSetLightingControllerState(hCamera, *kwargs['light_controller_state'])

    # ---------- exposure settings --------------------
    if 'ae_state' in kwargs:
        mvsdk.CameraSetAeState(hCamera, int(kwargs['ae_state'][0]))

    if 'ae_target' in kwargs:
        mvsdk.CameraSetAeTarget(hCamera, kwargs['ae_target'])

    if 'antiflick' in kwargs:
        mvsdk.CameraSetAntiFlick(hCamera, kwargs['antiflick'])

    if 'lightFrequency' in kwargs:
        mvsdk.CameraSetLightFrequency(hCamera, kwargs['lightFrequency'])

    if 'analogGain' in kwargs:
        mvsdk.CameraSetAnalogGain(hCamera, kwargs['analogGain'])

    if "expose" in kwargs:
        mvsdk.CameraSetExposureTime(hCamera, kwargs['expose'])

    # -------------------- isp --------------------
    if 'h_mirror' in kwargs:
        mvsdk.CameraSetMirror(hCamera, 0, kwargs['h_mirror'])
    if 'v_mirror' in kwargs:
        mvsdk.CameraSetMirror(hCamera, 1, kwargs['v_mirror'])
    if 'sharpness' in kwargs:
        mvsdk.CameraSetSharpness(hCamera, kwargs['sharpness'])

    # -------------------- mapping table --------------------
    if 'lut_gamma' in kwargs:
        mvsdk.CameraSetGamma(hCamera, kwargs['lut_gamma'])
    if 'lut_contrast' in kwargs:
        mvsdk.CameraSetContrast(hCamera, kwargs['lut_contrast'])

    # -------------------- snap --------------------
    if 'snap_resolution' in kwargs:
        mvsdk.CameraSetResolutionForSnap(hCamera, kwargs['snap_resolution'])

    # -------------------- speed --------------------
    if 'frame_speed' in kwargs:
        # val: [0, 1, 2]
        mvsdk.CameraSetFrameSpeed(hCamera, kwargs['frame_speed'])
    return True


if __name__ == "__main__":
     import time
     device_list = get_devInfo_list()
     if len(device_list):
         devInfo = device_list[0]

         hCamera, cap, monoCamera, FrameBufferSize, pFrameBuffer = \
         initialize_cam(devInfo)
         t0 = time.time()
         n = 50
         for i in range(n):
            pFrameBuffer, FrameHead = get_one_frame(hCamera, pFrameBuffer)
            frame = image_to_numpy(pFrameBuffer, FrameHead)
            print(frame.shape) 
         print(f"frame rate: {n / (time.time() - t0)}")

         close_camera(hCamera, pFrameBuffer)
