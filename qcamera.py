#!/usr/bin/python3
# -*- coding: utf-8 -*-
import PySpin
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import sys
import enum
import time
import cv2

import numpy2qimage

cameraSystem = None
cameraList = None

def initSystem():
    global cameraSystem, cameraList

    if cameraSystem is not None or cameraList is not None:
        return -1

    # Retrieve singleton reference to system object
    cameraSystem = PySpin.System.GetInstance()
    # Get current library version
    version = cameraSystem.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cameraList = cameraSystem.GetCameras()
    num_cameras = cameraList.GetSize()
    print('Number of cameras detected: %d' % num_cameras)

    if num_cameras <= 0:
        cameraList.Clear()
        cameraList = None
        cameraSystem.ReleaseInstance()
        cameraSystem = None
        raise PySpin.SpinnakerException('Not enough camera!')

    return num_cameras


def deinitSystem():
    global cameraSystem, cameraList

    if cameraList is not None:
        cameraList.Clear()

    if cameraSystem is not None:
        cameraSystem.ReleaseInstance()

class TriggerType(enum.Enum):
    NONE = 0
    SOFTWARE = 1
    HARDWARE = 2

class AcquisitionStatus(enum.Enum):
    IDLE = 1
    ACQUISITION = 2

class ImageEventHandler(PySpin.ImageEvent):
    serialNumber = None
    imageCount = 0
    """
    This class defines the properties, parameters, and the event itself. Take a
    moment to notice what parts of the class are mandatory, and what have been
    added for demonstration purposes. First, any class used to define image events
    must inherit from ImageEvent. Second, the method signature of OnImageEvent()
    must also be consistent. Everything else - including the constructor,
    destructor, properties, body of OnImageEvent(), and other functions -
    is particular to the example.
    """

    def __init__(self, qcamera):
        """
        Constructor. Retrieves serial number of given camera and sets image counter to 0.

        :param cam: Camera instance, used to get serial number for unique image filenames.
        :type cam: CameraPtr
        :rtype: None
        """
        cam = qcamera.cameraObject
        super(ImageEventHandler, self).__init__()
        #if cam.TLDevice.DeviceSerialNumber.GetAccessMode() == PySpin.RO:
        self.serialNumber = cam.TLDevice.DeviceSerialNumber.GetValue()
        #print('Device serial number retrieved as %s...' % self.serialNumber)

        # Initialize image counter to 0
        self.imageCount = 0
        self.sendImage = qcamera.sendImage

        # Release reference to camera
        # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
        # cleaned up when going out of scope.
        # The usage of del is preferred to assigning the variable to None.
        #del cam

    def OnImageEvent(self, image):
        """
        This method defines an image event. In it, the image that triggered the
        event is converted and saved before incrementing the count. Please see
        Acquisition example for more in-depth comments on the acquisition
        of images.

        :param image: Image from event.
        :type image: ImagePtr
        :rtype: None
        """
        if image.IsIncomplete():
            print('Image incomplete with image status %i...' % image.GetImageStatus())
        else:
            image_converted = image.Convert(PySpin.PixelFormat_RGB8,
                                                   PySpin.NEAREST_NEIGHBOR)  # PySpin.HQ_LINEAR)

            image_array = image_converted.GetNDArray()
            self.imageCount += 1

            # Signaling
            self.sendImage.emit(image_array, self.imageCount, self.serialNumber)

    def getImageCount(self):
        """
        Getter for image count.

        :return: Number of images saved.
        :rtype: int
        """
        return self.imageCount

class QCamera(QtCore.QObject):
    cameraObject = None
    cameraSerial = ''
    triggerType = TriggerType.NONE
    #triggerType = TriggerType.SOFTWARE
    acquisitionStatus = AcquisitionStatus.IDLE
    imageEventHandler = None

    sendImage = QtCore.pyqtSignal(np.ndarray, int, str)

    def __init__(self, serial=None):
        super().__init__()
        global cameraSystem, cameraList
        '''
        # Retrieve singleton reference to system object
        self.cameraSystem = PySpin.System.GetInstance()
        # Get current library version
        version = self.cameraSystem.GetLibraryVersion()
        print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

        # Retrieve list of cameras from the system
        self.cameraList = self.cameraSystem.GetCameras()
        print(dir(self.cameraList))
        num_cameras = self.cameraList.GetSize()
        print('Number of cameras detected: %d' % num_cameras)

        if num_cameras <= 0:
            self.cameraList.Clear()
            self.cameraList = None
            self.cameraSystem.ReleaseInstance()
            self.cameraSystem = None
            raise PySpin.SpinnakerException('Not enough camera!')
        '''
        if cameraSystem is None or cameraList is None:
            raise PySpin.SpinnakerException('Camera system is not initialized at all!')

        if cameraList.GetSize() <= 0:
            raise PySpin.SpinnakerException('Not enough camera!')

        if serial is None:
            self.cameraObject = cameraList.GetByIndex(0)
        else:
            self.cameraObject = cameraList.GetBySerial(serial)

        self.cameraObject.Init()

        try:
            self.imageEventHandler = ImageEventHandler(self)
            self.cameraObject.RegisterEvent(self.imageEventHandler)
        except PySpin.SpinnakerException as ex:
            print('Error: %s'%ex)

        self.cameraObject.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        self.cameraObject.GainAuto.SetValue(PySpin.GainAuto_Off)
        self.cameraObject.BlackLevel.SetValue(0)
        self.cameraObject.OffsetX.SetValue(0)
        self.cameraObject.OffsetY.SetValue(0)
        #self.cameraObject.Width.SetValue(720)
        #self.cameraObject.Height.SetValue(540)

        self.setTrigger(self.triggerType)
        # self.cameraObject.AcquisitionMode.SetValue(PySpin.AcquisitionMode_SingleFrame)
        self.cameraObject.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)

        # print(type(self.cameraObject.DeviceSerialNumber()))

    def __del__(self):
        print('Destruct camera object')
        if self.cameraObject is not None:
            self.cameraObject.EndAcquisition()
            self.cameraObject.UnregisterEvent(self.imageEventHandler)
            self.cameraObject.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
            self.cameraObject.GainAuto.SetValue(PySpin.GainAuto_Continuous)
            self.cameraObject.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)
            self.cameraObject.DeInit()
            del self.cameraObject

    def getMinExposure(self):
        return self.cameraObject.ExposureTime.GetMin()

    def getMaxExposure(self):
        return self.cameraObject.ExposureTime.GetMax()

    def getExposure(self):
        return self.cameraObject.ExposureTime.GetValue()

    def setExposure(self, exposure_time):
        exposure_time_to_set = min(self.cameraObject.ExposureTime.GetMax(), exposure_time)
        exposure_time_to_set = max(self.cameraObject.ExposureTime.GetMin(), exposure_time_to_set)
        self.cameraObject.ExposureTime.SetValue(exposure_time_to_set)
        # print('Exposure Time To set:', exposure_time_to_set)

    def getMinGain(self):
        return self.cameraObject.Gain.GetMin()

    def getMaxGain(self):
        return self.cameraObject.Gain.GetMax()

    def getGain(self):
        return self.cameraObject.Gain.GetValue()

    def setGain(self, gain):
        # Ensure desired exposure time does not exceed the maximum
        gain_to_set = min(self.cameraObject.Gain.GetMax(), gain)
        gain_to_set = max(self.cameraObject.Gain.GetMin(), gain_to_set)
        self.cameraObject.Gain.SetValue(gain_to_set)
        # print('Gain To set:', gain_to_set)

    def setTrigger(self, trigger_type):
        self.triggerType = trigger_type
        self.cameraObject.TriggerMode.SetValue(PySpin.TriggerMode_Off)
        # print('Trigger mode disabled...')
        # Select trigger source
        # The trigger source must be set to hardware or software while trigger
        # mode is off.
        if self.cameraObject.TriggerSource.GetAccessMode() != PySpin.RW:
            raise PySpin.SpinnakerException('Unable to get trigger source (node retrieval). Aborting...')

        if trigger_type == TriggerType.SOFTWARE:
            self.cameraObject.TriggerSource.SetValue(PySpin.TriggerSource_Software)
        elif trigger_type == TriggerType.HARDWARE:
            self.cameraObject.TriggerSource.SetValue(PySpin.TriggerSource_Line0)
        elif trigger_type == TriggerType.NONE:
            return

        # Turn trigger mode on
        # Once the appropriate trigger source has been set, turn trigger mode
        # on in order to retrieve images using the trigger.
        self.cameraObject.TriggerMode.SetValue(PySpin.TriggerMode_On)
        # print('Trigger mode turned back on...')

    def sendSwTrigger(self):
        if self.triggerType == TriggerType.SOFTWARE:
            #print('swtriggered')
            self.cameraObject.TriggerSoftware.Execute()

    def enableAcquisition(self):
        if self.acquisitionStatus == AcquisitionStatus.IDLE:
            self.cameraObject.BeginAcquisition()
            self.acquisitionStatus = AcquisitionStatus.ACQUISITION

    def disableAcquisition(self):
        if self.acquisitionStatus == AcquisitionStatus.ACQUISITION:
            self.cameraObject.EndAcquisition()
            self.acquisitionStatus = AcquisitionStatus.IDLE

@QtCore.pyqtSlot(np.ndarray, int, str)
def onReceiveImage(image, count, serial):
    print(serial, count)

def main(argv):
    initSystem()
    cam = QCamera()
    #cam.setTrigger(TriggerType.SOFTWARE)
    cam.sendImage.connect(onReceiveImage)

    cam.enableAcquisition()
    print('Hello World!')
    time.sleep(1)
    cam.disableAcquisition()

    del cam
    deinitSystem()

    return 0

class CameraThreadWindow(QtWidgets.QWidget):
    exposureValue = 2000
    gainValue = 12

    def __init__(self):
        super().__init__()
        initSystem()
        self.camera = QCamera()
        self.initUI()

        self.fpsTime = time.time()
        self.camera.setTrigger(TriggerType.SOFTWARE)
        self.camera.sendImage.connect(self.receiveImage)
        self.camera.enableAcquisition()
        self.camera.sendSwTrigger()

    def __del__(self):
        self.camera.disableAcquisition()
        del self.camera
        deinitSystem()
        print('Dialog destruction')
        #self.sleep(0)

    @QtCore.pyqtSlot(np.ndarray, int, str)
    def receiveImage(self, image, image_count, serial_number):
        qimage = numpy2qimage.numpy2qimage(image)
        self.imageCanvas.setPixmap(QtGui.QPixmap.fromImage(qimage.scaled(self.imageCanvas.width(), self.imageCanvas.height(), QtCore.Qt.KeepAspectRatio)))
        new_time = time.time()
        self.statusBar.showMessage('FPS: %.2f, Image Count: %d'%(1.0/(new_time-self.fpsTime), image_count))
        self.fpsTime = new_time

        yuv_image = cv2.cvtColor(image, cv2.COLOR_RGB2YUV)
        lab_image = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)

        bin_image = cv2.inRange(yuv_image, np.array([128, 128, 128]), np.array([255,255,255]))
        labels,label_image,stats,centroids = cv2.connectedComponentsWithStats(bin_image, connectivity=8, ltype=cv2.CV_32S)
        foreground_mask = np.zeros(bin_image.shape, dtype=np.uint8)
        foreground_mask[label_image != 0] = 255

        black_pixs = np.where(label_image == 0)
        if len(black_pixs[0]) > 0:
            black_seed = (black_pixs[0][0], black_pixs[1][0])
            h,w = foreground_mask.shape[:2]

            if black_seed[1] >= 0 and black_seed[1] < h and black_seed[0] >= 0 and black_seed[0] < w:
                floodfill_mask = foreground_mask.copy()
                mask = np.zeros((h+2,w+2), np.uint8)
                cv2.floodFill(floodfill_mask, mask, black_seed, 255)

                inv_floodfill_mask = cv2.bitwise_not(floodfill_mask)
                foreground_mask = foreground_mask | inv_floodfill_mask

        if labels >= 2:
            _,contours,_ = cv2.findContours(foreground_mask, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)
            #assert(len(contours) > 0)
            contour = contours[0]
            bounding_rect = cv2.minAreaRect(contour) # (center(x, y), (width, height), angle of rotation)

        a_mask = cv2.inRange(lab_image, np.array([0,128,0]), np.array([255,255,255]))
        a_mask = cv2.bitwise_and(foreground_mask, a_mask)

        b_mask = cv2.inRange(lab_image, np.array([0,0,128]), np.array([255,255,255]))
        b_mask = cv2.bitwise_and(foreground_mask, b_mask)

        #time.sleep(0.005)
        self.camera.sendSwTrigger()
        #self.camera.swTrigger()

    def initUI(self):
        self.setFixedSize(800, 600)
        self.setWindowTitle('CameraThreadWindow')

        # TODO: Label to display an image
        self.imageCanvas = QtWidgets.QLabel()
        self.imageCanvas.setAlignment(QtCore.Qt.AlignCenter)

        # TODO: Sliders to change exposure, gain
        exp_tag = QtWidgets.QLabel('Exposure:')
        exp_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        exp_slider.setMinimumHeight(30)
        exp_slider.setValue(self.exposureValue)
        self.camera.setExposure(self.exposureValue)
        exp_slider.setRange(self.camera.getMinExposure(), 100000)#self.camera.getMaxExposure())
        exp_slider.setObjectName('Exposure')
        exp_slider.setFocusPolicy(QtCore.Qt.StrongFocus)
        exp_slider.setTickPosition(QtWidgets.QSlider.NoTicks)
        exp_slider.setTickInterval(100)
        exp_slider.setSingleStep(10)
        exp_slider.valueChanged.connect(self.exposureChangedEvent)
        self.exposureLabel = QtWidgets.QLabel(str(self.exposureValue))
        self.exposureLabel.setMinimumWidth(50)
        exp_unit = QtWidgets.QLabel('[us]')
        print('Exposure MinMax:', self.camera.getMinExposure(), self.camera.getMaxExposure())

        gain_tag = QtWidgets.QLabel('Gain:')
        gain_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        gain_slider.setMinimumHeight(30)
        gain_slider.setValue(self.gainValue)
        self.camera.setGain(self.gainValue)
        gain_slider.setRange(self.camera.getMinGain(), self.camera.getMaxGain())
        gain_slider.setObjectName('Gain')
        gain_slider.setFocusPolicy(QtCore.Qt.StrongFocus)
        gain_slider.setTickPosition(QtWidgets.QSlider.NoTicks)
        gain_slider.setTickInterval(1)
        gain_slider.setSingleStep(1)
        gain_slider.valueChanged.connect(self.gainChangedEvent)
        self.gainLabel = QtWidgets.QLabel(str(self.gainValue))
        self.gainLabel.setMinimumWidth(50)
        gain_unit = QtWidgets.QLabel('[db]')
        print('Gain MinMax:', self.camera.getMinGain(), self.camera.getMaxGain())

        grid_layout = QtWidgets.QGridLayout()
        grid_layout.addWidget(exp_tag, 0, 0)
        grid_layout.addWidget(exp_slider, 0, 1)
        grid_layout.addWidget(self.exposureLabel, 0, 2)
        grid_layout.addWidget(exp_unit, 0, 3)
        grid_layout.addWidget(gain_tag, 1, 0)
        grid_layout.addWidget(gain_slider, 1, 1)
        grid_layout.addWidget(self.gainLabel, 1, 2)
        grid_layout.addWidget(gain_unit, 1, 3)

        # TODO: Statusbar to print message
        self.statusBar = QtWidgets.QStatusBar(self)
        self.statusBar.showMessage('Hello World.')

        vbox_layout = QtWidgets.QVBoxLayout()
        vbox_layout.addWidget(self.imageCanvas, 1) # expanding
        vbox_layout.addLayout(grid_layout)
        vbox_layout.addWidget(self.statusBar)

        self.setLayout(vbox_layout)

    @QtCore.pyqtSlot(int)
    def exposureChangedEvent(self, value):
        #print('Exposure:', value)
        self.exposureLabel.setText(str(value))
        self.camera.setExposure(value)

    @QtCore.pyqtSlot(int)
    def gainChangedEvent(self, value):
        #print('Gain:', value)
        self.gainLabel.setText(str(value))
        self.camera.setGain(value)

    @QtCore.pyqtSlot()
    def closeEvent(self, event):
        msgbox = QtWidgets.QMessageBox(self)
        ret = msgbox.question(self,'CameraThreadWindow', "Are you sure to close ?", msgbox.Yes | msgbox.No)
        if ret == msgbox.Yes:
            print('I am closing now!')
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = CameraThreadWindow()
    win.show()
    app.exec_()
    del win
