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

def close_camera(hCamera, pFrameBuffer):
	# 关闭相机
    mvsdk.CameraUnInit(hCamera)
	# 释放帧缓存
    mvsdk.CameraAlignFree(pFrameBuffer)
    return

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
