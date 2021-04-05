import PySpin
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
import enum

spinnakerSystem = None
cameraList = None

def initSystem():
    global spinnakerSystem, cameraList

    if spinnakerSystem is not None or cameraList is not None:
        return -1

    # Retrieve singleton reference to system object
    spinnakerSystem = PySpin.System.GetInstance()
    # Get current library version
    version = spinnakerSystem.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cameraList = spinnakerSystem.GetCameras()
    num_cameras = cameraList.GetSize()
    print('Number of cameras detected: %d' % num_cameras)

    if num_cameras <= 0:
        cameraList.Clear()
        cameraList = None
        spinnakerSystem.ReleaseInstance()
        spinnakerSystem = None
        raise PySpin.SpinnakerException('Not enough camera!')

    return num_cameras

def deinitSystem():
    global spinnakerSystem, cameraList

    if cameraList is not None:
        cameraList.Clear()

    if spinnakerSystem is not None:
        spinnakerSystem.ReleaseInstance()

class TriggerType(enum.Enum):
    NONE = 0
    SOFTWARE = 1
    HARDWARE = 2

class AcquisitionStatus(enum.Enum):
    IDLE = 0
    ACQUISITION = 1

class Camera(QtCore.QObject, PySpin.ImageEventHandler):
    serialNumber = None
    imageCount = 0
    cameraObject = None
    cameraSerial = ''
    triggerType = TriggerType.NONE
    #triggerType = TriggerType.SOFTWARE
    acquisitionStatus = AcquisitionStatus.IDLE
    imageEventHandler = None

    imageArrived = QtCore.pyqtSignal(np.ndarray, int, str)

    """
    This class defines the properties, parameters, and the event itself. Take a
    moment to notice what parts of the class are mandatory, and what have been
    added for demonstration purposes. First, any class used to define image events
    must inherit from ImageEvent. Second, the method signature of OnImageEvent()
    must also be consistent. Everything else - including the constructor,
    destructor, properties, body of OnImageEvent(), and other functions -
    is particular to the example.
    """
    def __init__(self, serial=None):
        """
        Constructor. Retrieves serial number of given camera and sets image counter to 0.

        :param cam: Camera instance, used to get serial number for unique image filenames.
        :type cam: CameraPtr
        :rtype: None
        """
        global spinnakerSystem, cameraList

        #super(QtCore.QObject).__init__()
        #super(PySpin.ImageEvent).__init__()
        super(Camera, self).__init__()

        if not spinnakerSystem.IsValid():
            raise PySpin.SpinnakerException('No spinnaker system is found')
        
        if cameraList.GetSize() <= 0:
            raise PySpin.SpinnakerException('No camera is found!')

        if serial is None:
            self.cameraObject = cameraList.GetByIndex(0)
        else:
            self.cameraObject = cameraList.GetBySerial(serial)

        nodemap = self.cameraObject.GetTLDeviceNodeMap()
        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))
                if node_feature.GetName() == 'DeviceModelName':
                    self.deviceName = node_feature.ToString()

        else:
            print('Device control information not available.')

        if not self.cameraObject.IsValid():
            raise PySpin.SpinnakerException("Invalid camera was selected.")
        if self.cameraObject.IsInitialized():
            raise PySpin.SpinnakerException("Selected camera has already initialized.")

        self.cameraObject.Init()

        self.cameraObject.RegisterEventHandler(self)
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
        self.serialNumber = self.cameraObject.DeviceSerialNumber() #this->objectPtr->TLDevice.DeviceSerialNumber.GetValue();
        self.imageCount = 0;

        print(f"Initialized Spinnaker compatible camera ({self.cameraObject.Width()}x{self.cameraObject.Height()}@{self.cameraObject.PixelFormat.GetCurrentEntry().GetSymbolic()})")
        #this->objectPtr->PixelFormat.GetCurrentEntry()->GetSymbolic()

    def __del__(self):
        print('Destruct camera object')
        if self.cameraObject is not None and self.cameraObject.IsValid():
            #self.cameraObject.EndAcquisition()
            self.disableAcquisition()
            self.cameraObject.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
            self.cameraObject.GainAuto.SetValue(PySpin.GainAuto_Continuous)
            self.cameraObject.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)
            self.cameraObject.UnregisterEventHandler(self)
            self.cameraObject.DeInit()
            del self.cameraObject

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
            self.imageArrived.emit(image_array, self.imageCount, self.serialNumber)

    def getImageCount(self):
        """
        Getter for image count.

        :return: Number of images saved.
        :rtype: int
        """
        return self.imageCount


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

    def getDeviceName(self):
        return self.deviceName


