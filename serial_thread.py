#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os
import PyQt5
from PyQt5 import QtCore, QtWidgets, QtGui

import serial
import serial.tools.list_ports

from construct import *
from PyCRC.CRCCCITT import CRCCCITT
#import crc16

class worker(QtCore.QThread):
    shutdownSignal = QtCore.pyqtSignal()
    thresholdSignal = QtCore.pyqtSignal(int)    
    triggerSignal = QtCore.pyqtSignal()
    resetSignal = QtCore.pyqtSignal()

    serialPort = None

    messageRxList = b'' # bytes for handling ASCII-like string
    messageCRC = Struct('message_crc' / Int16ub)
    messageFormat = Struct('sflag' / Const(b'\x7e'),
                           'cmd' / Enum(Int8ub,
					I_AM_READY = 0x00,
                                        ATX_OFF = 0x01,
                                        IMAGE_THRESHOLD = 0x02,
                                        TRIGGER = 0x03,
                                        IMAGE_RATIO = 0x04,
                                        TRIGGER_DELAY = 0x05,
                                        LIGHT_ON = 0x06,
                                        LIGHT_OFF = 0x07,
                                        LIGHT_AUTO = 0x08,
                                        LIGHT_DURATION = 0x09,
                                        RESET_COUNT = 0x0a),
                           'datalen' / Int8ub,
                           'data' / Array(this.datalen, Byte),
                           'crc' / Int16ub)
    
    def buildMessageToSend(self, cmd, data=[]):
        raw = self.messageFormat.build(dict(cmd=cmd,
                                            datalen=len(data),
                                            data=data,
                                            crc=0))

        msg_without_crc = raw[:-2]
        #msg_crc = self.messageCRC.build(dict(message_crc=crc16.crc16xmodem(msg_without_crc)))
        msg_crc = self.messageCRC.build(dict(message_crc=CRCCCITT().calculate(msg_without_crc)))
        msg = msg_without_crc + msg_crc
        #print(msg)
        #c = messageFormat.parse(msg)
        #print(c)
        return msg
    
    def __init__(self, serial_dev, baudrate=115200, parent=None):
        super().__init__()
        self.doLooping = True
        self.serialPort = serial.Serial(serial_dev, baudrate, timeout=0)
        self.sendIAmReady()

    def __del__(self):
        print('Destruct serial thread')
        self.doLooping = False
        self.sleep(0)
        self.wait()
        if self.serialPort is not None: self.serialPort.close()
        #super().__del__()

    @QtCore.pyqtSlot()
    def sendIAmReady(self):
        msg = self.buildMessageToSend('I_AM_READY')
        self.serialPort.write(msg)
        
    @QtCore.pyqtSlot(int)
    def sendARatio(self, a_ratio):
        msg = self.buildMessageToSend('IMAGE_RATIO', [a_ratio])
        self.serialPort.write(msg)

    @QtCore.pyqtSlot(int)
    def sendTriggerDelay(self, delay_ms):
        msg = self.buildMessageToSend('TRIGGER_DELAY', [(delay_ms>>8)&0xff, delay_ms&0xff])
        self.serialPort.write(msg)
        
    @QtCore.pyqtSlot()
    def turnLightOn(self):
        msg = self.buildMessageToSend('LIGHT_ON')
        self.serialPort.write(msg)

    @QtCore.pyqtSlot()
    def turnLightOff(self):
        msg = self.buildMessageToSend('LIGHT_OFF')
        self.serialPort.write(msg)

    @QtCore.pyqtSlot()
    def turnLightAuto(self):
        msg = self.buildMessageToSend('LIGHT_AUTO')
        self.serialPort.write(msg)

    @QtCore.pyqtSlot(int)
    def sendLightDuration(self, ontime_ms):
        msg = self.buildMessageToSend('LIGHT_DURATION', [(ontime_ms>>8)&0xff, ontime_ms&0xff])
        self.serialPort.write(msg)
        
    @QtCore.pyqtSlot()
    def stopRunning(self):
        self.doLooping = False
        self.sleep(0)
    
    def run(self):
        while self.doLooping:
            if self.serialPort.inWaiting():
                self.messageRxList += self.serialPort.read()
                #self.messageRxList.append(ord(incoming))
                #print(incoming)

            if len(self.messageRxList) >= 5:
                #print(self.messageRxList)
                if self.messageRxList[0] == 0x7e:
                    #print(self.messageRxList[2])
                    datalen = self.messageRxList[2]
                    if len(self.messageRxList) >= datalen+5:
                        parsed = self.messageFormat.parse(self.messageRxList)                        
                        #crc = crc16.crc16xmodem(self.messageRxList[:parsed.datalen+5-2])
                        crc = CRCCCITT().calculate(self.messageRxList[:parsed.datalen+5-2])
                        
                        #print(hex(crc), hex(parsed.crc))
                        if crc == parsed.crc:
                            if parsed.cmd == 'ATX_OFF':
                                #print('shutdown')
                                self.shutdownSignal.emit()
                            elif parsed.cmd == 'IMAGE_THRESHOLD':
                                #print('threshold', hex(parsed.data[0]), hex(parsed.data[1]))
                                self.thresholdSignal.emit((parsed.data[0]<<8)+parsed.data[1])
                            elif parsed.cmd == 'TRIGGER':
                                #print('trigger')
                                self.triggerSignal.emit()
                            elif parsed.cmd == 'RESET_COUNT':
                                self.resetSignal.emit()
                                
                            self.messageRxList = self.messageRxList[parsed.datalen+5:]
                        else:
                            self.messageRxList = b''
                else:
                    self.messageRxList = b''
                    
            self.sleep(0)

class SerialTestWindow(QtWidgets.QWidget):
    #vendorID = 0x10c4
    #productID = 0xea60
    vendorID = 0x110a
    productID = 0x1110

    devicePath = ''

    ratioSignal = QtCore.pyqtSignal(int)
    delaySignal = QtCore.pyqtSignal(int)
    durationSignal = QtCore.pyqtSignal(int)

    onLightSignal = QtCore.pyqtSignal()
    offLightSignal = QtCore.pyqtSignal()
    autoLightSignal = QtCore.pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Serial Test')

        com_list = serial.tools.list_ports.comports()
        for com in com_list:
            print('com.vid:', hex(com.vid),
                  'com.pid:', hex(com.pid),
                  'com.serial_number:', com.serial_number)
            if com.vid == self.vendorID and com.pid == self.productID:
                self.devicePath = com.device
                break

        self.devicePath = '/dev/ttyUSB1'
        
        if not self.devicePath:
            self.packetHandler = None
            return
        
        print('device:', self.devicePath)
        self.packetHandler = worker(self.devicePath)

        # Setup signals
        self.packetHandler.shutdownSignal.connect(self.onReceiveShutdown)
        self.packetHandler.thresholdSignal.connect(self.onReceiveThreshold)
        self.packetHandler.triggerSignal.connect(self.onSenseTrigger)
        self.packetHandler.resetSignal.connect(self.onResetCount)
        
        self.ratioSignal.connect(self.packetHandler.sendARatio)
        self.delaySignal.connect(self.packetHandler.sendTriggerDelay)
        self.durationSignal.connect(self.packetHandler.sendLightDuration)
        self.onLightSignal.connect(self.packetHandler.turnLightOn)
        self.offLightSignal.connect(self.packetHandler.turnLightOff)
        self.autoLightSignal.connect(self.packetHandler.turnLightAuto)

        # Initialize UI
        self.ratioTag = QtWidgets.QLabel('A Ratio:')
        self.ratioEdit = QtWidgets.QLineEdit()
        self.ratioEdit.setValidator(QtGui.QIntValidator(0, 100))
        self.ratioEdit.setMaxLength(3)
        self.ratioEdit.setAlignment(QtCore.Qt.AlignRight)
        self.ratioButton = QtWidgets.QPushButton('Send')
        self.ratioButton.clicked.connect(self.onSendRatio)

        self.delayTag = QtWidgets.QLabel('Trigger Delay:')
        self.delayEdit = QtWidgets.QLineEdit()
        self.delayEdit.setValidator(QtGui.QIntValidator(0, 65535))
        self.delayEdit.setMaxLength(5)
        self.delayEdit.setAlignment(QtCore.Qt.AlignRight)
        self.delayButton = QtWidgets.QPushButton('Send')
        self.delayButton.clicked.connect(self.onSendDelay)

        self.durationTag = QtWidgets.QLabel('Light Duration:')
        self.durationEdit = QtWidgets.QLineEdit()
        self.durationEdit.setValidator(QtGui.QIntValidator(0, 65535))
        self.durationEdit.setMaxLength(5)
        self.durationEdit.setAlignment(QtCore.Qt.AlignRight)
        self.durationButton = QtWidgets.QPushButton('Send')
        self.durationButton.clicked.connect(self.onSendDuration)

        self.onRadio = QtWidgets.QRadioButton('Light On')
        self.onRadio.setChecked(False)
        self.offRadio = QtWidgets.QRadioButton('Light Off')
        self.offRadio.setChecked(False)
        self.autoRadio = QtWidgets.QRadioButton('Light Auto')
        self.autoRadio.setChecked(True)

        self.onRadio.clicked.connect(self.onLightMode)
        self.offRadio.clicked.connect(self.onLightMode)
        self.autoRadio.clicked.connect(self.onLightMode)
        
        vbox0 = QtWidgets.QVBoxLayout()
        vbox0.addWidget(self.ratioTag)
        vbox0.addWidget(self.delayTag)
        vbox0.addWidget(self.durationTag)

        vbox1 = QtWidgets.QVBoxLayout()
        vbox1.addWidget(self.ratioEdit)
        vbox1.addWidget(self.delayEdit)
        vbox1.addWidget(self.durationEdit)

        vbox2 = QtWidgets.QVBoxLayout()
        vbox2.addWidget(self.ratioButton)
        vbox2.addWidget(self.delayButton)
        vbox2.addWidget(self.durationButton)
        
        hbox0 = QtWidgets.QHBoxLayout()
        hbox0.addLayout(vbox0, 1)
        hbox0.addLayout(vbox1)
        hbox0.addLayout(vbox2)

        gbox0 = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.TopToBottom)        
        gbox0.addLayout(hbox0)
        group0 = QtWidgets.QGroupBox('Send Param.')
        group0.setLayout(gbox0)
        
        gbox1 = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.TopToBottom)        
        gbox1.addWidget(self.onRadio)
        gbox1.addWidget(self.offRadio)
        gbox1.addWidget(self.autoRadio)
        group1 = QtWidgets.QGroupBox('Light On/Off/Auto')
        group1.setLayout(gbox1)
        
        vbox3 = QtWidgets.QVBoxLayout()
        vbox3.addWidget(group0)
        vbox3.addWidget(group1)

        self.setLayout(vbox3)

        self.packetHandler.start()

        self.expiredCount = 0
        self.updateTimer = QtCore.QTimer()
        self.updateTimer.setSingleShot(False)
        self.updateTimer.timeout.connect(self.sendData)
        self.updateTimer.start(100)

    def sendData(self):
        if self.expiredCount > 100:
            self.expiredCount = 0
            
        self.ratioSignal.emit(self.expiredCount)
        self.expiredCount += 1
        
    @QtCore.pyqtSlot()
    def onSendRatio(self):
        a_ratio = int(self.ratioEdit.text())
        print('A ratio:', a_ratio)
        self.ratioSignal.emit(a_ratio)
        
    @QtCore.pyqtSlot()
    def onSendDelay(self):
        trigger_delay = int(self.delayEdit.text())
        print('Trigger Delay:', trigger_delay)
        self.delaySignal.emit(trigger_delay)

    @QtCore.pyqtSlot()
    def onSendDuration(self):
        light_duration = int(self.durationEdit.text())
        print('Light duration:', light_duration)
        self.durationSignal.emit(light_duration)

    @QtCore.pyqtSlot()
    def onLightMode(self):
        if self.onRadio.isChecked():
            print('Light on')
            self.onLightSignal.emit()
        elif self.offRadio.isChecked():
            print('Light off')
            self.offLightSignal.emit()
        elif self.autoRadio.isChecked():
            print('Light auto')
            self.autoLightSignal.emit()

    @QtCore.pyqtSlot()
    def onReceiveShutdown(self):
        print('Received the shutdown message!')

    @QtCore.pyqtSlot(int)
    def onReceiveThreshold(self, thres):
        print('Received the threshold:', thres)

    @QtCore.pyqtSlot()
    def onSenseTrigger(self):
        print('Sensed trigger!')

    @QtCore.pyqtSlot()
    def onResetCount(self):
        print('Reset Count!')
        
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = SerialTestWindow()
    win.show()
    sys.exit(app.exec_())
    
'''
msg = buildMessageToSend('LIGHT_ON')

if len(msg) >= 5:
    if msg[0] == 0x7e:
        c = messageFormat.parse(msg)
        if len(msg) >= c.datalen+5:
            crc = crc16.crc16xmodem(msg[:c.datalen+5-2])
            if crc == c.crc:
                print(msg.cmd)
                
                msg = msg[c.datalen+5:]
                print(msg)
            else:
                msg = []
    else:
        msg = []
'''

'''
buffer = raw[:-2]
print(hex(CRCCCITT().calculate(buffer)))

print(hex(crc16.crc16xmodem(buffer)))
'''
'''
serialPort = serial.Serial('/dev/ttyUSB0', 19200, timeout=0)
Rxbuffer = []

# TODO: receiving, parsing and signaling into main
def threading():
    while True:
        ch = serialPort.read()
        rxBuffer.append(ord(ch))
'''
