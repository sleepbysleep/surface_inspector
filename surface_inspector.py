#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import json
import numpy as np

import cv2
#import serial
import multiprocessing
import PySpin
import math

import flir_camera as FLIRVision

# import serial_thread
from range_slider import RangeSlider
from toggle_switch import Switch
from image_canvas import ImageCanvas
from control_dock import ControlPanel
from binarize_dock import BinarizePanel
from calibrate_dock import CalibratePanel
from roi_dock import ROIPanel

#import pytesseract
# If you don't have tesseract executable in your PATH, include the following:
#pytesseract.pytesseract.tesseract_cmd = r'<full_path_to_your_tesseract_executable>'
# Example tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract'

class CustomSpinBox(QSpinBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setRange(0, 999)
    def textFromValue(self, value):
        return "%03d" % value

class SurfaceInspectWindow(QMainWindow):
    def __init__(self, config_file=None, parent=None):
        super().__init__(parent)

        self.filename = config_file

        self.raw_image = None
        self.color_corrected_image = None # color corrected image
        self.undistorted_image = None # undistorted image

        self.roi_images = None
        self.binary_image = None
        self.template_images = None
        self.overlay_images = None
        self.background_image = np.zeros((480, 640, 3), dtype=np.uint8)

        self.initAssets()
        self.initUI()
        self.lockButton.setChecked(True)
        self.lockUI()

        # self.resize(1280, 720)

        try:
            FLIRVision.initSystem()
            self.visionCamera = FLIRVision.Camera()
            self.setWindowTitle('Surface Inspector - ' + self.visionCamera.getDeviceName())
        except PySpin.SpinnakerException as error:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Could not connect to the camera.")
            msg.setInformativeText(str(error))
            msg.setWindowTitle("Connection failed")
            msg.exec_()
            # self.quit()

        # try:
        #     self.serialThread = serial_thread.worker(self.commPath, self.commBaudrate)
        #     self.serialThread.shutdownSignal.connect(self.onReceiveShutdown)
        #     self.serialThread.thresholdSignal.connect(self.onReceiveThreshold)
        #     self.serialThread.triggerSignal.connect(self.onSenseTrigger)
        #     self.serialThread.resetSignal.connect(self.onResetCount)
        #     self.serialThread.start()
        # except serial.serialutil.SerialException as error:
        #     msg = QtWidgets.QMessageBox()
        #     msg.setIcon(QtWidgets.QMessageBox.Critical)
        #     msg.setText("Could not connect to the serial device.")
        #     msg.setInformativeText(str(error))
        #     msg.setWindowTitle("Connection failed")
        #     msg.exec_()
        #     #self.quit()
        #     self.serialThread = None

        if self.visionCamera:
            self.controlWidget.setExposureUI(
                (self.visionCamera.getMinExposure(), 100000, self.visionCamera.getExposure())
            )

            self.controlWidget.setGainUI(
                (self.visionCamera.getMinGain(), self.visionCamera.getMaxGain(), self.visionCamera.getGain())
            )

            self.setWindowTitle(
                'Surface Inspector - Serial#: {0:s}, Config: {1:s}'.format(
                    self.visionCamera.getDeviceName(), self.filename
                )
            )

            self.visionCamera.setTrigger(FLIRVision.TriggerType.SOFTWARE)
            self.visionCamera.imageArrived.connect(self.onReceiveImage)
            self.visionCamera.enableAcquisition()

            #self.fpsTime = time.time()
            self.elapsedTime.start()
            self.visionCamera.sendSwTrigger()
        else:
            self.imageCanvas.setImage(self.background_image)

        # TODO: Load default config file
        if self.filename:
            self.loadConfig(self.filename)

    def __del__(self):
        if self.visionCamera: del self.visionCamera
        FLIRVision.deinitSystem()

    def initUI(self):
        #self.setMouseTracking(True)
        # TODO: put Label to display an image, Sliders to change exposure, gain, delay, and light-on-time,
        self.imageCanvas = ImageCanvas() #QtWidgets.QLabel()
        self.imageCanvas.rectChanged.connect(self.setROI)

        ########################################################################
        self.resultLCD = QLCDNumber(3)
        #self.resultLCD.setGeometry(QtCore.QRect(20, 10, 61, 61))
        #self.resultLCD.setFixedSize(400, 300)
        self.resultLCD.setMinimumWidth(150)
        self.resultLCD.setMinimumHeight(100)
        #self.resultLCD.setFixedWidth(200)
        self.resultLCD.setObjectName('resultLCD')
        self.resultLCD.setStyleSheet('QLCDNumber {color: darkred; border: 0px;}')
        #self.resultLCD.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.resultLCD.setDecMode()
        self.resultLCD.setSegmentStyle(QLCDNumber.Flat)
        self.resultLCD.display('{0:03d}'.format(99))
        self.resultLCD.repaint()

        unit_label = QLabel('%  ')
        #unit_label.setMinimumWidth(100)
        unit_label.setMinimumHeight(50)
        unit_label.setStyleSheet('font:12pt;')

        ########################################################

        self.modeButton = QPushButton('Trigger Mode')
        self.modeButton.setCheckable(True)
        self.modeButton.setMinimumHeight(50)
        self.modeButton.toggled.connect(self.onModeToggledEvent)

        self.lockButton = QPushButton('Lock ROI')
        self.lockButton.setCheckable(True)
        self.lockButton.setMinimumHeight(50)
        self.lockButton.toggled.connect(self.onLockToggledEvent)

        # Switch
        self.saveRawImageButton = QPushButton('Save Raw')
        self.saveRawImageButton.setMinimumHeight(50)
        self.saveRawImageButton.clicked.connect(self.onSaveRawImageEvent)

        self.saveCalibImageButton = QPushButton('Save Calibrated')
        self.saveCalibImageButton.setMinimumHeight(50)
        #self.saveCalibImageButton.clicked.connect(self.exitProgram)
        self.saveCalibImageButton.clicked.connect(self.onSaveCalibImageEvent)

        self.imageCntSpinBox = CustomSpinBox()
        self.imageCntSpinBox.setMinimumHeight(50)
        #self.imageCntSpinBox.setRange(0, 999)

        #image_spin_box.valueChanged.connect(self.)
        self.saveStreamButton = QPushButton('Save Stream')
        self.saveStreamButton.setCheckable(True)
        self.saveStreamButton.setMinimumHeight(50)
        # self.saveStreamButton.clicked.connect(self.onSaveStreamEvent)

        hbox1 = QHBoxLayout()
        hbox1.setSpacing(0)
        hbox1.setContentsMargins(0,0,0,0)
        hbox1.addWidget(self.resultLCD)
        hbox1.addWidget(unit_label)

        hbox2 = QHBoxLayout()
        # hbox2.setSpacing(20)
        # hbox2.setContentsMargins(20,20,20,20)
        hbox2.addWidget(self.modeButton)
        hbox2.addWidget(self.lockButton)
        hbox2.addWidget(self.saveRawImageButton)
        hbox2.addWidget(self.saveCalibImageButton)

        hbox3 = QHBoxLayout()
        # hbox2.setSpacing(0)
        # hbox2.setContentsMargins(5,5,5,5)
        #hbox31_layout.addWidget(self.imageCntLCD)
        hbox3.addWidget(self.imageCntSpinBox)
        hbox3.addWidget(self.saveStreamButton)

        hbox4 = QHBoxLayout()
        hbox4.addLayout(hbox2, 1)
        hbox4.addLayout(hbox3)

        gbox = QGroupBox("Operation")
        gbox.setLayout(hbox4)

        hbox_layout = QHBoxLayout()
        hbox_layout.addLayout(hbox1)
        hbox_layout.addWidget(gbox, 1)
        # hbox_layout.addLayout(hbox3)

        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.imageCanvas, 1)
        vbox_layout.addLayout(hbox_layout)

        window = QWidget()
        window.setLayout(vbox_layout)

        self.setCentralWidget(window)

        self.createDocks()
        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.createStatusBar()
        self.readSettings()
        # self.imageCanvas.adjustSize()

    def createActions(self):
        self.actOpen = QAction('&Open', self, shortcut='Ctrl+O', statusTip='Open file', triggered=self.onFileOpen)
        self.actSave = QAction('&Save', self, shortcut='Ctrl+S', statusTip='Save file', triggered=self.onFileSave)
        self.actSaveAs = QAction('Save &As...', self, shortcut='Ctrl+Shift+S', statusTip='Save file as...', triggered=self.onFileSaveAs)
        self.actExit = QAction('E&xit', self, shortcut='Ctrl+Q', statusTip='Exit application', triggered=self.close)

        self.actCtrl = QAction('&Ctrol', self, shortcut='Ctrl+C', statusTip='View control dock', triggered=self.onViewControl)
        self.actBinary = QAction('&Binarize', self, shortcut='Ctrl+V', statusTip='View binarize dock', triggered=self.onViewBinarize)
        self.actCalib = QAction('Calibra&te', self, shortcut='Ctrl+Z', statusTip='View calibrate dock', triggered=self.onViewCalibrate)

        self.actSeparator = QAction(self)
        self.actSeparator.setSeparator(True)

    def createMenus(self):
        """Create Menus for `File` and `Edit`"""
        self.createFileMenu()
        self.createViewMenu()

    def createFileMenu(self):
        menubar = self.menuBar()
        self.fileMenu = menubar.addMenu('&File')
        # self.fileMenu.addAction(self.actNew)
        # self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.actOpen)
        self.fileMenu.addAction(self.actSave)
        self.fileMenu.addAction(self.actSaveAs)
        # self.fileMenu.addAction(self.actExport)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.actExit)

    def createViewMenu(self):
        menubar = self.menuBar()
        self.viewMenu = menubar.addMenu('&View')
        self.viewMenu.addAction(self.actCtrl)
        self.viewMenu.addAction(self.actBinary)
        self.viewMenu.addAction(self.actCalib)

    def onWindowNodesToolbar(self):
        if self.controlDock.isVisible():
            self.controlDock.hide()
        else:
            self.controlDock.show()

    def createToolBars(self):
        pass

    def createDocks(self):
        self.binarizeWidget = BinarizePanel()
        # TODO: connect the handlers
        self.binarizeWidget.luminanceChanged.connect(self.onLChangedEvent)
        self.binarizeWidget.aChannelChanged.connect(self.onAChangedEvent)
        self.binarizeWidget.bChannelChanged.connect(self.onBChangedEvent)
        self.binarizeWidget.saveButtonClicked.connect(self.onSaveBinaryEvent)
        self.binarizeDock = QDockWidget('Binarize', self)
        self.binarizeDock.setWidget(self.binarizeWidget)
        self.binarizeDock.setFloating(False)
        self.binarizeDock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        # self.addDockWidget(Qt.LeftDockWidgetArea, self.binarizeDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.binarizeDock)

        self.controlWidget = ControlPanel()
        # TODO: connect the handlers
        self.controlWidget.exposureChanged.connect(self.onExposureChangedEvent)
        self.controlWidget.gainChanged.connect(self.onGainChangedEvent)
        self.controlWidget.delayChanged.connect(self.onDelayChangedEvent)
        self.controlWidget.lightChanged.connect(self.onLightChangedEvent)
        self.controlWidget.lightModeChanged.connect(self.onLightMode)
        self.controlDock = QDockWidget('Setting', self)
        self.controlDock.setWidget(self.controlWidget)
        self.controlDock.setFloating(False)
        self.controlDock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        # self.addDockWidget(Qt.LeftDockWidgetArea, self.controlDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.controlDock)


        self.calibrateWidget = CalibratePanel(color_correct_filename=None, calibrate_filename=None, parent=self)
        # TODO: connect the handlers
        # self.controlWidget.exposureChanged.connect()
        # self.controlWidget.gainChanged.connect()
        # self.controlWidget.delayChanged.connect()
        # self.controlWidget.lightChanged.connect()
        # self.controlWidget.lightModeChanged.connect()
        self.calibrateDock = QDockWidget('Calibrate', self)
        self.calibrateDock.setWidget(self.calibrateWidget)
        self.calibrateDock.setFloating(False)
        self.calibrateDock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.calibrateDock)

        self.tabifyDockWidget(self.calibrateDock, self.binarizeDock)
        self.tabifyDockWidget(self.binarizeDock, self.controlDock)

        # self.calibrateDock.setFeatures(
        #     QDockWidget.DockWidgetMovable |
        #     QDockWidget.DockWidgetFloatable |
        #     # QDockWidget.DockWidgetVerticalTitleBar |
        #     QDockWidget.DockWidgetClosable
        # )
        # self.calibrateDock.setFloating(True)
        # self.calibrateDock.setVisible(False)

        # self.setDockOptions(QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)

        self.roiWidget = ROIPanel(self)
        self.roiDock = QDockWidget('ROI Setting', self)
        self.roiDock.setWidget(self.roiWidget)
        self.roiDock.setFloating(False)
        self.roiDock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.roiDock)

    def createStatusBar(self):
        self.statusBar().showMessage('Ready')

    def readSettings(self):
        """Read the permanent profile settings for this app"""
        settings = QSettings(self.name_company, self.name_product)
        pos = settings.value('pos', QPoint(200, 200))
        size = settings.value('size', QSize(400, 400))
        self.move(pos)
        self.resize(size)

    def writeSettings(self):
        """Write the permanent profile settings for this app"""
        settings = QSettings(self.name_company, self.name_product)
        settings.setValue('pos', self.pos())
        settings.setValue('size', self.size())

    def initAssets(self):
        self.name_company = "daysleep"
        self.name_product = "surface_inspector"

        # self.windowGeometry = QRect(0, 0, 1280, 760)
        self.visionCamera = None
        self.serialThread = None
        self.serialNumber = None  # str
        # self.imageROIs = [[y*60, x*60, 50, 50] for y in range(4) for x in range(4) ]

        '''
        self.roiColors = [(128,0,0), # Marron
                     (170,110,40), # Brown
                     (128,128,0), # Olive
                     (0,128,128), # Teal
                     (0,0,128), # Navy
                     (230,25,75), # Red
                     (245,130,48), # Orange
                     (255,225,25), # Yellow
                     (210,245,60), # Lime
                     (60,180,75), # Green
                     (70,240,240), # Cyan
                     (0,130,200), # Blue
                     (145,30,180), # Purple
                     (240,50,230), # Magenta
                     (128,128,128), # Grey
                     (250,190,190), # Pink
                     (255,215,180), # Apricot
                     (255,250,200), # BEige
                     (170,255,195), # Mint
                     (230,190,255)] # Lavender
        '''
        self.roiColors = [(128, 0, 0),  # Marron
                     (170, 110, 40),  # Brown
                     (0, 128, 128),  # Teal
                     (0, 0, 128),  # Navy
                     (230, 25, 75),  # Red
                     (245, 130, 48),  # Orange
                     (255, 225, 25),  # Yellow
                     (60, 180, 75),  # Green
                     (70, 240, 240),  # Cyan
                     (0, 130, 200),  # Blue
                     (240, 50, 230),  # Magenta
                     (128, 128, 128),  # Grey
                     (250, 190, 190),  # Pink
                     (255, 250, 200),  # Beige
                     (170, 255, 195),  # Mint
                     (230, 190, 255)]  # Lavender

        self.roiIndex = 0
        self.templatePaths = None
        self.templateFeatures = None

        # featureExtractor = cv2.xfeatures2d.SIFT_create()
        # featureExtractor = cv2.xfeatures2d.SURF_create()
        self.featureExtractor = cv2.ORB_create(nfeatures=1500)
        # featureExtractor = cv2.BRISK_create()
        # featureExtractor = cv2.KAZE_create()
        # featureExtractor = cv2.AKAZE_create()
        # featureExtractor = cv2.BRISK_create()

        FLANN_INDEX_LSH = 6
        self.flannMatcher = cv2.FlannBasedMatcher(
            indexParams={'algorithm': FLANN_INDEX_LSH, 'table_number': 6, 'key_size': 12, 'multi_probe_level': 1},
            searchParams={'checks': 50})
        # flannMatcher = cv2.FlannBasedMatcher(
        #    indexParams={'algorithm':FLANN_INDEX_LSH, 'table_number':12, 'key_size':20, 'multi_probe_level':2},
        #    searchParams={'checks':50})

        self.exposureValue = 1000  # us
        self.gainValue = 12  # db
        self.delayValue = 80  # ms
        self.lightValue = 100  # ms
        self.lightMode = 'Auto'

        self.commPath = 'COM1'
        self.commBaudrate = 115200

        self.binaryRange = [np.array([0, 0, 0]), np.array([255, 255, 255])]
        self.latestImage = None  # numpy.array for image
        self.minArea = 100

        self.elapsedTime = QElapsedTimer()
        self.fpsCount = 0
        self.fpsSum = 0.0
        self.fpsMessage = ''

    def loadConfig(self, filename='config.json'):
        json_data = open(filename, 'r').read()
        load_dict = json.loads(json_data)

        self.roiWidget.is_activated = load_dict["ROISetting"]["Activate"]
        self.roiWidget.roi_rects = load_dict["ROISetting"]["Rects"]
        self.roiWidget.enable_list = load_dict["ROISetting"]["Enable"]
        self.roiWidget.updateUI()

        self.calibrateWidget.color_correct_filename = load_dict["Calibration"]["ColorCorrection"]["Filename"]
        self.calibrateWidget.need_color_correction = load_dict["Calibration"]["ColorCorrection"]["Enable"]
        self.calibrateWidget.camera_calibrate_filename = load_dict["Calibration"]["CameraCalibration"]["Filename"]
        self.calibrateWidget.need_lens_distortion_correction = load_dict["Calibration"]["CameraCalibration"]["Enable"]
        self.calibrateWidget.updateUI()

        self.minArea = load_dict["Binarization"]['MinArea']
        self.binarizeWidget.onLChangedEvent(
            load_dict["Binarization"]["LowerLimit"][0],
            load_dict["Binarization"]["HigherLimit"][0]
        )
        self.binarizeWidget.onAChangedEvent(
            load_dict["Binarization"]["LowerLimit"][1],
            load_dict["Binarization"]["HigherLimit"][1]
        )
        self.binarizeWidget.onBChangedEvent(
            load_dict["Binarization"]["LowerLimit"][2],
            load_dict["Binarization"]["HigherLimit"][2]
        )

        self.controlWidget.onExposureChangedEvent(load_dict['Setting']["Exposure"])
        self.controlWidget.onGainChangedEvent(load_dict['Setting']["Gain"])
        self.controlWidget.onDelayChangedEvent(load_dict['Setting']["Delay"])
        self.controlWidget.onLightChangedEvent(load_dict['Setting']["Light"])
        if load_dict["Setting"]["LightMode"] == "On":
            self.controlWidget.onRadio.setChecked(True)
            self.controlWidget.offRadio.setChecked(False)
            self.controlWidget.autoRadio.setChecked(False)
        elif load_dict["Setting"]["LightMode"] == "Off":
            self.controlWidget.onRadio.setChecked(False)
            self.controlWidget.offRadio.setChecked(True)
            self.controlWidget.autoRadio.setChecked(False)
        else:
            self.controlWidget.onRadio.setChecked(False)
            self.controlWidget.offRadio.setChecked(False)
            self.controlWidget.autoRadio.setChecked(True)
        self.controlWidget.onLightMode()

        self.commPath = load_dict['Communication']['DevicePath']
        self.commBaudrate = load_dict['Communication']['BaudRate']

        #self.imageROI = QtCore.QRect(app_dict['ROIs'][0], app_dict['ROIs'][1], app_dict['ROIs'][2], app_dict['ROIs'][3])
        self.templatePaths = load_dict['Templates']
        self.templateFeatures = []
        for fn in self.templatePaths:
            '''
            image = cv2.imread(fn)
            #gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            keypoints = None
            descriptors = None
            if image is not None:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                keypoints,descriptors = self.featureExtractor.detectAndCompute(gray, None)
            '''

            image = cv2.imread(fn, cv2.IMREAD_GRAYSCALE)

            keypoints,descriptors = self.featureExtractor.detectAndCompute(image, None)

            # Calculate Moments
            moments = cv2.moments(image)
            # Calculate Hu Moments
            hu_moments = cv2.HuMoments(moments)
            # Log scale hu moments
            for i in range(0, 7):
                hu_moments[i] = -1 * math.copysign(1.0, hu_moments[i]) * math.log10(abs(hu_moments[i]))

            #print(hu_moments)
            self.templateFeatures.append({'image':image, 'keypoints':keypoints, 'descriptors':descriptors, 'hu_moments':hu_moments})

        #print(self.templateFeatures)

    def saveConfig(self, filename='config.json'):
        save_dict = dict()
        save_dict["ROISetting"] = dict()

        save_dict["ROISetting"]["Activate"] = self.roiWidget.is_activated
        save_dict["ROISetting"]["Rects"] = self.roiWidget.roi_rects
        save_dict["ROISetting"]["Enable"] = self.roiWidget.enable_list

        save_dict["Calibration"] = dict()
        save_dict["Calibration"]["ColorCorrection"] = dict()
        save_dict["Calibration"]["ColorCorrection"]["Filename"] = self.calibrateWidget.color_correct_filename
        save_dict["Calibration"]["ColorCorrection"]["Enable"] = self.calibrateWidget.need_color_correction
        save_dict["Calibration"]["CameraCalibration"] = dict()
        save_dict["Calibration"]["CameraCalibration"]["Filename"] = self.calibrateWidget.camera_calibrate_filename
        save_dict["Calibration"]["CameraCalibration"]["Enable"] = self.calibrateWidget.need_lens_distortion_correction

        save_dict["Binarization"] = dict()
        save_dict["Binarization"]['MinArea'] = self.minArea
        save_dict["Binarization"]["LowerLimit"] = [
            self.binarizeWidget.lRangeSlider.low(),
            self.binarizeWidget.aRangeSlider.low(),
            self.binarizeWidget.bRangeSlider.low()
        ]
        save_dict["Binarization"]["HigherLimit"] = [
            self.binarizeWidget.lRangeSlider.high(),
            self.binarizeWidget.aRangeSlider.high(),
            self.binarizeWidget.bRangeSlider.high()
        ]

        save_dict['Setting'] = dict()
        save_dict['Setting']["Exposure"] = int(self.visionCamera.getExposure())
        save_dict['Setting']["Gain"] = int(self.visionCamera.getGain())
        save_dict['Setting']["Delay"] = self.controlWidget.delaySlider.value()
        save_dict['Setting']["Light"] = self.controlWidget.lightSlider.value()
        save_dict["Setting"]["LightMode"] = self.controlWidget.lightMode

        save_dict['Communication'] = dict()
        save_dict['Communication']['DevicePath'] = self.commPath
        save_dict['Communication']['BaudRate'] = self.commBaudrate

        save_dict['Templates'] = self.templatePaths

        json_txt = json.dumps(save_dict, indent=2, separators=(',', ': '))
        with open(filename, 'w') as file:
            file.write(json_txt)

    def getFileDialogDirectory(self):
        """Returns starting directory for ``QFileDialog`` file open/save"""
        return ''

    def getFileDialogFilter(self):
        """Returns ``str`` standard file open/save filter for ``QFileDialog``"""
        return 'Config (*.json);;All files (*)'

    def onFileOpen(self):
        """Handle File Open operation"""
        fname,filter = QFileDialog.getOpenFileName(
            self,
            'Open the camera config from file',
            self.getFileDialogDirectory(),
            self.getFileDialogFilter()
        )
        if fname != '' and os.path.isfile(fname):
            self.loadConfig(fname)

    def isFilenameSet(self):
        return self.filename is not None

    def onFileSave(self):
        """Handle File Save operation"""
        if not self.isFilenameSet(): return self.onFileSaveAs()

        self.saveConfig(self.filename)
        self.statusBar().showMessage("Successfully saved %s" % self.filename, 5000)

        return True

    def onFileSaveAs(self):
        """Handle File Save As operation"""
        fname,filter = QFileDialog.getSaveFileName(
            self,
            'Save the camera config to file',
            self.getFileDialogDirectory(),
            self.getFileDialogFilter()
        )
        if fname == '': return False

        self.saveConfig(fname)
        self.statusBar().showMessage("Successfully saved as %s" % self.filename, 5000)

        return True

    def onViewControl(self):
        self.controlDock.show()

    def onViewBinarize(self):
        self.binarizeDock.show()

    def onViewCalibrate(self):
        self.calibrateDock.show()

    def unlockUI(self):
        self.imageCanvas.setRubberBand(True)
        self.binarizeWidget.unlockUI()
        self.calibrateWidget.unlockUI()
        self.controlWidget.unlockUI()
        self.roiWidget.unlockUI()
        self.imageCntSpinBox.setEnabled(True)
        self.saveStreamButton.setEnabled(True)
        self.modeButton.setEnabled(True)
        self.saveRawImageButton.setEnabled(True)
        self.saveCalibImageButton.setEnabled(True)

    def lockUI(self):
        self.imageCanvas.setRubberBand(False)
        self.binarizeWidget.lockUI()
        self.calibrateWidget.lockUI()
        self.controlWidget.lockUI()
        self.roiWidget.lockUI()
        self.imageCntSpinBox.setEnabled(False)
        self.saveStreamButton.setEnabled(False)
        self.modeButton.setEnabled(False)
        self.saveRawImageButton.setEnabled(False)
        self.saveCalibImageButton.setEnabled(False)

    @pyqtSlot(QRect)
    def setROI(self, rect):
        # print("setROI with :", rect.normalized())
        #self.imageROI = rect.normalized()
        self.roiWidget.roi_rects[self.roiWidget.current_index] = [
            rect.normalized().y(),
            rect.normalized().x(),
            rect.normalized().height(),
            rect.normalized().width()
        ]
        # self.imageROIs[self.roiWidget.current_index] = [
        #     rect.normalized().y(),
        #     rect.normalized().x(),
        #     rect.normalized().height(),
        #     rect.normalized().width()
        # ]

    def matchTemplates(self, image, templates):
        base_h,base_w = image.shape[:2]

        ### Plain
        hit_scores = np.zeros(len(templates), dtype=np.float32)
        hit_locs = []
        for i,template in enumerate(templates):
            #print(template)
            temp_h,temp_w = template.shape[:2]
            if template is None or temp_h > base_h or temp_w > base_w:
                hit_scores[i] = 0.0
                hit_locs.append((-1,-1))
            else:
                background = image.astype(np.float32) - 128
                object = template.astype(np.float32) - 128
                score_image = cv2.matchTemplate(background, object, cv2.TM_CCORR_NORMED)
                #score_image = cv2.matchTemplate(image, template, cv2.TM_CCORR_NORMED)
                #score_image = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                min_value,max_value,min_loc,max_loc = cv2.minMaxLoc(score_image)
                hit_scores[i] = max_value
                hit_locs.append(max_loc)
        '''
        ### Multiprocessing
        args_list = []
        for template in templates:
            args_list.append([image.copy(),template,cv2.TM_CCOEFF_NORMED])

        score_images = None
        score_locs = None
        with multiprocessing.Pool(processes=4) as pool:
            score_images = pool.starmap(cv2.matchTemplate, args_list)  # for multiple arguments
            score_locs = pool.map(cv2.minMaxLoc, score_images)  # for single argument

        # with multiprocessing.Pool(processes=2) as pool:
        #    score_images = pool.starmap(cv2.matchTemplate, args_list) # for multiple arguments

        # with multiprocessing.Pool(processes=2) as pool:
        #    score_locs = pool.map(cv2.minMaxLoc, score_images) # for single argument

        hit_scores = np.zeros(len(templates), dtype=np.float)
        hit_locs = []
        for i,[_,max_score,_,max_loc] in enumerate(score_locs):
            hit_scores[i] = max_score
            hit_locs.append(max_loc)
        '''
        ###

        i = np.argmax(hit_scores)
        score = hit_scores[i]
        loc = hit_locs[i]

        return i,score,loc

    def matchFeatures(self, image):
        image_keypoints,image_descriptors = self.featureExtractor.detectAndCompute(image, None)

        res = []
        for template_dict in self.templateFeatures:
            template = template_dict['image']
            template_keypoints = template_dict['keypoints']
            template_descriptors = template_dict['descriptors']
            if template is not None and template_keypoints is not None and template_descriptors is not None:
                matches = self.flannMatcher.knnMatch(template_descriptors, image_descriptors, k=2)
                ratio_thresh = 0.5
                good_matches = []
                for m,n in matches:
                    if m.distance < ratio_thresh * n.distance:
                        good_matches.append(m)

                template_points = []
                image_points = []
                for m in good_matches:
                    template_points.append(template_keypoints[m.queryIdx].pt)
                    image_points.append(image_keypoints[m.trainIdx].pt)

                template_points,image_points = np.float32((template_points,image_points))
                H,status = cv2.findHomography(template_points, image_points, cv2.RANSAC, 3.0)
                h,w = template.shape[:2]
                template_border = np.float32([[[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]])
                image_border = cv2.perspectiveTransform(template_border, H)
                #cv2.polylines(sceneImage, [np.int32(sceneBorder)], True, (255, 255, 0), 5)
                res.append({'matches':len(good_matches), 'points':len(template_keypoints), 'border':image_border})
            else:
                res.append({'matches':0, 'points':len(template_keypoints), 'border':None})
        return res

    def processImage(self, image, bin_range, a_range, b_range):
        '''
        #yuv_image = cv2.cvtColor(image, cv2.COLOR_RGB2YUV)
        lab_image = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)

        bin_image = cv2.inRange(lab_image, bin_range[0], bin_range[1])
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

        a_mask = None
        if a_range is not None:
            a_mask = cv2.inRange(lab_image, a_range[0], a_range[1])
            a_mask = cv2.bitwise_and(foreground_mask, a_mask)

        b_mask = None
        if b_range is not None:
            b_mask = cv2.inRange(lab_image, b_range[0], b_range[1])
            b_mask = cv2.bitwise_and(foreground_mask, b_mask)

        #contours,_ = cv2.findContours(bin_image, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)
        return foreground_mask, a_mask, b_mask, None
        '''
        ###################################################


        #start_time = time.time()
        yuv_image = cv2.cvtColor(image, cv2.COLOR_RGB2YUV)
        lab_image = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        #import multiprocessing
        #with multiprocessing.Pool(2) as pool:
        #    yuv_image,lab_image = pool.starmap(cv2.cvtColor, [(image.copy(), cv2.COLOR_RGB2YUV), (image.copy(), cv2.COLOR_RGB2LAB)])

        bin_image = cv2.inRange(yuv_image, bin_range[0], bin_range[1])
        #labels,label_image,stats,centroids = cv2.connectedComponentsWithStats(bin_image, connectivity=8, ltype=cv2.CV_32S)
        labels,label_image,stats,_ = cv2.connectedComponentsWithStats(bin_image, connectivity=8, ltype=cv2.CV_32S)
        #end_time = time.time()
        #print('1:', end_time-start_time)

        if labels < 2:
            return None, None, None, None

        label_of_big_area = np.argmax(stats[1:,4])+1
        if stats[label_of_big_area,4] < self.minArea:
            return None, None, None, None

        foreground_mask = np.zeros(bin_image.shape, dtype=np.uint8)
        foreground_mask[label_image == label_of_big_area] = 255

        #start_time = time.time()
        # fill holes
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
        #end_time = time.time()
        #print('2:', end_time-start_time)

        #start_time = time.time()
        # find the contour
        #contours,hierarchy = cv2.findContours(foreground_mask, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)
        _,contours,_ = cv2.findContours(foreground_mask, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_SIMPLE)
        #assert(len(contours) > 0)
        contour = contours[0]
        bounding_rect = cv2.minAreaRect(contour) # (center(x, y), (width, height), angle of rotation)
        '''
        if len(contour) >= 5:
            ellipse = cv2.fitEllipse(contour)
            print(ellipse)
            cv2.ellipse(masked_image, ellipse, (0, 255, 0), 2)
        '''
        #end_time = time.time()
        #print('3:', end_time-start_time)
        #####################################################################
        a_mask = None
        if a_range is not None:
            a_mask = cv2.inRange(lab_image, a_range[0], a_range[1])
            a_mask = cv2.bitwise_and(foreground_mask, a_mask)

        b_mask = None
        if b_range is not None:
            b_mask = cv2.inRange(lab_image, b_range[0], b_range[1])
            b_mask = cv2.bitwise_and(foreground_mask, b_mask)

        return foreground_mask, a_mask, b_mask, bounding_rect

    @pyqtSlot(np.ndarray, int, str)
    def onReceiveImage(self, image, image_count, serial_number):
        if image is None:
            if self.modeButton.text() == 'Live View':
                QThread.msleep(100)
                self.visionCamera.sendSwTrigger()
            return

        processTime = QElapsedTimer()
        processTime.start()
        # start_time = time.time()

        self.raw_image = image # RGB format

        if self.calibrateWidget.need_color_checker_detection:
            self.undistorted_image = self.calibrateWidget.processColorCheckerDetection(self.raw_image)
            self.imageCanvas.setImage(self.undistorted_image)
        elif self.calibrateWidget.need_chessboard_detection:
            self.undistorted_image = self.calibrateWidget.processChessboardDetectioin(self.raw_image)
            self.imageCanvas.setImage(self.undistorted_image)
        else:
            # work_image = image.copy()
            # TODO: color correction
            if self.calibrateWidget.need_color_correction:
                self.color_corrected_image = self.calibrateWidget.processColorCorrection(image)
            else:
                self.color_corrected_image = image

            # TODO: lens distortion correction
            if self.calibrateWidget.need_lens_distortion_correction:
                self.undistorted_image = self.calibrateWidget.processLensDistortionCorrection(self.color_corrected_image)
            else:
                self.undistorted_image = self.color_corrected_image

            if self.saveStreamButton.isChecked():
                if not os.path.isdir("./images"): os.mkdir("./images")
                filename = "./images/" + self.imageCntSpinBox.text() + ".png"
                cv2.imwrite(filename, cv2.cvtColor(self.undistorted_image, cv2.COLOR_RGB2BGR))
                self.imageCntSpinBox.setValue(self.imageCntSpinBox.value() + 1)

            # TODO: color space conversion
            self.lab_image = cv2.cvtColor(self.undistorted_image, cv2.COLOR_RGB2LAB)

            # TODO: binary image
            self.binary_image = cv2.inRange(self.lab_image, self.binaryRange[0], self.binaryRange[1])

            # TODO: crop image on ROI
            self.roi_images = []
            self.overlay_images = []
            # for roi in self.imageROIs:
            for roi in self.roiWidget.roi_rects:
                roi_image = self.undistorted_image[roi[0]:roi[0]+roi[2], roi[1]:roi[1]+roi[3]]
                self.roi_images.append(roi_image)
                self.overlay_images.append(roi_image)

            # TODO: template matching
            # work_image = self.raw_image.copy()
            # for roi in self.imageROIs:
            #     bin_image = self.binary_image[roi[0]:roi[0]+roi[2], roi[1]:roi[1]+roi[3]]
            #     if bin_image.shape[0] > self.templateFeatures[0]['image'].shape[0] and bin_image.shape[1] > self.templateFeatures[0]['image'].shape[1]:
            #         i,score,loc = self.matchTemplates(bin_image, [item['image'] for item in self.templateFeatures])
            #
            #         # Eye candies
            #         template = self.templateFeatures[i]['image']
            #         temp_h, temp_w = template.shape[:2]
            #         template_mask = np.zeros(bin_image.shape, dtype=np.uint8)
            #         template_mask[loc[1]:loc[1] + temp_h, loc[0]:loc[0] + temp_w] = template
            #
            #         psuedo_image = np.zeros((bin_image.shape[0],bin_image.shape[1],3), dtype=np.uint8)
            #         psuedo_image[bin_image == 255] = (255, 255, 255)
            #         psuedo_image[template_mask == 255] = (255, 0, 0)
            #
            #         overlay_image = self.raw_image[roi[0]:roi[0] + roi[2], roi[1]:roi[1] + roi[3]]
            #         overlay_image = cv2.addWeighted(overlay_image, 0.5, psuedo_image, 0.5, 0.0)
            #         work_image[roi[0]:roi[0]+roi[2], roi[1]:roi[1]+roi[3], :] = overlay_image


            #time.sleep(0.005) # for nothing to do
            ####################################################################################

            self.imageCanvas.setImage(
                self.undistorted_image,
                [x for i,x in enumerate(self.roiWidget.roi_rects) if self.roiWidget.enable_list[i] and self.roiWidget.is_activated],
                [x for i,x in enumerate(self.roiWidget.roi_colors) if self.roiWidget.enable_list[i] and self.roiWidget.is_activated]
            )

        # end_time = time.time()
        processed = processTime.elapsed()

        elapsed = self.elapsedTime.elapsed()
        self.fpsSum += 1000.0 / (elapsed+0.0000001)
        self.fpsCount += 1

        if self.fpsCount >= 10:
            self.fpsMessage = 'FPS: {0:.2f}, Count: {1:d}'.format(self.fpsSum/self.fpsCount, image_count)
            self.fpsSum = 0.0
            self.fpsCount = 0

        self.elapsedTime.restart()

        # status_msg = 'FPS: {0:.2f}, Count: {1:d}'.format(1.0/(end_time-self.fpsTime+0.000001), image_count)
        # self.fpsTime = end_time

        if self.modeButton.text() == 'Live View':
            self.visionCamera.sendSwTrigger()
        else: # 'Trigger Mode'
            if self.saveStreamButton.isChecked() is True:
                filename = self.imageCntSpinBox.text() + '.png'
                cv2.imwrite(filename, cv2.cvtColor(self.latestImage, cv2.COLOR_RGB2BGR))
                self.imageCntSpinBox.setValue(self.imageCntSpinBox.value() + 1)

        self.statusBar().showMessage('Process: {0:.3f}[ms], {1:s}'.format(processed, self.fpsMessage))

    def onReceiveShutdown(self):
        print('TODO: shutdown()')

    def onReceiveThreshold(self, value):
        print('TODO: set the threshold value')

    def onSenseTrigger(self):
        #self.fpsTime = new_time
        if self.visionCamera: self.visionCamera.sendSwTrigger()
        print('TODO: triggering')

    def onResetCount(self):
        #self.camera.imageCount = 0
        pass

    def onLChangedEvent(self, low_value, high_value):
        # print('L:', low_value, high_value)
        self.binaryRange[0][0] = low_value
        self.binaryRange[1][0] = high_value

    def onAChangedEvent(self, low_value, high_value):
        # print('a*:', low_value, high_value)
        self.binaryRange[0][1] = low_value
        self.binaryRange[1][1] = high_value

    def onBChangedEvent(self, low_value, high_value):
        # print('b*:', low_value, high_value)
        self.binaryRange[0][2] = low_value
        self.binaryRange[1][2] = high_value

    def onSaveBinaryEvent(self):
        pass

    def onExposureChangedEvent(self, value):
        if self.visionCamera:
            self.visionCamera.setExposure(value)

    def onGainChangedEvent(self, value):
        if self.visionCamera:
            self.visionCamera.setGain(value)

    def onDelayChangedEvent(self, value):
        if self.serialThread:
            self.serialThread.sendTriggerDelay(value)

    def onLightChangedEvent(self, value):
        if self.serialThread:
            self.serialThread.sendLightDuration(value)

    def onLightMode(self, light_mode):
        if light_mode == 'On':
            if self.serialThread:
                self.serialThread.turnLightOn()
        elif light_mode == 'Off':
            if self.serialThread:
                self.serialThread.turnLightOff()
        elif light_mode == 'Auto':
            if self.serialThread:
                self.serialThread.turnLightAuto()

    def onModeToggledEvent(self, state):
        #print('mode:', state)
        if state:
            self.modeButton.setText('Live View')
            if self.visionCamera:
                #self.cameraThread.setCaptureMode(-1)
                self.visionCamera.sendSwTrigger()
                # self.fpsTime = time.time()
                self.elapsedTime.start()
            else:
                self.imageCanvas.setImage(
                    self.background_image,
                    [x for i, x in enumerate(self.roiWidget.roi_rects) if self.roiWidget.enable_list[i] and self.roiWidget.is_activated],
                    [x for i, x in enumerate(self.roiWidget.roi_colors) if self.roiWidget.enable_list[i] and self.roiWidget.is_activated]
                )
        else:
            self.modeButton.setText('Trigger Mode')

    def onLockToggledEvent(self, state):
        #print('roi:', state)
        if state:
            self.lockButton.setText('Unlock UI')
            self.lockUI()
        else:
            # self.imageCanvas.setRubberBand(False)
            self.lockButton.setText('Lock UI')
            self.unlockUI()

    def getFileDialogDirectory(self):
        """Returns starting directory for ``QFileDialog`` file open/save"""
        return ''

    def getFileDialogFilter(self):
        """Returns ``str`` standard file open/save filter for ``QFileDialog``"""
        return 'Image (*.png);;All files (*)'

    def onSaveRawImageEvent(self):
        if self.raw_image is None: return

        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        # dialog.setDefaultSuffix(".csv");
        filename,filter = QFileDialog.getSaveFileName(
            self,
            "Save Raw Image",
            self.getFileDialogDirectory(),
            self.getFileDialogFilter(),
            options=options
        )

        if filename and filename != "":
            fname,fext = os.path.splitext(filename)
            new_filename = fname
            if fext == "":
                new_filename += ".png"
                if os.path.isfile(new_filename):
                    msgbox = QMessageBox(self)
                    ret = msgbox.question(self, new_filename, "Are you sure to overwrite ?", msgbox.Yes | msgbox.No)
                    if ret == msgbox.No: return
            else:
                new_filename += fext

            cv2.imwrite(new_filename, cv2.cvtColor(self.raw_image, cv2.COLOR_RGB2BGR))

    def onSaveCalibImageEvent(self):
        if self.undistorted_image is None: return

        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        filename,filter = QFileDialog.getSaveFileName(
            self,
            "Save Calibrated Image",
            self.getFileDialogDirectory(),
            self.getFileDialogFilter(),
            options=options
        )

        if filename and filename != "":
            fname,fext = os.path.splitext(filename)
            new_filename = fname
            if fext == "":
                new_filename += ".png"
                if os.path.isfile(new_filename):
                    msgbox = QMessageBox(self)
                    ret = msgbox.question(self, new_filename, "Are you sure to overwrite ?", msgbox.Yes | msgbox.No)
                    if ret == msgbox.No: return
            else:
                new_filename += fext

            cv2.imwrite(new_filename, cv2.cvtColor(self.undistorted_image, cv2.COLOR_RGB2BGR))

    def closeEvent(self, event):
        msgbox = QMessageBox(self)
        ret = msgbox.question(self,'Surface Inspector', "Are you sure to close ?", msgbox.Yes | msgbox.No)
        if ret == msgbox.Yes:
            print('I am closing now!')
            self.writeSettings()
            # TODO: Stop threading !
            #self.serialThread.stopRunning()
            #self.cameraThread.stopRunning()
            #self.saveConfig('config.json')
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    #dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
    #app.setStyleSheet(dark_stylesheet)

    # Force the style to be the same on all OSs:
    app.setStyle("Fusion")

    # Now use a palette to switch to dark colors:
    # palette = QPalette()
    # palette.setColor(QPalette.Window, QColor(53, 53, 53))
    # palette.setColor(QPalette.WindowText, Qt.white)
    # palette.setColor(QPalette.Base, QColor(25, 25, 25))
    # palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    # palette.setColor(QPalette.ToolTipBase, Qt.white)
    # palette.setColor(QPalette.ToolTipText, Qt.white)
    # palette.setColor(QPalette.Text, Qt.white)
    # palette.setColor(QPalette.Button, QColor(53, 53, 53))
    # palette.setColor(QPalette.ButtonText, Qt.white)
    # palette.setColor(QPalette.BrightText, Qt.red)
    # palette.setColor(QPalette.Link, QColor(42, 130, 218))
    # palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    # palette.setColor(QPalette.HighlightedText, Qt.black)
    # app.setPalette(palette)

    win = SurfaceInspectWindow('config.json')
    win.setGeometry(
        QStyle.alignedRect(
            Qt.LeftToRight,
            Qt.AlignCenter,
            win.size(),
            app.desktop().availableGeometry()
        )
    )
    win.show()

    sys.exit(app.exec_())
