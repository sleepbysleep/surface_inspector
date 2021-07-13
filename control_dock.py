import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

class ControlPanel(QWidget):
    exposureChanged = pyqtSignal(int)
    gainChanged = pyqtSignal(int)
    delayChanged = pyqtSignal(int)
    lightChanged = pyqtSignal(int)
    lightModeChanged = pyqtSignal(str)

    def __init__(self, exposure:tuple=None, gain:tuple=None, delay:tuple=None, light:tuple=None, light_mode:str=None, parent=None):
        super().__init__(parent)

        self.createSignals()
        self.initAssets(exposure, gain, delay, light, light_mode)
        self.initUI()

    def createSignals(self):
        pass

    def setExposureUI(self, exposure):
        self.exposureMinValue = exposure[0]
        self.exposureMaxValue = exposure[1]
        self.exposureValue = exposure[2]

        self.exposureSpin.setRange(self.exposureMinValue, self.exposureMaxValue)
        self.exposureSpin.lineEdit().setText(str(self.exposureValue))

        self.exposureSlider.setRange(self.exposureMinValue, self.exposureMaxValue)
        self.exposureSlider.setValue(self.exposureValue)

    def setGainUI(self, gain):
        self.gainMinValue = gain[0]
        self.gainMaxValue = gain[1]
        self.gainValue = gain[2]

        self.gainSpin.setRange(self.gainMinValue, self.gainMaxValue)
        self.gainSpin.lineEdit().setText(str(self.gainValue))

        self.gainSlider.setRange(self.gainMinValue, self.gainMaxValue)
        self.gainSlider.setValue(self.gainValue)

    def initAssets(self, exposure:tuple=None, gain:tuple=None, delay:tuple=None, light:tuple=None, light_mode:str=None):
        self.visionCamera = None
        self.serialThread = None

        if exposure:
            self.exposureMinValue = exposure[0]
            self.exposureMaxValue = exposure[1]
            self.exposureValue = exposure[2]
        else:
            self.exposureMinValue = 10
            self.exposureMaxValue = 10000
            self.exposureValue = 100

        if gain:
            self.gainMinValue = gain[0]
            self.gainMaxValue = gain[1]
            self.gainValue = gain[2]
        else:
            self.gainMinValue = 0
            self.gainMaxValue = 100
            self.gainValue = 1

        if delay:
            self.delayMinValue = delay[0]
            self.delayMaxValue = delay[1]
            self.delayValue = delay[2]
        else:
            self.delayMinValue = 0
            self.delayMaxValue = 255
            self.delayValue = 1

        if light:
            self.lightMinValue = light[0]
            self.lightMaxValue = light[1]
            self.lightValue = light[2]
        else:
            self.lightMinValue = 0
            self.lightMaxValue = 255
            self.lightValue = 2

        if light_mode:
            self.lightMode = light_mode
        else:
            self.lightMode = "Auto"

    def initUI(self):
        # initialize the exposure slider
        self.exposureSpin = QSpinBox()
        self.exposureSpin.setRange(self.exposureMinValue, self.exposureMaxValue)
        self.exposureSpin.lineEdit().setText(str(self.exposureValue))
        self.exposureSpin.valueChanged.connect(self.onExposureChangedEvent)
        # self.exposureLabel.setMinimumWidth(width)
        width = self.exposureSpin.sizeHint().width()
        self.exposureSpin.setAlignment(Qt.AlignCenter)

        # self.exposureLabel.setMinimumWidth(width) #setMinimumWidth(width)
        # self.exposureLabel.setText(str(self.exposureValue))
        # self.exposureLabel.setAlignment(Qt.AlignCenter)

        exp_tag = QLabel("Exp.")
        exp_tag.setMinimumWidth(width)
        exp_tag.setAlignment(Qt.AlignCenter)
        exp_unit = QLabel('[us]')
        exp_unit.setMinimumWidth(width)
        exp_unit.setAlignment(Qt.AlignCenter)
        self.exposureSlider = QSlider(Qt.Vertical)
        self.exposureSlider.setMinimumWidth(width)
        self.exposureSlider.setObjectName('Exposure')
        self.exposureSlider.setFocusPolicy(Qt.StrongFocus)
        self.exposureSlider.setTickPosition(QSlider.NoTicks)
        #self.exposureSlider.setMinimumHeight(30)
        #self.exposureSlider.setRange(self.cameraThread.cameraObject.getMinExposure(), self.cameraThread.cameraObject.getMaxExposure())
        self.exposureSlider.setRange(self.exposureMinValue, self.exposureMaxValue)
        self.exposureSlider.setTickInterval(1000)
        self.exposureSlider.setSingleStep(100)
        self.exposureSlider.valueChanged.connect(self.onExposureChangedEvent)
        self.exposureSlider.setValue(self.exposureValue)
        '''
        self.exposureSlider.setStyleSheet(":enabled { color: " + foreground + "; background-color: " + color 
                             + " } :disabled { color: " + disabledForeground 
                             + "; background-color: " + disabledColor + " }")
        '''
        # if self.visionCamera:
        #     self.visionCamera.setExposure(self.exposureValue)

        #print('Exposure MinMax:', self.cameraThread.cameraObject.getMinExposure(), self.cameraThread.cameraObject.getMaxExposure())

        # initialize the gain slider
        gain_tag = QLabel('Gain')
        gain_tag.setMinimumWidth(width)
        gain_tag.setAlignment(Qt.AlignCenter)
        self.gainSpin = QSpinBox()
        self.gainSpin.setMinimumWidth(width)
        self.gainSpin.setAlignment(Qt.AlignCenter)
        self.gainSpin.setRange(self.gainMinValue, self.gainMaxValue)
        self.gainSpin.lineEdit().setText(str(self.gainValue))
        self.gainSpin.valueChanged.connect(self.onGainChangedEvent)
        gain_unit = QLabel('[db]')
        gain_unit.setMinimumWidth(width)
        gain_unit.setAlignment(Qt.AlignCenter)
        self.gainSlider = QSlider(Qt.Vertical)
        self.gainSlider.setMinimumWidth(width)
        self.gainSlider.setObjectName('Gain')
        self.gainSlider.setFocusPolicy(Qt.StrongFocus)
        self.gainSlider.setTickPosition(QSlider.NoTicks)
        #self.gainSlider.setMinimumHeight(30)
        self.gainSlider.setRange(self.gainMinValue, self.gainMaxValue)
        self.gainSlider.setTickInterval(1)
        self.gainSlider.setSingleStep(1)
        self.gainSlider.valueChanged.connect(self.onGainChangedEvent)
        self.gainSlider.setValue(self.gainValue)
        # if self.visionCamera: self.visionCamera.setGain(self.gainValue)

        #print('Gain MinMax:', self.cameraThread.cameraObject.getMinGain(), self.cameraThread.cameraObject.getMaxGain())

        # initialize the delay time
        delay_tag = QLabel('Delay')
        delay_tag.setMinimumWidth(width)
        delay_tag.setAlignment(Qt.AlignCenter)
        self.delaySpin = QSpinBox()
        self.delaySpin.setMinimumWidth(width)
        self.delaySpin.setAlignment(Qt.AlignCenter)
        self.delaySpin.setRange(self.delayMinValue, self.delayMaxValue)
        self.delaySpin.lineEdit().setText(str(self.delayValue))
        self.delaySpin.valueChanged.connect(self.onDelayChangedEvent)
        # self.delayLabel.setMinimumWidth(50)
        delay_unit = QLabel('[ms]')
        delay_unit.setMinimumWidth(width)
        delay_unit.setAlignment(Qt.AlignCenter)
        self.delaySlider = QSlider(Qt.Vertical)
        self.delaySlider.setMinimumWidth(width)
        #self.delaySlider.setMinimumHeight(30)
        #self.cameraThread.setExposure(self.exposureValue)
        # TODO: fly the delay of trigger into Arduino
        self.delaySlider.setObjectName('Delay')
        self.delaySlider.setFocusPolicy(Qt.StrongFocus)
        self.delaySlider.setTickPosition(QSlider.NoTicks)
        self.delaySlider.setRange(self.delayMinValue, self.delayMaxValue)
        self.delaySlider.setTickInterval(10)
        self.delaySlider.setSingleStep(1)
        self.delaySlider.valueChanged.connect(self.onDelayChangedEvent)
        self.delaySlider.setValue(self.delayValue)

        light_tag = QLabel('Light')
        light_tag.setMinimumWidth(width)
        light_tag.setAlignment(Qt.AlignCenter)
        self.lightSpin = QSpinBox()
        self.lightSpin.setMinimumWidth(width)
        self.lightSpin.setAlignment(Qt.AlignCenter)
        self.lightSpin.setRange(self.lightMinValue, self.lightMaxValue)
        self.lightSpin.lineEdit().setText(str(self.lightValue))
        self.lightSpin.valueChanged.connect(self.onLightChangedEvent)
        light_unit = QLabel('[ms]')
        light_unit.setMinimumWidth(width)
        light_unit.setAlignment(Qt.AlignCenter)
        self.lightSlider = QSlider(Qt.Vertical)
        self.lightSlider.setMinimumWidth(width)
        self.lightSlider.setObjectName('Light')
        self.lightSlider.setFocusPolicy(Qt.StrongFocus)
        self.lightSlider.setTickPosition(QSlider.NoTicks)
        #self.lightSlider.setMinimumHeight(30)
        #self.cameraThread.setGain(self.lightValue)
        # TODO: fly the period of lightening into Arduino
        self.lightSlider.setRange(self.lightMinValue, self.lightMaxValue)
        self.lightSlider.setTickInterval(10)
        self.lightSlider.setSingleStep(1)
        self.lightSlider.valueChanged.connect(self.onLightChangedEvent)
        self.lightSlider.setValue(self.lightValue)

        grid00_layout = QGridLayout()
        # grid00_layout.setSpacing(8)
        # grid00_layout.setContentsMargins(8,8,8,8)
        #grid00_layout.sizeConstraint = QLayout.SetDefaultConstraint
        grid00_layout.setAlignment(Qt.AlignCenter)
        grid00_layout.addWidget(exp_tag, 0, 0)
        grid00_layout.addWidget(self.exposureSlider, 1, 0)
        grid00_layout.addWidget(self.exposureSpin, 2, 0)
        grid00_layout.addWidget(exp_unit, 3, 0)
        grid00_layout.addWidget(gain_tag, 0, 1)
        grid00_layout.addWidget(self.gainSlider, 1, 1)
        grid00_layout.addWidget(self.gainSpin, 2, 1)
        grid00_layout.addWidget(gain_unit, 3, 1)
        grid00_layout.addWidget(delay_tag, 0, 2)
        grid00_layout.addWidget(self.delaySlider, 1, 2)
        grid00_layout.addWidget(self.delaySpin, 2, 2)
        grid00_layout.addWidget(delay_unit, 3, 2)
        grid00_layout.addWidget(light_tag, 0, 3)
        grid00_layout.addWidget(self.lightSlider, 1, 3)
        grid00_layout.addWidget(self.lightSpin, 2, 3)
        grid00_layout.addWidget(light_unit, 3, 3)

        light_tag = QLabel('Light Switch')
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
        # hbox01_layout.setSpacing(8)
        # hbox01_layout.setContentsMargins(8,8,8,8)
        hbox01_layout.addWidget(self.onRadio)
        hbox01_layout.addWidget(self.offRadio)
        hbox01_layout.addWidget(self.autoRadio)

        vbox01_layout = QVBoxLayout()
        vbox01_layout.setSpacing(10)
        vbox01_layout.setContentsMargins(10,10,10,10)
        vbox01_layout.addLayout(grid00_layout)
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        # hline.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # hline.setStyleSheet("background-color: #c0c0c0;")
        vbox01_layout.addWidget(hline)
        vbox01_layout.addWidget(light_tag)
        vbox01_layout.addLayout(hbox01_layout)

        self.setLayout(vbox01_layout)

    @pyqtSlot(int)
    def onExposureChangedEvent(self, value):
        #print('Exposure:', value)
        self.exposureSpin.lineEdit().setText(str(value))
        self.exposureSlider.setValue(value)
        self.exposureChanged.emit(value)

    @pyqtSlot(int)
    def onGainChangedEvent(self, value):
        #print('Gain:', value)
        self.gainSpin.lineEdit().setText(str(value))
        self.gainSlider.setValue(value)
        self.gainChanged.emit(value)

    @pyqtSlot(int)
    def onDelayChangedEvent(self, value):
        #print('Delay:', value)
        self.delaySpin.lineEdit().setText(str(value))
        self.delaySlider.setValue(value)
        self.delayChanged.emit(value)

    @pyqtSlot(int)
    def onLightChangedEvent(self, value):
        #print('Light:', value)
        self.lightSpin.lineEdit().setText(str(value))
        self.lightSlider.setValue(value)
        self.lightChanged.emit(value)

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
        self.lightModeChanged.emit(self.lightMode)

    def lockUI(self):
        self.exposureSpin.setEnabled(False)
        self.exposureSlider.setEnabled(False)
        self.gainSpin.setEnabled(False)
        self.gainSlider.setEnabled(False)
        self.delaySpin.setEnabled(False)
        self.delaySlider.setEnabled(False)
        self.lightSpin.setEnabled(False)
        self.lightSlider.setEnabled(False)
        self.onRadio.setEnabled(False)
        self.offRadio.setEnabled(False)
        self.autoRadio.setEnabled(False)

    def unlockUI(self):
        self.exposureSpin.setEnabled(True)
        self.exposureSlider.setEnabled(True)
        self.gainSpin.setEnabled(True)
        self.gainSlider.setEnabled(True)
        self.delaySpin.setEnabled(True)
        self.delaySlider.setEnabled(True)
        self.lightSpin.setEnabled(True)
        self.lightSlider.setEnabled(True)
        self.onRadio.setEnabled(True)
        self.offRadio.setEnabled(True)
        self.autoRadio.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ControlPanel()
    win.show()
    sys.exit(app.exec_())