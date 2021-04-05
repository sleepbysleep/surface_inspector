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
import numpy2qimage
# import serial_thread
from range_slider import RangeSlider
from toggle_switch import Switch
#import qdarkstyle

#import pytesseract
# If you don't have tesseract executable in your PATH, include the following:
#pytesseract.pytesseract.tesseract_cmd = r'<full_path_to_your_tesseract_executable>'
# Example tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract'

class ImageCanvas(QLabel):
    rectChanged = pyqtSignal(QRect)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.setMouseTracking(True)
        self.origin = QPoint()
        self.changeRubberBand = False
        self.allowRubberBand = False
        self.setAlignment(Qt.AlignCenter)
        self.viewRect = None

    def setRubberBand(self, state):
        self.allowRubberBand = state

    def mousePressEvent(self, event):
        if self.viewRect is not None and self.viewRect.contains(event.pos()) and self.allowRubberBand and event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            #self.rectChanged.emit(self.rubberBand.geometry())
            self.rubberBand.show()
            self.changeRubberBand = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.viewRect is not None and self.viewRect.contains(event.pos()) and self.changeRubberBand:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
            #self.rectChanged.emit(self.rubberBand.geometry())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.allowRubberBand and event.button() == Qt.LeftButton:
            #self.image2viewTransform.inverted().mapRect(self.rubberBand.geometry())
            view2image = self.image2viewTransform.inverted()[0]
            #print(view2image)
            self.rectChanged.emit(view2image.mapRect(self.rubberBand.geometry()))
            self.rubberBand.hide()
            self.changeRubberBand = False
        super().mouseReleaseEvent(event)

    @pyqtSlot(np.ndarray)
    def setImage(self, image, rect=None):
        qimage = numpy2qimage.numpy2qimage(image).scaled(self.width(), self.height(), Qt.KeepAspectRatio)
        self.viewRect = QRect(QPoint(int((self.width()-qimage.width())/2), int((self.height()-qimage.height())/2)), qimage.size())
        #self.imageRatio = self.width() / image.shape[1]
        self.image2viewTransform = QTransform(
            qimage.width()/image.shape[1], 0.0,
            0.0, qimage.height()/image.shape[0],
            self.viewRect.topLeft().x(), self.viewRect.topLeft().y()
        )

        if rect is not None:
            painter = QPainter(qimage)
            painter.setPen(QPen(QColor(0,100,255,100), 3))
            painter.drawRect(self.image2viewTransform.mapRect(rect).translated(-self.viewRect.topLeft()))
            painter.end()
        super().setPixmap(QPixmap.fromImage(qimage))

class CustomSpinBox(QSpinBox):
    def __init__(self, *args):
        super().__init__(*args)
        self.setRange(0, 999)
    def textFromValue(self, value):
        return "%03d" % value

class SurfaceInspectWindow(QWidget):
    def initAssets(self):
        self.windowGeometry = QRect(0, 0, 1500, 1300)
        self.serialNumber = None  # str
        self.imageROIs = None  # QtCore.QRect(0, 0, 100, 100)7
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
        self.aRange = [[0, 128, 0], [255, 255, 255]]
        self.bRange = [[0, 0, 128], [255, 255, 255]]
        self.binRange = [[0, 0, 0], [255, 255, 255]]
        self.latestImage = None  # numpy.array for image
        self.minArea = 100
        self.binCh1Apply = True
        self.binCh2Apply = True
        self.binCh3Apply = True
        self.aInspect = True
        self.bInspect = False

        self.elapsedTime = QElapsedTimer()
        self.fpsCount = 0
        self.fpsSum = 0.0
        self.fpsMessage = ''

    def loadConfig(self, filename='config.json', do_apply=False):
        json_data = open(filename).read()
        load_dict = json.loads(json_data)

        app_dict = load_dict['Application']
        self.windowGeometry = QRect(app_dict['WindowSize'][0], app_dict['WindowSize'][1], app_dict['WindowSize'][2], app_dict['WindowSize'][3])
        self.imageROIs = app_dict['ROIs']
        #self.imageROI = QtCore.QRect(app_dict['ROIs'][0], app_dict['ROIs'][1], app_dict['ROIs'][2], app_dict['ROIs'][3])
        self.templatePaths = app_dict['Templates']
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

        cam_dict = load_dict['Camera']
        self.serialNumber = cam_dict['SerialNumber']
        self.exposureValue = cam_dict['Exposure']
        self.gainValue = cam_dict['Gain']
        self.delayValue = cam_dict['Delay']
        self.lightValue = cam_dict['Light']
        self.lightMode = cam_dict['LightMode']

        isp_dict = load_dict['ISP']
        self.minArea = isp_dict['MinArea']
        self.binCh1Apply = isp_dict['BinCh1Apply']
        self.binCh2Apply = isp_dict['BinCh2Apply']
        self.binCh3Apply = isp_dict['BinCh3Apply']
        self.binRange = [isp_dict['BinLowerLimit'], isp_dict['BinUpperLimit']]
        self.aRange = [isp_dict['ALowerLimit'], isp_dict['AUpperLimit']]
        self.aInspect = isp_dict['AInspect']
        self.bRange = [isp_dict['BLowerLimit'], isp_dict['BUpperLimit']]
        self.bInspect = isp_dict['BInspect']

        comm_dict = load_dict['Communication']
        self.commPath = comm_dict['DevicePath']
        self.commBaudrate = comm_dict['BaudRate']

        if do_apply:
            #self.setGeometry(self.windowGeometry)
            self.exposureSlider.setValue(self.exposureValue)
            self.cameraThread.setExposure(self.exposureValue)
            self.gainSlider.setValue(self.gainValue)
            self.cameraThread.setGain(self.gainValue)
            self.delaySlider.setValue(self.delayValue)
            self.lightSlider.setValue(self.lightValue)
            #self.binSlider.setValue(self.binValue)
            self.ch1Switch.setChecked(self.binCh1Apply)
            self.ch2Switch.setChecked(self.binCh2Apply)
            self.ch3Switch.setChecked(self.binCh3Apply)
            self.aSlider.setValue(self.aValue)
            self.aSwitch.setChecked(self.aInspect)
            self.bSlider.setValue(self.bValue)
            self.bSwitch.setChecked(self.bInspect)
            self.onRadio.setChecked(True if self.lightMode == 'On' else False)
            self.offRadio.setChecked(True if self.lightMode == 'Off' else False)
            self.autoRadio.setChecked(True if self.lightMode == 'Auto' else False)

    def saveConfig(self, filename='config.json'):
        json_config = dict()
        json_config['Application'] = dict()
        self.windowGeometry = self.geometry()
        json_config['Application']['WindowSize'] = [self.windowGeometry.x(), self.windowGeometry.y(), self.windowGeometry.width(), self.windowGeometry.height()]
        #json_config['Application']['ROIs'] = [self.imageROI.x(), self.imageROI.y(), self.imageROI.width(), self.imageROI.height()]
        json_config['Application']['ROIs'] = self.imageROIs
        json_config['Application']['Templates'] = self.templatePaths

        json_config['Camera'] = dict()
        json_config['Camera']['SerialNumber'] = self.serialNumber
        json_config['Camera']['Exposure'] = self.exposureValue
        json_config['Camera']['Gain'] = self.gainValue
        json_config['Camera']['Delay'] = self.delayValue
        json_config['Camera']['Light'] = self.lightValue
        json_config['Camera']['LightMode'] = self.lightMode

        json_config['ISP'] = dict()
        json_config['ISP']['MinArea'] = self.minArea
        json_config['ISP']['BinCh1Apply'] = self.binCh1Apply
        json_config['ISP']['BinCh2Apply'] = self.binCh2Apply
        json_config['ISP']['BinCh3Apply'] = self.binCh3Apply
        json_config['ISP']['BinLowerLimit'] = self.binRange[0]
        json_config['ISP']['BinUpperLimit'] = self.binRange[1]
        json_config['ISP']['AInspect'] = self.aInspect
        json_config['ISP']['ALowerLimit'] = self.aRange[0]
        json_config['ISP']['AUpperLimit'] = self.aRange[1]
        json_config['ISP']['BInspect'] = self.bInspect
        json_config['ISP']['BLowerLimit'] = self.bRange[0]
        json_config['ISP']['BUpperLimit'] = self.bRange[1]

        json_config['Communication'] = dict()
        json_config['Communication']['DevicePath'] = self.commPath
        json_config['Communication']['BaudRate'] = self.commBaudrate
        
        json_txt = json.dumps(json_config, indent=2, separators=(',', ': '))
        with open(filename, 'w') as file:
            file.write(json_txt)

    def __init__(self, config_file='config.json'):
        super().__init__()

        self.initAssets()

        # TODO: Load default config file
        self.loadConfig(config_file)

        #self.setGeometry(self.windowGeometry)
        #self.setFixedSize(1500, 1300)
        #self.resize(self.windowGeometry.width(), self.windowGeometry.height())

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
            self.quit()

        self.initUI()

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

        # Preparation for Trigger Mode
        self.onRadio.setEnabled(False)
        self.offRadio.setEnabled(False)
        self.autoRadio.setEnabled(False)
        self.exposureSlider.setEnabled(False)
        self.gainSlider.setEnabled(False)
        self.delaySlider.setEnabled(False)
        self.lightSlider.setEnabled(False)
        self.ch1RangeSlider.setEnabled(False)
        self.ch1Switch.setEnabled(False)
        self.ch2RangeSlider.setEnabled(False)
        self.ch2Switch.setEnabled(False)
        self.ch3RangeSlider.setEnabled(False)
        self.ch3Switch.setEnabled(False)
        self.aRangeSlider.setEnabled(False)
        self.aSwitch.setEnabled(False)
        self.bRangeSlider.setEnabled(False)
        self.bSwitch.setEnabled(False)
        if self.roiButton.isChecked():
            self.roiButton.click()
        self.roiButton.setEnabled(False)

        self.setWindowTitle(
            'Surface Inspector - Serial#: {0:s}, Config: {1:s}'.format(
                self.visionCamera.getDeviceName(), config_file
            )
        )

        self.visionCamera.setTrigger(FLIRVision.TriggerType.SOFTWARE)
        self.visionCamera.imageArrived.connect(self.onReceiveImage)
        self.visionCamera.enableAcquisition()

        #self.fpsTime = time.time()
        self.elapsedTime.start()
        self.visionCamera.sendSwTrigger()

    def __del__(self):
        del self.visionCamera
        FLIRVision.deinitSystem()

    def initUI(self):
        #self.setMouseTracking(True)
        # TODO: put Label to display an image, Sliders to change exposure, gain, delay, and light-on-time, 
        self.imageCanvas = ImageCanvas() #QtWidgets.QLabel()
        self.imageCanvas.rectChanged.connect(self.setROI)

        exp_tag = QLabel('Exp.')
        self.exposureSlider = QSlider(Qt.Vertical)
        #self.exposureSlider.setMinimumHeight(30)
        #self.exposureSlider.setRange(self.cameraThread.cameraObject.getMinExposure(), self.cameraThread.cameraObject.getMaxExposure())
        self.exposureSlider.setRange(int(self.visionCamera.getMinExposure()), 100000)
        self.exposureSlider.setObjectName('Exposure')
        self.exposureSlider.setFocusPolicy(Qt.StrongFocus)
        self.exposureSlider.setTickPosition(QSlider.NoTicks)
        self.exposureSlider.setTickInterval(1000)
        self.exposureSlider.setSingleStep(100)
        self.exposureSlider.setValue(self.exposureValue)
        '''
        self.exposureSlider.setStyleSheet(":enabled { color: " + foreground + "; background-color: " + color 
                             + " } :disabled { color: " + disabledForeground 
                             + "; background-color: " + disabledColor + " }")
        '''

        self.visionCamera.setExposure(self.exposureValue)
        self.exposureSlider.valueChanged.connect(self.onExposureChangedEvent)
        self.exposureLabel = QLabel(str(self.exposureValue))
        self.exposureLabel.setMinimumWidth(50)
        exp_unit = QLabel('[us]')
        #print('Exposure MinMax:', self.cameraThread.cameraObject.getMinExposure(), self.cameraThread.cameraObject.getMaxExposure())

        gain_tag = QLabel('Gain')
        self.gainSlider = QSlider(Qt.Vertical)
        #self.gainSlider.setMinimumHeight(30)
        self.gainSlider.setRange(int(self.visionCamera.getMinGain()), int(self.visionCamera.getMaxGain()))
        self.gainSlider.setObjectName('Gain')
        self.gainSlider.setFocusPolicy(Qt.StrongFocus)
        self.gainSlider.setTickPosition(QSlider.NoTicks)
        self.gainSlider.setTickInterval(1)
        self.gainSlider.setSingleStep(1)
        self.gainSlider.setValue(self.gainValue)
        self.visionCamera.setGain(self.gainValue)
        self.gainSlider.valueChanged.connect(self.onGainChangedEvent)
        self.gainLabel = QLabel(str(self.gainValue))
        self.gainLabel.setMinimumWidth(50)
        gain_unit = QLabel('[db]')
        #print('Gain MinMax:', self.cameraThread.cameraObject.getMinGain(), self.cameraThread.cameraObject.getMaxGain())

        delay_tag = QLabel('Delay')
        self.delaySlider = QSlider(Qt.Vertical)
        #self.delaySlider.setMinimumHeight(30)
        #self.cameraThread.setExposure(self.exposureValue)
        # TODO: fly the delay of trigger into Arduino
        self.delaySlider.setRange(0, 255)
        self.delaySlider.setObjectName('Delay')
        self.delaySlider.setFocusPolicy(Qt.StrongFocus)
        self.delaySlider.setTickPosition(QSlider.NoTicks)
        self.delaySlider.setTickInterval(10)
        self.delaySlider.setSingleStep(1)
        self.delaySlider.setValue(self.delayValue)
        self.delaySlider.valueChanged.connect(self.onDelayChangedEvent)
        self.delayLabel = QLabel(str(self.delayValue))
        self.delayLabel.setMinimumWidth(50)
        delay_unit = QLabel('[ms]')

        light_tag = QLabel('Light')
        #light_tag.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        light_tag.setAlignment(Qt.AlignCenter)

        self.lightSlider = QSlider(Qt.Vertical)
        #self.lightSlider.setMinimumHeight(30)
        #self.cameraThread.setGain(self.lightValue)
        # TODO: fly the period of lightening into Arduino
        self.lightSlider.setRange(0, 255)
        self.lightSlider.setObjectName('Light')
        self.lightSlider.setFocusPolicy(Qt.StrongFocus)
        self.lightSlider.setTickPosition(QSlider.NoTicks)
        self.lightSlider.setTickInterval(10)
        self.lightSlider.setSingleStep(1)
        self.lightSlider.setValue(self.lightValue)
        self.lightSlider.valueChanged.connect(self.onLightChangedEvent)
        self.lightLabel = QLabel(str(self.lightValue))
        self.lightLabel.setMinimumWidth(50)
        light_unit = QLabel('[ms]')

        grid00_layout = QGridLayout()
        #grid0_layout.setContentsMargins(20,20,20,20)
        grid00_layout.setSpacing(10)
        grid00_layout.setContentsMargins(20,20,20,20)
        grid00_layout.setAlignment(Qt.AlignCenter)
        grid00_layout.addWidget(exp_tag, 0, 0)
        grid00_layout.addWidget(self.exposureSlider, 1, 0)
        grid00_layout.addWidget(self.exposureLabel, 2, 0)
        grid00_layout.addWidget(exp_unit, 3, 0)
        grid00_layout.addWidget(gain_tag, 0, 1)
        grid00_layout.addWidget(self.gainSlider, 1, 1)
        grid00_layout.addWidget(self.gainLabel, 2, 1)
        grid00_layout.addWidget(gain_unit, 3, 1)
        grid00_layout.addWidget(delay_tag, 0, 2)
        grid00_layout.addWidget(self.delaySlider, 1, 2)
        grid00_layout.addWidget(self.delayLabel, 2, 2)
        grid00_layout.addWidget(delay_unit, 3, 2)
        grid00_layout.addWidget(light_tag, 0, 3)
        grid00_layout.addWidget(self.lightSlider, 1, 3)
        grid00_layout.addWidget(self.lightLabel, 2, 3)
        grid00_layout.addWidget(light_unit, 3, 3)

        light_tag = QLabel('Light')
        self.onRadio = QRadioButton('On')
        self.offRadio = QRadioButton('Off')
        self.autoRadio = QRadioButton('Auto')
        self.onRadio.clicked.connect(self.onLightMode)
        self.offRadio.clicked.connect(self.onLightMode)
        self.autoRadio.clicked.connect(self.onLightMode)
        self.onRadio.setChecked(True if self.lightMode == 'On' else False)
        self.offRadio.setChecked(True if self.lightMode == 'Off' else False)
        self.autoRadio.setChecked(True if self.lightMode == 'Auto' else False)
        hbox01_layout = QHBoxLayout()
        hbox01_layout.setSpacing(10)
        hbox01_layout.setContentsMargins(20,20,20,20)
        hbox01_layout.addWidget(self.onRadio)
        hbox01_layout.addWidget(self.offRadio)
        hbox01_layout.addWidget(self.autoRadio)

        vbox01_layout = QVBoxLayout()
        vbox01_layout.setSpacing(10)
        vbox01_layout.setContentsMargins(10,10,10,10)
        vbox01_layout.addLayout(grid00_layout)
        vbox01_layout.addWidget(light_tag)
        vbox01_layout.addLayout(hbox01_layout)

        group00_box = QGroupBox('Control')
        group00_box.setLayout(vbox01_layout)

        hbox0_layout = QHBoxLayout()
        hbox0_layout.addWidget(self.imageCanvas, 1)
        hbox0_layout.addWidget(group00_box)

        ########################################################################
        self.resultLCD = QLCDNumber(3)
        #self.resultLCD.setGeometry(QtCore.QRect(20, 10, 61, 61))
        #self.resultLCD.setFixedSize(400, 300)
        self.resultLCD.setMinimumWidth(400)
        self.resultLCD.setMinimumHeight(300)
        #self.resultLCD.setFixedWidth(200)
        self.resultLCD.setObjectName('resultLCD')
        self.resultLCD.setStyleSheet('QLCDNumber {color: white; border: 0px;}')
        #self.resultLCD.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.resultLCD.setDecMode()
        self.resultLCD.setSegmentStyle(QLCDNumber.Flat)
        self.resultLCD.display('{0:03d}'.format(99))
        self.resultLCD.repaint()
        unit_label = QLabel('%')
        #unit_label.setMinimumWidth(100)
        unit_label.setMinimumHeight(300)
        unit_label.setStyleSheet('font:20pt;')
        #unit_label.setFon
        hbox10_layout = QHBoxLayout()
        hbox10_layout.addWidget(self.resultLCD)
        hbox10_layout.addWidget(unit_label)
        #group10_box = QtWidgets.QGroupBox('Ratio')
        #group10_box.setLayout(hbox10_layout)

        ch1_tag = QLabel('Ch1:')
        '''
        self.ch1ToggleSwitch = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.ch1ToggleSwitch.setRange(0, 1)
        self.ch1ToggleSwitch.setMaximumWidth(50)
        self.ch1ToggleSwitch.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.ch1ToggleSwitch.setTickInterval(10)
        self.ch1ToggleSwitch.setSingleStep(1)
        self.ch1ToggleSwitch.setValue(self.lightValue)
        self.ch1ToggleSwitch.setStyleSheet("QSlider::groove:horizontal {height: 50px; margin: 0 0;}\n")
        #"QSlider::handle:horizontal {background-color: black; border: 1px; height: 40px; width: 40px; margin: 0 0;}\n")
        '''
        self.ch1Switch = Switch(thumb_radius=12, track_radius=15)
        self.ch1Switch.setChecked(self.binCh1Apply)
        self.ch1Switch.toggled.connect(self.onCh1ToggledEvent)
        self.ch1LowerLabel = QLabel(str(self.binRange[0][0]))
        self.ch1UpperLabel = QLabel(str(self.binRange[1][0]))
        self.ch1RangeSlider = RangeSlider(Qt.Horizontal)
        self.ch1RangeSlider.setMinimumHeight(30)
        self.ch1RangeSlider.setMinimum(0)
        self.ch1RangeSlider.setMaximum(255)
        self.ch1RangeSlider.setLow(self.binRange[0][0])
        self.ch1RangeSlider.setHigh(self.binRange[1][0])
        self.ch1RangeSlider.sliderMoved.connect(self.onCh1ChangedEvent)

        ch2_tag = QLabel('Ch2:')
        self.ch2Switch = Switch(thumb_radius=12, track_radius=15)
        self.ch2Switch.setChecked(self.binCh2Apply)
        self.ch2Switch.toggled.connect(self.onCh2ToggledEvent)
        self.ch2LowerLabel = QLabel(str(self.binRange[0][1]))
        self.ch2UpperLabel = QLabel(str(self.binRange[1][1]))
        self.ch2RangeSlider = RangeSlider(Qt.Horizontal)
        self.ch2RangeSlider.setMinimumHeight(30)
        self.ch2RangeSlider.setMinimum(0)
        self.ch2RangeSlider.setMaximum(255)
        self.ch2RangeSlider.setLow(self.binRange[0][1])
        self.ch2RangeSlider.setHigh(self.binRange[1][1])
        self.ch2RangeSlider.sliderMoved.connect(self.onCh2ChangedEvent)

        ch3_tag = QLabel('Ch3:')
        self.ch3Switch = Switch(thumb_radius=12, track_radius=15)
        self.ch3Switch.setChecked(self.binCh3Apply)
        self.ch3Switch.toggled.connect(self.onCh3ToggledEvent)
        self.ch3LowerLabel = QLabel(str(self.binRange[0][2]))
        self.ch3UpperLabel = QLabel(str(self.binRange[1][2]))
        self.ch3RangeSlider = RangeSlider(Qt.Horizontal)
        self.ch3RangeSlider.setMinimumHeight(30)
        self.ch3RangeSlider.setMinimum(0)
        self.ch3RangeSlider.setMaximum(255)
        self.ch3RangeSlider.setLow(self.binRange[0][2])
        self.ch3RangeSlider.setHigh(self.binRange[1][2])
        self.ch3RangeSlider.sliderMoved.connect(self.onCh3ChangedEvent)
        #self.ch1RangeSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)

        a_tag = QLabel('A*:')
        self.aSwitch = Switch(thumb_radius=12, track_radius=15)
        self.aSwitch.setChecked(self.aInspect)
        self.aSwitch.toggled.connect(self.onAToggledEvent)
        self.aLowerLabel = QLabel(str(self.aRange[0][1]))
        self.aUpperLabel = QLabel(str(self.aRange[1][1]))
        self.aRangeSlider = RangeSlider(Qt.Horizontal)
        self.aRangeSlider.setMinimumHeight(30)
        self.aRangeSlider.setMinimum(0)
        self.aRangeSlider.setMaximum(255)
        self.aRangeSlider.setLow(self.aRange[0][1])
        self.aRangeSlider.setHigh(self.aRange[1][1])
        self.aRangeSlider.sliderMoved.connect(self.onAChangedEvent)

        b_tag = QLabel('B*:')
        self.bSwitch = Switch(thumb_radius=12, track_radius=15)
        self.bSwitch.setChecked(self.bInspect)
        self.bSwitch.toggled.connect(self.onBToggledEvent)
        self.bLowerLabel = QLabel(str(self.bRange[0][2]))
        self.bUpperLabel = QLabel(str(self.bRange[1][2]))
        self.bRangeSlider = RangeSlider(Qt.Horizontal)
        self.bRangeSlider.setMinimumHeight(30)
        self.bRangeSlider.setMinimum(0)
        self.bRangeSlider.setMaximum(255)
        self.bRangeSlider.setLow(self.bRange[0][2])
        self.bRangeSlider.setHigh(self.bRange[1][2])
        self.bRangeSlider.sliderMoved.connect(self.onBChangedEvent)

        grid11_layout = QGridLayout()
        grid11_layout.setSpacing(10)
        grid11_layout.setContentsMargins(20,20,20,10)
        grid11_layout.addWidget(ch1_tag, 0, 0)
        grid11_layout.addWidget(self.ch1LowerLabel, 0, 1)
        grid11_layout.addWidget(self.ch1RangeSlider, 0, 2)
        grid11_layout.addWidget(self.ch1UpperLabel, 0, 3)
        grid11_layout.addWidget(self.ch1Switch, 0, 4)
        grid11_layout.addWidget(ch2_tag, 1, 0)
        grid11_layout.addWidget(self.ch2LowerLabel, 1, 1)
        grid11_layout.addWidget(self.ch2RangeSlider, 1, 2)
        grid11_layout.addWidget(self.ch2UpperLabel, 1, 3)
        grid11_layout.addWidget(self.ch2Switch, 1, 4)
        grid11_layout.addWidget(ch3_tag, 2, 0)
        grid11_layout.addWidget(self.ch3LowerLabel, 2, 1)
        grid11_layout.addWidget(self.ch3RangeSlider, 2, 2)
        grid11_layout.addWidget(self.ch3UpperLabel, 2, 3)
        grid11_layout.addWidget(self.ch3Switch, 2, 4)
        grid11_layout.addWidget(a_tag, 3, 0)
        grid11_layout.addWidget(self.aLowerLabel, 3, 1)
        grid11_layout.addWidget(self.aRangeSlider, 3, 2)
        grid11_layout.addWidget(self.aUpperLabel, 3, 3)
        grid11_layout.addWidget(self.aSwitch, 3, 4)
        grid11_layout.addWidget(b_tag, 4, 0)
        grid11_layout.addWidget(self.bLowerLabel, 4, 1)
        grid11_layout.addWidget(self.bRangeSlider, 4, 2)
        grid11_layout.addWidget(self.bUpperLabel, 4, 3)
        grid11_layout.addWidget(self.bSwitch, 4, 4)

        self.group11_box = QGroupBox('ISP')
        self.group11_box.setLayout(grid11_layout)


        hbox1_layout = QHBoxLayout()
        #hbox1_layout.addWidget(group10_box)
        hbox1_layout.addLayout(hbox10_layout)
        hbox1_layout.addWidget(self.group11_box, 1)
        ########################################################

        self.modeButton = QPushButton('Trigger Mode')
        self.modeButton.setCheckable(True)
        self.modeButton.setMinimumHeight(50)
        self.modeButton.toggled.connect(self.onModeToggledEvent)

        self.roiButton = QPushButton('Locked ROI')
        self.roiButton.setCheckable(True)
        self.roiButton.setMinimumHeight(50)
        self.roiButton.toggled.connect(self.onRoiToggledEvent)

        config_button = QPushButton('Save Config')
        config_button.setMinimumHeight(50)
        config_button.clicked.connect(self.onConfigClickedEvent)

        exit_button = QPushButton('Exit')
        exit_button.setMinimumHeight(50)
        #exit_button.clicked.connect(self.exitProgram)
        exit_button.clicked.connect(self.close)

        '''
        self.imageCntLCD = QtWidgets.QLCDNumber(3)
        #self.resultLCD.setMinimumWidth(400)
        #self.resultLCD.setMinimumHeight(300)
        self.imageCntLCD.setObjectName('imageCnt')
        self.imageCntLCD.setStyleSheet('QLCDNumber {color: white; border: 0px;}')
        #self.imageCntLCD.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.imageCntLCD.setDecMode()
        self.imageCntLCD.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.imageCntLCD.display('{0:03d}'.format(99))
        self.imageCntLCD.repaint()
        '''

        self.imageCntSpinBox = CustomSpinBox()
        self.imageCntSpinBox.setMinimumHeight(40)
        #self.imageCntSpinBox.setRange(0, 999)

        #image_spin_box.valueChanged.connect(self.)
        self.imageButton = QPushButton('Save image')
        self.imageButton.setCheckable(True)
        self.imageButton.setMinimumHeight(40)
        self.imageButton.clicked.connect(self.onImageClickedEvent)

        hbox3_layout = QHBoxLayout()
        hbox3_layout.setSpacing(20)
        hbox3_layout.setContentsMargins(20,20,20,10)
        hbox3_layout.addWidget(self.modeButton,1)
        hbox3_layout.addWidget(self.roiButton, 1)
        hbox3_layout.addWidget(config_button, 1)
        hbox3_layout.addWidget(exit_button, 1)
        hbox31_layout = QHBoxLayout()
        #hbox31_layout.addWidget(self.imageCntLCD)
        hbox31_layout.addWidget(self.imageCntSpinBox)
        hbox31_layout.addWidget(self.imageButton, 1)
        hbox3_layout.addLayout(hbox31_layout)

        group3_box = QGroupBox('Operation')
        group3_box.setLayout(hbox3_layout)

        # TODO: Statusbar to print message
        self.statusBar = QStatusBar(self)
        #self.statusBar.showMessage('Hello World.')

        vbox_layout = QVBoxLayout()
        vbox_layout.addLayout(hbox0_layout, 1)
        #vbox_layout.addWidget(self.imageCanvas, 1) # Expanding
        #vbox_layout.addWidget(group1_box)
        #vbox_layout.addWidget(group2_box)
        vbox_layout.addLayout(hbox1_layout)
        vbox_layout.addWidget(group3_box)
        vbox_layout.addWidget(self.statusBar)

        self.setLayout(vbox_layout)

    @pyqtSlot(QRect)
    def setROI(self, rect):
        #self.imageROI = rect.normalized()
        self.imageROIs[self.roiIndex] = [rect.normalized().x(), rect.normalized().y(), rect.normalized().width(), rect.normalized().height()]

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
        processTime = QElapsedTimer()
        processTime.start()
        # start_time = time.time()

        self.latestImage = image

        bin_range = [np.array([0,0,0]), np.array([255,255,255])]
        if self.binCh1Apply:
            bin_range[0][0] = self.binRange[0][0]
            bin_range[1][0] = self.binRange[1][0]
        if self.binCh2Apply:
            bin_range[0][1] = self.binRange[0][1]
            bin_range[1][1] = self.binRange[1][1]
        if self.binCh3Apply:
            bin_range[0][2] = self.binRange[0][2]
            bin_range[1][2] = self.binRange[1][2]

        a_range = None
        if self.aInspect:
            a_range = [np.array(self.aRange[0]), np.array(self.aRange[1])]

        b_range = None
        if self.bInspect:
            b_range = [np.array(self.bRange[0]), np.array(self.bRange[1])]

        copied = image.copy()
        results = []

        '''
        ##################################################################
        for i,roi in enumerate(self.imageROIs):
            y,yend,x,xend = [roi[1], roi[1]+roi[3], roi[0], roi[0]+roi[2]]
            roi_image = image[y:yend,x:xend,:]

            ### Color Processing
            foreground_mask,a_mask,b_mask,rect = self.processImage(roi_image, bin_range, a_range, b_range)
            if foreground_mask is not None:
                common_mask = None
                if a_mask is not None and b_mask is not None:
                    common_mask = cv2.bitwise_and(a_mask, b_mask)

                foregound_count = np.count_nonzero(foreground_mask == 255)
                chroma_count = 0
                if a_mask is not None:
                    chroma_count += np.count_nonzero(a_mask == 255)
                if b_mask is not None:
                    chroma_count += np.count_nonzero(b_mask == 255)
                if common_mask is not None:
                    chroma_count -= np.count_nonzero(common_mask == 255)

                chroma_ratio = int(chroma_count/foregound_count*100.0+0.5)
                results.append('{0:03d}'.format(chroma_ratio))

                # Eye candies
                psuedo_image = np.zeros(roi_image.shape, dtype=np.uint8)
                psuedo_image[foreground_mask == 255] = (255, 255, 255)
                if a_mask is not None: psuedo_image[a_mask == 255] = (255, 0, 0)
                if b_mask is not None: psuedo_image[b_mask == 255] = (0, 0, 255)
                if common_mask is not None: psuedo_image[common_mask == 255] = (255, 0, 255)

                roi_image = cv2.addWeighted(roi_image, 0.4, psuedo_image, 0.6, 0.0)
                if rect is not None:
                    box = cv2.boxPoints(rect)
                    box = np.int0(box) # Points of 4 corners
                    cv2.drawContours(roi_image, [box], 0, (0,255,0), 1)
                copied[y:yend,x:xend,:] = roi_image

            else:
                results.append('bad')

            cv2.drawContours(copied, [np.array([[x,y],[xend-1,y],[xend-1,yend-1],[x,yend-1]])], 0, self.roiColors[i], 1)

        '''
        ### Template matching
        for i,roi in enumerate(self.imageROIs):
            y,yend,x,xend = [roi[1], roi[1]+roi[3], roi[0], roi[0]+roi[2]]
            roi_image = image[y:yend,x:xend,:]
            yuv_image = cv2.cvtColor(roi_image, cv2.COLOR_RGB2YUV)
            bin_image = cv2.inRange(yuv_image, bin_range[0], bin_range[1])

            i,score,loc = self.matchTemplates(bin_image, [x['image'] for x in self.templateFeatures])

            # Eye candies
            template = self.templateFeatures[i]['image']
            temp_h, temp_w = template.shape[:2]
            template_mask = np.zeros(bin_image.shape, dtype=np.uint8)
            template_mask[loc[1]:loc[1]+temp_h, loc[0]:loc[0]+temp_w] = template

            psuedo_image = np.zeros(roi_image.shape, dtype=np.uint8)
            psuedo_image[bin_image == 255] = (255, 255, 255)
            psuedo_image[template_mask == 255] = (255, 0, 0)

            roi_image = cv2.addWeighted(roi_image, 0.5, psuedo_image, 0.5, 0.0)
            copied[y:yend, x:xend, :] = roi_image

            if score <= 0.009:
                results.append('bad')
            else:
                percent_score = int(score * 100.0 + 0.5)
                results.append('{0:03d}'.format(percent_score))

            #cv2.drawContours(copied, [np.array([[x,y], [xend-1,y], [xend-1,yend-1], [x,yend-1]])], 0, self.roiColors[i], 1)
        ###
        '''
        ### Feature match
        for i,roi in enumerate(self.imageROIs):
            y,yend,x,xend = [roi[1], roi[1]+roi[3], roi[0], roi[0]+roi[2]]
            roi_image = image[y:yend,x:xend,:]
            yuv_image = cv2.cvtColor(roi_image, cv2.COLOR_RGB2YUV)
            bin_image = cv2.inRange(yuv_image, bin_range[0], bin_range[1])

            res = self.matchFeatures(bin_image)
            print(res)


            # Eye candies
            template = self.templateFeatures[i]['image']
            temp_h, temp_w = template.shape[:2]
            template_mask = np.zeros(bin_image.shape, dtype=np.uint8)
            template_mask[loc[1]:loc[1]+temp_h, loc[0]:loc[0]+temp_w] = template

            psuedo_image = np.zeros(roi_image.shape, dtype=np.uint8)
            psuedo_image[bin_image == 255] = (255, 255, 255)
            psuedo_image[template_mask == 255] = (255, 0, 0)

            roi_image = cv2.addWeighted(roi_image, 0.5, psuedo_image, 0.5, 0.0)
            copied[y:yend, x:xend, :] = roi_image

            if score <= 0.009:
                results.append('bad')
            else:
                percent_score = int(score * 100.0 + 0.5)
                results.append('{0:03d}'.format(percent_score))

            cv2.drawContours(copied, [np.array([[x,y], [xend-1,y], [xend-1,yend-1], [x,yend-1]])], 0, self.roiColors[i], 1)
        ###
        '''
        '''
        ### OCR
        for i,roi in enumerate(self.imageROIs):
            y,yend,x,xend = [roi[1], roi[1]+roi[3], roi[0], roi[0]+roi[2]]
            roi_image = image[y:yend,x:xend,:]
            yuv_image = cv2.cvtColor(roi_image, cv2.COLOR_RGB2YUV)
            bin_image = cv2.inRange(yuv_image, bin_range[0], bin_range[1])

            with PyTessBaseAPI() as api:
                pil_image = Image.fromarray(bin_image)
                api.SetImage(pil_image)
                boxes = api.GetComponentImages(RIL.TEXTLINE, True)
                print('Found {} textline image components.'.format(len(boxes)))

                for i, (im, box, _, _) in enumerate(boxes):
                    # im is a PIL image object
                    # box is a dict with x, y, w and h keys
                    api.SetRectangle(box['x'], box['y'], box['w'], box['h'])
                    ocrResult = api.GetUTF8Text()
                    conf = api.MeanTextConf()
                    print(u"Box[{0}]: x={x}, y={y}, w={w}, h={h}, "
                          "confidence: {1}, text: {2}".format(i, conf, ocrResult, **box))

            # Eye candies
            psuedo_image = np.zeros(roi_image.shape, dtype=np.uint8)
            psuedo_image[bin_image == 255] = (255, 255, 255)

            roi_image = cv2.addWeighted(roi_image, 0.4, psuedo_image, 0.6, 0.0)
            copied[y:yend, x:xend, :] = roi_image

            cv2.drawContours(copied, [np.array([[x,y], [xend-1,y], [xend-1,yend-1], [x,yend-1]])], 0, self.roiColors[i], 1)
        '''

        ### Display results
        if len(results) == 1:
            self.resultLCD.display(results[0])
            self.resultLCD.repaint()
        else:
            # TODO: append results to board, and display the decision.
            pass

        #time.sleep(0.005) # for nothing to do
        ####################################################################################
        self.imageCanvas.setImage(copied)#, None if self.imageROI is None else self.imageROI)

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
            if self.imageButton.isChecked() is True:
                filename = self.imageCntSpinBox.text() + '.png'
                cv2.imwrite(filename, cv2.cvtColor(self.latestImage, cv2.COLOR_RGB2BGR))
                self.imageCntSpinBox.setValue(self.imageCntSpinBox.value() + 1)

        self.statusBar.showMessage('Process: {0:.3f}[ms], {1:s}'.format(processed, self.fpsMessage))

    @pyqtSlot()
    def onReceiveShutdown(self):
        print('TODO: shutdown()')

    @pyqtSlot(int)
    def onReceiveThreshold(self, value):
        print('TODO: set the threshold value')

    @pyqtSlot()
    def onSenseTrigger(self):
        #self.fpsTime = new_time
        self.visionCamera.sendSwTrigger()
        print('TODO: triggering')

    @pyqtSlot()
    def onResetCount(self):
        #self.camera.imageCount = 0
        pass

    @pyqtSlot(int, int)
    def onCh1ChangedEvent(self, low_value, high_value):
        self.binRange[0][0] = low_value
        self.binRange[1][0] = high_value
        self.ch1LowerLabel.setText(str(low_value))
        self.ch1UpperLabel.setText(str(high_value))

    @pyqtSlot(int, int)
    def onCh2ChangedEvent(self, low_value, high_value):
        self.binRange[0][1] = low_value
        self.binRange[1][1] = high_value
        self.ch2LowerLabel.setText(str(low_value))
        self.ch2UpperLabel.setText(str(high_value))

    @pyqtSlot(int, int)
    def onCh3ChangedEvent(self, low_value, high_value):
        self.binRange[0][2] = low_value
        self.binRange[1][2] = high_value
        self.ch3LowerLabel.setText(str(low_value))
        self.ch3UpperLabel.setText(str(high_value))

    @pyqtSlot(bool)
    def onCh1ToggledEvent(self, checked):
        #print('Ch1:', checked)
        self.binCh1Apply = checked

    @pyqtSlot(bool)
    def onCh2ToggledEvent(self, checked):
        #print('Ch2:', checked)
        self.binCh2Apply = checked

    @pyqtSlot(bool)
    def onCh3ToggledEvent(self, checked):
        #print('Ch3:', checked)
        self.binCh3Apply = checked

    @pyqtSlot(bool)
    def onAToggledEvent(self, checked):
        #print('A*:', checked)
        self.aInspect = checked

    @pyqtSlot(int, int)
    def onAChangedEvent(self, low_value, high_value):
        #print('a*:', value)
        self.aRange[0][1] = low_value
        self.aRange[1][1] = high_value
        self.aLowerLabel.setText(str(low_value))
        self.aUpperLabel.setText(str(high_value))

    @pyqtSlot(bool)
    def onBToggledEvent(self, checked):
        #print('B*:', checked)
        self.bInspect = checked

    @pyqtSlot(int, int)
    def onBChangedEvent(self, low_value, high_value):
        #print('b*:', value)
        self.bRange[0][2] = low_value
        self.bRange[1][2] = high_value
        self.bLowerLabel.setText(str(low_value))
        self.bUpperLabel.setText(str(high_value))

    @pyqtSlot(int)
    def onExposureChangedEvent(self, value):
        #print('Exposure:', value)
        self.exposureLabel.setText(str(value))
        self.visionCamera.setExposure(value)

    @pyqtSlot(int)
    def onGainChangedEvent(self, value):
        #print('Gain:', value)
        self.gainLabel.setText(str(value))
        self.visionCamera.setGain(value)

    @pyqtSlot(int)
    def onDelayChangedEvent(self, value):
        #print('Delay:', value)
        self.delayLabel.setText(str(value))
        if self.serialThread is not None:
            self.serialThread.sendTriggerDelay(value)

    @pyqtSlot(int)
    def onLightChangedEvent(self, value):
        #print('Light:', value)
        self.lightLabel.setText(str(value))
        if self.serialThread is not None:
            self.serialThread.sendLightDuration(value)

    @pyqtSlot()
    def onLightMode(self):
        if self.onRadio.isChecked():
            self.lightMode = 'On'
            if self.serialThread is not None:
                self.serialThread.turnLightOn()
        elif self.offRadio.isChecked():
            self.lightMode = 'Off'
            if self.serialThread is not None:
                self.serialThread.turnLightOff()
        elif self.autoRadio.isChecked():
            self.lightMode = 'Auto'
            if self.serialThread is not None:
                self.serialThread.turnLightAuto()

    @pyqtSlot(bool)
    def onModeToggledEvent(self, state):
        #print('mode:', state)
        if state:
            self.modeButton.setText('Live View')
            #self.cameraThread.setCaptureMode(-1)
            self.visionCamera.sendSwTrigger()
            # self.fpsTime = time.time()
            self.elapsedTime.start()

            self.onRadio.setEnabled(True)
            self.offRadio.setEnabled(True)
            self.autoRadio.setEnabled(True)
            self.exposureSlider.setEnabled(True)
            self.gainSlider.setEnabled(True)
            self.delaySlider.setEnabled(True)
            self.lightSlider.setEnabled(True)
            self.ch1RangeSlider.setEnabled(True)
            self.ch1Switch.setEnabled(True)
            self.ch2RangeSlider.setEnabled(True)
            self.ch2Switch.setEnabled(True)
            self.ch3RangeSlider.setEnabled(True)
            self.ch3Switch.setEnabled(True)
            self.aRangeSlider.setEnabled(True)
            self.aSwitch.setEnabled(True)
            self.bRangeSlider.setEnabled(True)
            self.bSwitch.setEnabled(True)
            self.roiButton.setEnabled(True)

            if self.imageButton.isChecked():
                self.imageButton.click()
            self.imageButton.setCheckable(False)
        else:
            self.modeButton.setText('Trigger Mode')
            #self.camera.s

            self.onRadio.setEnabled(False)
            self.offRadio.setEnabled(False)
            self.autoRadio.setEnabled(False)
            self.exposureSlider.setEnabled(False)
            self.gainSlider.setEnabled(False)
            self.delaySlider.setEnabled(False)
            self.lightSlider.setEnabled(False)
            self.ch1RangeSlider.setEnabled(False)
            self.ch1Switch.setEnabled(False)
            self.ch2RangeSlider.setEnabled(False)
            self.ch2Switch.setEnabled(False)
            self.ch3RangeSlider.setEnabled(False)
            self.ch3Switch.setEnabled(False)
            self.aRangeSlider.setEnabled(False)
            self.aSwitch.setEnabled(False)
            self.bRangeSlider.setEnabled(False)
            self.bSwitch.setEnabled(False)
            if self.roiButton.isChecked():
                self.roiButton.click()
            self.roiButton.setEnabled(False)

            self.imageButton.setCheckable(True)

    @pyqtSlot(bool)
    def onRoiToggledEvent(self, state):
        #print('roi:', state)
        if state:
            self.imageCanvas.setRubberBand(True)
            self.roiButton.setText('Unlocked ROI')
        else:
            self.imageCanvas.setRubberBand(False)
            self.roiButton.setText('Locked ROI')

    @pyqtSlot()
    def onImageClickedEvent(self):
        '''
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save image File", "", "PNG Files (*.png);;All Files (*)", options=options)
        if filename:
            fname,fext = os.path.splitext(filename)
            filename += '' if fext == '.png' or fext == '.PNG' else '.png'
            cv2.imwrite(filename, cv2.cvtColor(self.latestImage, cv2.COLOR_RGB2BGR))
        '''
        if self.imageButton.isCheckable() is False:
            filename = self.imageCntSpinBox.text() + '.png'
            cv2.imwrite(filename, cv2.cvtColor(self.latestImage, cv2.COLOR_RGB2BGR))
            self.imageCntSpinBox.setValue(self.imageCntSpinBox.value()+1)

    @pyqtSlot()
    def onConfigClickedEvent(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(self, "Save Configuration File", "", "Json Files (*.json);;All Files (*)", options=options)
        if filename:
            fname,fext = os.path.splitext(filename)
            filename += '' if fext == '.json' or fext == '.JSON' else '.json'
            self.saveConfig(filename)

    @pyqtSlot()
    def exitProgram(self):
        self.close()

    @pyqtSlot()
    def closeEvent(self, event):
        msgbox = QMessageBox(self)
        ret = msgbox.question(self,'Surface Inspector', "Are you sure to close ?", msgbox.Yes | msgbox.No)
        if ret == msgbox.Yes:
            print('I am closing now!')
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
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    win = SurfaceInspectWindow('config.json')
    win.show()

    sys.exit(app.exec_())
