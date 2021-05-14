import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from range_slider import RangeSlider
# from toggle_switch import Switch

class BinarizePanel(QWidget):
    luminanceChanged = pyqtSignal(int, int)
    aChannelChanged = pyqtSignal(int, int)
    bChannelChanged = pyqtSignal(int, int)
    saveButtonClicked = pyqtSignal()

    def __init__(self, luminance:tuple=(0,255), a_channel:tuple=(0,255), b_channel:tuple=(0,255), parent=None):
        super().__init__(parent)

        self.initAssets()
        self.initUI(luminance, a_channel, b_channel)

    def initAssets(self):
        self.width = 45

    def initUI(self, luminance:tuple, a_channel:tuple, b_chanel:tuple):
        l_tag = QLabel('L')
        l_tag.setMinimumWidth(self.width)
        l_tag.setAlignment(Qt.AlignCenter)
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
        self.lLowerLabel = QLabel(str(luminance[0]))
        self.lLowerLabel.setMinimumWidth(self.width)
        self.lLowerLabel.setAlignment(Qt.AlignCenter)
        self.lUpperLabel = QLabel(str(luminance[1]))
        self.lUpperLabel.setMinimumWidth(self.width)
        self.lUpperLabel.setAlignment(Qt.AlignCenter)
        self.lRangeSlider = RangeSlider(Qt.Vertical)
        self.lRangeSlider.setMinimumWidth(self.width)
        # self.lRangeSlider.setAlignment(Qt.AlignCenter)
        self.lRangeSlider.setMinimum(0)
        self.lRangeSlider.setMaximum(255)
        self.lRangeSlider.setLow(luminance[0])
        self.lRangeSlider.setHigh(luminance[1])
        self.lRangeSlider.sliderMoved.connect(self.onLChangedEvent)

        a_tag = QLabel('a*')
        a_tag.setMinimumWidth(self.width)
        a_tag.setAlignment(Qt.AlignCenter)
        self.aLowerLabel = QLabel(str(a_channel[0]))
        self.aLowerLabel.setMinimumWidth(self.width)
        self.aLowerLabel.setAlignment(Qt.AlignCenter)
        self.aUpperLabel = QLabel(str(a_channel[1]))
        self.aUpperLabel.setMinimumWidth(self.width)
        self.aUpperLabel.setAlignment(Qt.AlignCenter)
        self.aRangeSlider = RangeSlider(Qt.Vertical)
        self.aRangeSlider.setMinimumWidth(self.width)
        self.aRangeSlider.setMinimum(0)
        self.aRangeSlider.setMaximum(255)
        self.aRangeSlider.setLow(a_channel[0])
        self.aRangeSlider.setHigh(a_channel[1])
        self.aRangeSlider.sliderMoved.connect(self.onAChangedEvent)

        b_tag = QLabel('b*')
        b_tag.setMinimumWidth(self.width)
        b_tag.setAlignment(Qt.AlignCenter)
        self.bLowerLabel = QLabel(str(b_chanel[0]))
        self.bLowerLabel.setMinimumWidth(self.width)
        self.bLowerLabel.setAlignment(Qt.AlignCenter)
        self.bUpperLabel = QLabel(str(b_chanel[1]))
        self.bUpperLabel.setMinimumWidth(self.width)
        self.bUpperLabel.setAlignment(Qt.AlignCenter)
        self.bRangeSlider = RangeSlider(Qt.Vertical)
        self.bRangeSlider.setMinimumWidth(self.width)
        self.bRangeSlider.setMinimum(0)
        self.bRangeSlider.setMaximum(255)
        self.bRangeSlider.setLow(b_chanel[0])
        self.bRangeSlider.setHigh(b_chanel[1])
        self.bRangeSlider.sliderMoved.connect(self.onBChangedEvent)
        # self.ch1RangeSlider.setTickPosition(QtWidgets.QSlider.TicksBelow)

        grid11_layout = QGridLayout()
        # grid11_layout.setSpacing(10)
        # grid11_layout.setContentsMargins(20, 20, 20, 10)
        grid11_layout.addWidget(l_tag, 0, 0)
        grid11_layout.addWidget(self.lUpperLabel, 1, 0)
        grid11_layout.addWidget(self.lRangeSlider, 2, 0)
        grid11_layout.addWidget(self.lLowerLabel, 3, 0)
        grid11_layout.addWidget(a_tag, 0, 1)
        grid11_layout.addWidget(self.aUpperLabel, 1, 1)
        grid11_layout.addWidget(self.aRangeSlider, 2, 1)
        grid11_layout.addWidget(self.aLowerLabel, 3, 1)
        grid11_layout.addWidget(b_tag, 0, 2)
        grid11_layout.addWidget(self.bUpperLabel, 1, 2)
        grid11_layout.addWidget(self.bRangeSlider, 2, 2)
        grid11_layout.addWidget(self.bLowerLabel, 3, 2)

        self.saveButton = QPushButton('Save Binary')
        self.saveButton.setMinimumHeight(50)
        self.saveButton.clicked.connect(self.onSaveEvent)

        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        # hline.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # hline.setStyleSheet("background-color: #c0c0c0;")
        vbox_layout = QVBoxLayout()
        vbox_layout.setSpacing(10)
        vbox_layout.setContentsMargins(10,10,10,10)
        vbox_layout.addLayout(grid11_layout, 1)
        vbox_layout.addWidget(hline)
        vbox_layout.addWidget(self.saveButton)

        self.setLayout(vbox_layout)

    @pyqtSlot(int, int)
    def onLChangedEvent(self, low_value, high_value):
        self.lLowerLabel.setText(str(low_value))
        self.lUpperLabel.setText(str(high_value))
        self.lRangeSlider.setLow(low_value)
        self.lRangeSlider.setHigh(high_value)
        self.luminanceChanged.emit(low_value, high_value)

    @pyqtSlot(int, int)
    def onAChangedEvent(self, low_value, high_value):
        self.aLowerLabel.setText(str(low_value))
        self.aUpperLabel.setText(str(high_value))
        self.aRangeSlider.setLow(low_value)
        self.aRangeSlider.setHigh(high_value)
        self.aChannelChanged.emit(low_value, high_value)

    @pyqtSlot(int, int)
    def onBChangedEvent(self, low_value, high_value):
        self.bLowerLabel.setText(str(low_value))
        self.bUpperLabel.setText(str(high_value))
        self.bRangeSlider.setLow(low_value)
        self.bRangeSlider.setHigh(high_value)
        self.bChannelChanged.emit(low_value, high_value)

    def lockUI(self):
        self.lRangeSlider.setEnabled(False)
        self.aRangeSlider.setEnabled(False)
        self.bRangeSlider.setEnabled(False)
        self.saveButton.setEnabled(False)

    def unlockUI(self):
        self.lRangeSlider.setEnabled(True)
        self.aRangeSlider.setEnabled(True)
        self.bRangeSlider.setEnabled(True)
        self.saveButton.setEnabled(True)

    def onSaveEvent(self):
        self.saveButtonClicked.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = BinarizePanel((0, 255), (0, 255), (0, 255))
    win.show()
    sys.exit(app.exec_())