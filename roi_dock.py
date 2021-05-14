import sys
import os
import cv2
import numpy as np

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from toggle_switch import Switch

class ROIPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.mom = parent
        self.initAssets()
        self.initUI()

    def initAssets(self):
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
        self.roi_colors = [
            (128, 0, 0),  # Marron
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
            (230, 190, 255) # Lavender
        ]
        self.roi_rects = [[y*60, x*60, 50, 50] for y in range(4) for x in range(4) ]
        self.switch_thumb_size = 12
        self.switch_track_size = 15
        self.enable_list = [ False for x in range(16) ]
        self.current_index = 0
        self.is_activated = False

    def initUI(self):
        self.widgetList = []
        grid = QGridLayout()
        for i,color in enumerate(self.roi_colors):
            radio = QRadioButton()#f"ROI{i:02d}")
            radio.setStyleSheet("QRadioButton::indicator { width : 20px; height : 20px; }")
            radio.clicked.connect(lambda state,index=i : self.onRadioClickEvent(index,state))
            if i == 0: radio.setChecked(True)
            else: radio.setChecked(False)
            label = QLabel(f" - ROI {i:>2d} - ")
            label.setStyleSheet("QLabel { background-color: rgb(%d,%d,%d); }"%(color[0],color[1],color[2]))
            button = Switch(thumb_radius=self.switch_thumb_size, track_radius=self.switch_track_size)
            button.toggled.connect(lambda state,index=i : self.onToggledEvent(index, state))
            grid.addWidget(radio, i, 2)
            grid.addWidget(label, i, 0)
            grid.addWidget(button, i, 1)
            self.widgetList.append(radio)
            self.widgetList.append(button)

        vbox = QVBoxLayout()
        vbox.setSpacing(10)
        vbox.setContentsMargins(10,10,10,10)
        vbox.addLayout(grid)
        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        vbox.addWidget(hline)

        button = QPushButton("Activate ROIs")
        button.setCheckable(True)
        button.setMinimumHeight(50)
        button.toggled.connect(self.onModeToggledEvent)
        vbox.addWidget(button)
        self.widgetList.append(button)

        self.setLayout(vbox)

    def lockUI(self):
        for item in self.widgetList:
            item.setEnabled(False)

    def unlockUI(self):
        for item in self.widgetList:
            item.setEnabled(True)

    def updateUI(self):
        for i,checked in enumerate(self.enable_list):
            self.widgetList[2*i+1].setChecked(checked)
        self.widgetList[-1].setChecked(self.is_activated)

    def onToggledEvent(self, index, state):
        self.enable_list[index] = state

    def onRadioClickEvent(self, index, state):
        # print("radio:", index, state)
        self.current_index = index

    def onModeToggledEvent(self, state):
        self.mom.imageCanvas.setRubberBand(state)
        self.is_activated = state

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ROIPanel()
    win.show()
    sys.exit(app.exec_())