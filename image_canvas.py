from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import numpy as np
from numpy2qimage import *

# cv2.color
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

    def setRubberBand(self, state:bool):
        self.allowRubberBand = state

    def mousePressEvent(self, event):
        if self.viewRect and self.viewRect.contains(event.pos()) and self.allowRubberBand and event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            #self.rectChanged.emit(self.rubberBand.geometry())
            self.rubberBand.show()
            self.changeRubberBand = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.viewRect and self.viewRect.contains(event.pos()) and self.changeRubberBand:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
            #self.rectChanged.emit(self.rubberBand.geometry())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.changeRubberBand and event.button() == Qt.LeftButton:
            #self.image2viewTransform.inverted().mapRect(self.rubberBand.geometry())
            view2image = self.image2viewTransform.inverted()[0]
            #print(view2image)
            self.rectChanged.emit(view2image.mapRect(self.rubberBand.geometry()))
            self.rubberBand.hide()
            self.changeRubberBand = False
        super().mouseReleaseEvent(event)

    @pyqtSlot(np.ndarray)
    def setImage(self, image:np.ndarray, rects:list=None, colors:list=None):
        # print("canvas size:", self.width(), self.height())
        qimage = numpy2qimage(image).scaled(self.width(), self.height(), Qt.KeepAspectRatio)
        self.viewRect = QRect(QPoint(int((self.width()-qimage.width())/2.0), int((self.height()-qimage.height())/2.0)), qimage.size())
        # print("self.viewRect:", self.viewRect)
        #self.imageRatio = self.width() / image.shape[1]
        self.image2viewTransform = QTransform(
            qimage.width()/image.shape[1], 0.0,
            0.0, qimage.height()/image.shape[0],
            self.viewRect.topLeft().x(), self.viewRect.topLeft().y()
        )

        if rects and colors:
            for rect,color in zip(rects,colors):
                rt = QRect(rect[1], rect[0], rect[3], rect[2])
                painter = QPainter(qimage)
                painter.setPen(QPen(QColor(color[0],color[1],color[2],100), 3))
                painter.drawRect(self.image2viewTransform.mapRect(rt).translated(-self.viewRect.topLeft()))
                painter.end()
        super().setPixmap(QPixmap.fromImage(qimage))