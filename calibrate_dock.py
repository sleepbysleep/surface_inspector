import sys
import os
import cv2
import numpy as np

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from camera_calibrate.generic_model import GenericModel
from toggle_switch import Switch

import utils

# cv2.setUseOpenVX(True)
# cv2.setUseOptimized(True)
# print(cv2.getBuildInformation())
'''
#include <opencv2/imgcodecs.hpp>
#include <opencv2/mcc.hpp>
#include <iostream>
using namespace std;
using namespace cv;
using namespace mcc;
using namespace ccm;
int main(int argc, char *argv[])
{
   // [get_messages_of_image]： Get image messages 
   string filepath = "input.png"; //  Enter the image path 
   Mat image = imread(filepath, IMREAD_COLOR);
   Mat imageCopy = image.clone();
   Ptr<CCheckerDetector> detector = CCheckerDetector::create();
   // [get_color_checker]： Get ready ColorChecker testing 
   vector<Ptr<mcc::CChecker>> checkers = detector->getListColorChecker();
   for (Ptr<mcc::CChecker> checker : checkers)
   {
       // [create]： establish CCheckerDetector object , And use getListColorChecker Function to obtain ColorChecker Information .
       Ptr<CCheckerDraw> cdraw = CCheckerDraw::create(checker);
       cdraw->draw(image);
       Mat chartsRGB = checker->getChartsRGB();
       Mat src = chartsRGB.col(1).clone().reshape(3, chartsRGB.rows/3);
       src /= 255.0;
       // [get_ccm_Matrix]： For each ColorChecker, You can calculate one ccm Matrix for color correction .Model1 yes ColorCorrectionModel Class object , You can modify the parameters as needed to get the best color correction effect .
       ColorCorrectionModel model1(src, COLORCHECKER_Vinyl);
       model1.run();
       Mat ccm = model1.getCCM();
       std::cout<<"ccm "<<ccm<<std::endl;
       double loss = model1.getLoss();
       std::cout<<"loss "<<loss<<std::endl;

       // [make_color_correction]： Member functions infer_image For the use of ccm Matrix correction .
       Mat img_;
       cvtColor(image, img_, COLOR_BGR2RGB);
       img_.convertTo(img_, CV_64F);
       const int inp_size = 255;
       const int out_size = 255;
       img_ = img_ / inp_size;
       Mat calibratedImage= model1.infer(img_);
       Mat out_ = calibratedImage * out_size;
       // [Save_calibrated_image]： Save the calibrated image .
       out_.convertTo(out_, CV_8UC3);
       Mat img_out = min(max(out_, 0), out_size);
       Mat out_img;
       cvtColor(img_out, out_img, COLOR_RGB2BGR);
       imwrite("output.png",out_img);
   }

   return 0;
}

import cv2
import numpy as np

import os

image_path = 'E:/datasets/biseka.png'

img = cv2.imdecode(np.fromfile(image_path,dtype=np.uint8),-1)

cv2.imshow('img', img)
cv2.waitKey(0)

detector = cv2.mcc.CCheckerDetector_create()

detector.process(img, cv2.mcc.MCC24)

# cv2.mcc_CCheckerDetector.getBestColorChecker()
checker = detector.getBestColorChecker()

cdraw = cv2.mcc.CCheckerDraw_create(checker)
img_draw = img.copy()
cdraw.draw(img_draw)

cv2.imshow('img_draw', img_draw)
cv2.waitKey(0)

chartsRGB = checker.getChartsRGB()

src = chartsRGB[:,1].copy().reshape(24, 1, 3)

src /= 255.0

print(src.shape)
# model1 = cv2.ccm_ColorCorrectionModel(src, cv2.mcc.MCC24)
model1 = cv2.ccm_ColorCorrectionModel(src, cv2.ccm.COLORCHECKER_Macbeth)
# model1 = cv2.ccm_ColorCorrectionModel(src,src,cv2.ccm.COLOR_SPACE_sRGB)
model1.run()
ccm = model1.getCCM()
print("ccm ", ccm)
loss = model1.getLoss()
print("loss ", loss)

img_ = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
img_ = img_.astype(np.float64)
img_ = img_/255
calibratedImage = model1.infer(img_)
out_ = calibratedImage * 255
out_[out_ < 0] = 0
out_[out_ > 255] = 255
out_ = out_.astype(np.uint8)

out_img = cv2.cvtColor(out_, cv2.COLOR_RGB2BGR)

file, ext = os.path.splitext(image_path)
calibratedFilePath = file + '_calibrated' + ext
# cv2.imwrite(calibratedFilePath, out_img)
cv2.imencode(ext, out_img)[1].tofile(calibratedFilePath)

cv2.imshow('out_img', out_img)
cv2.waitKey(0)
'''

class CalibratePanel(QWidget):
    def __init__(self, color_correct_filename:str=None, calibrate_filename:str=None, parent=None):
        super().__init__(parent)

        self.color_correct_filename = color_correct_filename
        self.need_color_checker_detection = False
        self.need_color_correction = False

        # self.color
        self.camera_calibrate_filename = calibrate_filename
        self.need_chessboard_detection = False
        self.need_lens_distortion_correction = False

        self.initAssets()
        self.initUI()

    def initAssets(self):
        self.color_checker_detector = cv2.mcc.CCheckerDetector_create()
        self.color_checker_rgb = None

        self.calibrateModel = GenericModel()
        if self.camera_calibrate_filename and os.path.isfile(self.camera_calibrate_filename):
            self.calibrateModel.loadParamsFromXML(self.camera_calibrate_filename)
        else:
            self.calibrateModel.boardSize = (6,9) # in the order of (h,w)
            self.calibrateModel.squareSize = (50,50) # in the order of (h,w)
            self.calibrateModel.calibrateFlags = cv2.CALIB_RATIONAL_MODEL  # + cv2.CALIB_FIX_K3 + cv2.CALIB_FIX_K4 + cv2.CALIB_FIX_K5 + cv2.CALIB_TILTED_MODEL
            # flags = cv2.CALIB_TILTED_MODEL
            # cv2.CALIB_FIX_ASPECT_RATIO
            # cv2.CALIB_FIX_FOCAL_LENGTH
            # cv2.CALIB_FIX_INTRINSIC
            # cv2.CALIB_FIX_K1 ~ 6
            # cv2.CALIB_FIX_PRINCIPAL_POINT
            # cv2.CALIB_FIX_S1_S2_S3_S4
            # cv2.CALIB_THIN_PRISM_MODEL
            # cv2.CALIB_TILTED_MODEL
            # cv2.CALIB_USE_INTRINSIC_GUESS
            # cv2.CALIB_USE_LU
            # cv2.CALIB_USE_QR
            # cv2.CALIB_ZERO_DISPARITY
            # cv2.CALIB_ZERO_TANGENT_DIST

            self.calibrateModel.undistortSize = None  # in the order of (h,w)
            self.calibrateModel.undistortOffset = (0, 50)  # in the order of (h,w)
            self.calibrateModel.undistortScale = 1.35

    def initUI(self):
        if self.camera_calibrate_filename: fname = os.path.basename(self.camera_calibrate_filename)
        else: fname = "N/A"
        self.camera_calibrate_filename_tag = QLabel(fname)

        detect_chessboard_tag = QLabel("Chessboard Detection:")
        self.detect_chessboard_switch = Switch(thumb_radius=12, track_radius=15)
        self.detect_chessboard_switch.toggled.connect(self.onChessboardDetectToggledEvent)

        horizontal_cross_tag = QLabel('Horizontal Crosses:')
        self.horizontal_cross_spin = QSpinBox()
        self.horizontal_cross_spin.setRange(3, 20)
        self.horizontal_cross_spin.lineEdit().setText(str(self.calibrateModel.boardSize[1]))
        self.horizontal_cross_spin.valueChanged.connect(self.onHCrossChangedEvent)

        vertical_cross_tag = QLabel('Vertical Crosses:')
        self.vertical_cross_spin = QSpinBox()
        self.vertical_cross_spin.setRange(3, 20)
        self.vertical_cross_spin.lineEdit().setText(str(self.calibrateModel.boardSize[0]))
        self.vertical_cross_spin.valueChanged.connect(self.onVCrossChangedEvent)

        square_width_tag = QLabel('Square Width[mm]:')
        self.square_width_spin = QSpinBox()
        self.square_width_spin.setRange(10, 100)
        self.square_width_spin.lineEdit().setText(str(self.calibrateModel.squareSize[1]))
        self.square_width_spin.valueChanged.connect(self.onSWidthChangedEvent)

        square_height_tag = QLabel('Square Height[mm]:')
        self.square_height_spin = QSpinBox()
        self.square_height_spin.setRange(10, 100)
        self.square_height_spin.lineEdit().setText(str(self.calibrateModel.squareSize[0]))
        self.square_height_spin.valueChanged.connect(self.onSHeightChangedEvent)

        scale_tag = QLabel("Undistort Scale:")
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setMinimum(0.1)
        self.scale_spin.setMaximum(20)
        self.scale_spin.setSingleStep(0.05)
        self.scale_spin.setValue(1)
        self.scale_spin.valueChanged.connect(self.onScaleChangedEvent)

        undist_xoff_tag = QLabel("Undistort xoff:")
        self.undist_xoff_spin = QSpinBox()
        self.undist_xoff_spin.setRange(-65535, 65535)
        self.undist_xoff_spin.lineEdit().setText(str(0))
        self.undist_xoff_spin.valueChanged.connect(self.onXoffChangedEvnet)

        undist_yoff_tag = QLabel("Undistort yoff:")
        self.undist_yoff_spin = QSpinBox()
        self.undist_yoff_spin.setRange(-65535, 65535)
        self.undist_yoff_spin.lineEdit().setText(str(0))
        self.undist_yoff_spin.valueChanged.connect(self.onYoffChangedEvnet)

        load_config_tag = QLabel("XML Config.:")
        self.load_config_button = QPushButton("Load")
        self.load_config_button.clicked.connect(self.onLoadCalibrateEvent)

        generate_tag = QLabel("Mapping Table:")
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.onGenerateMapEvent)

        ldc_tag = QLabel("Lens Distortion Correction:")
        self.ldc_switch = Switch(thumb_radius=12, track_radius=15)
        self.ldc_switch.toggled.connect(self.onLensDistortCorrectToggledEvent)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(8,8,8,8)
        grid.sizeConstraint = QLayout.SetDefaultConstraint
        # grid.setAlignment(Qt.AlignCenter)

        grid.addWidget(self.camera_calibrate_filename_tag, 0, 0, 1, 2)
        grid.addWidget(horizontal_cross_tag, 1, 0)
        grid.addWidget(self.horizontal_cross_spin, 1, 1)
        grid.addWidget(vertical_cross_tag, 2, 0)
        grid.addWidget(self.vertical_cross_spin, 2, 1)
        grid.addWidget(square_width_tag, 3, 0)
        grid.addWidget(self.square_width_spin, 3, 1)
        grid.addWidget(square_height_tag, 4, 0)
        grid.addWidget(self.square_height_spin, 4, 1)
        grid.addWidget(detect_chessboard_tag, 5, 0)
        grid.addWidget(self.detect_chessboard_switch, 5, 1, Qt.AlignRight)

        grid.addWidget(scale_tag, 6, 0)
        grid.addWidget(self.scale_spin, 6, 1)
        grid.addWidget(undist_xoff_tag, 7, 0)
        grid.addWidget(self.undist_xoff_spin, 7, 1)
        grid.addWidget(undist_yoff_tag, 8, 0)
        grid.addWidget(self.undist_yoff_spin, 8, 1)
        grid.addWidget(load_config_tag, 9, 0)
        grid.addWidget(self.load_config_button, 9, 1)
        grid.addWidget(generate_tag, 10, 0)
        grid.addWidget(self.generate_button, 10, 1)
        grid.addWidget(ldc_tag, 11, 0)
        grid.addWidget(self.ldc_switch, 11, 1, Qt.AlignRight)

        gbox1 = QGroupBox("Camera Calibration")
        gbox1.setLayout(grid)

        if self.color_correct_filename: fname = os.path.basename(self.color_correct_filename)
        else: fname = "N/A"
        self.color_correct_filename_tag = QLabel(fname)

        detect_colorchecker_tag = QLabel("ColorChecker Detection:")
        self.detect_colorchecker_switch = Switch(thumb_radius=12, track_radius=15)
        self.detect_colorchecker_switch.toggled.connect(self.onColorCheckerDetectToggledEvent)

        save_color_tag = QLabel("Color Patch XML:")
        self.save_color_button = QPushButton("Save")
        self.save_color_button.clicked.connect(self.onSaveColorEvent)

        set_ref_color_tag = QLabel("Ref. Color:")
        self.set_ref_color_button = QPushButton("Set")
        self.set_ref_color_button.clicked.connect(self.onSetColorEvent)

        load_color_tag = QLabel("Ref. Color XML:")
        self.load_color_button = QPushButton("Load")
        self.load_color_button.clicked.connect(self.onLoadColorEvent)

        color_correct_tag = QLabel("Color Correction:")
        self.color_correct_switch = Switch(thumb_radius=12, track_radius=15)
        self.color_correct_switch.toggled.connect(self.onColorCorrectToggledEvent)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(8,8,8,8)
        grid.sizeConstraint = QLayout.SetDefaultConstraint
        # grid.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.color_correct_filename_tag, 0, 0, 1, 2)
        grid.addWidget(detect_colorchecker_tag, 1, 0)
        grid.addWidget(self.detect_colorchecker_switch, 1, 1, Qt.AlignRight)
        grid.addWidget(set_ref_color_tag, 2, 0)
        grid.addWidget(self.set_ref_color_button, 2, 1)
        grid.addWidget(save_color_tag, 3, 0)
        grid.addWidget(self.save_color_button, 3, 1)
        grid.addWidget(load_color_tag, 4, 0)
        grid.addWidget(self.load_color_button, 4, 1)
        grid.addWidget(color_correct_tag, 5, 0)
        grid.addWidget(self.color_correct_switch, 5, 1, Qt.AlignRight)

        gbox2 = QGroupBox("Color Calibration")
        gbox2.setLayout(grid)

        vbox = QVBoxLayout()
        vbox.addWidget(gbox2)
        vbox.addWidget(gbox1)
        vbox.addStretch(1)

        self.setLayout(vbox)

    def lockUI(self):
        self.horizontal_cross_spin.setEnabled(False)
        self.vertical_cross_spin.setEnabled(False)
        self.square_width_spin.setEnabled(False)
        self.square_height_spin.setEnabled(False)
        self.detect_chessboard_switch.setEnabled(False)
        self.scale_spin.setEnabled(False)
        self.undist_xoff_spin.setEnabled(False)
        self.undist_yoff_spin.setEnabled(False)
        self.load_config_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.ldc_switch.setEnabled(False)
        self.detect_colorchecker_switch.setEnabled(False)
        self.set_ref_color_button.setEnabled(False)
        self.save_color_button.setEnabled(False)
        self.load_color_button.setEnabled(False)
        self.color_correct_switch.setEnabled(False)

    def unlockUI(self):
        self.horizontal_cross_spin.setEnabled(True)
        self.vertical_cross_spin.setEnabled(True)
        self.square_width_spin.setEnabled(True)
        self.square_height_spin.setEnabled(True)
        self.detect_chessboard_switch.setEnabled(True)
        self.scale_spin.setEnabled(True)
        self.undist_xoff_spin.setEnabled(True)
        self.undist_yoff_spin.setEnabled(True)
        self.load_config_button.setEnabled(True)
        self.generate_button.setEnabled(True)
        self.ldc_switch.setEnabled(True)
        self.detect_colorchecker_switch.setEnabled(True)
        self.set_ref_color_button.setEnabled(True)
        self.save_color_button.setEnabled(True)
        self.load_color_button.setEnabled(True)
        self.color_correct_switch.setEnabled(True)

    def updateCalibrateUI(self):
        self.horizontal_cross_spin.setValue(self.calibrateModel.boardSize[1])
        self.vertical_cross_spin.setValue(self.calibrateModel.boardSize[0])
        self.square_width_spin.setValue(self.calibrateModel.squareSize[1])
        self.square_height_spin.setValue(self.calibrateModel.squareSize[0])
        self.scale_spin.setValue(self.calibrateModel.undistortScale)
        self.undist_xoff_spin.setValue(self.calibrateModel.undistortOffset[1])
        self.undist_yoff_spin.setValue(self.calibrateModel.undistortOffset[0])
        self.generate_button.click()

    def updateUI(self):
        self.readRefColorFromXML(self.color_correct_filename)
        if self.color_correct_filename: fname = os.path.basename(self.color_correct_filename)
        else: fname = "N/A"
        self.color_correct_filename_tag.setText(fname)
        if self.need_color_correction:
            self.color_correct_switch.setChecked(True)
        else:
            self.color_correct_switch.setChecked(False)

        # self.readCalibrationFromXML(self.camera_calibrate_filename)
        self.calibrateModel.loadParamsFromXML(self.camera_calibrate_filename)
        self.onGenerateMapEvent()
        if self.camera_calibrate_filename: fname = os.path.basename(self.camera_calibrate_filename)
        else: fname = "N/A"
        self.camera_calibrate_filename_tag.setText(fname)
        if self.need_lens_distortion_correction:
            self.ldc_switch.setChecked(True)
        else:
            self.ldc_switch.setChecked(False)

    def onChessboardDetectToggledEvent(self, value):
        # print(value)
        self.need_chessboard_detection = value

    def onLensDistortCorrectToggledEvent(self, value):
        # print(value)
        self.need_lens_distortion_correction = value

    def onColorCheckerDetectToggledEvent(self, value):
        # print(value)
        self.need_color_checker_detection = value

    def onColorCorrectToggledEvent(self, value):
        # print(value)
        self.need_color_correction = value

    def onHCrossChangedEvent(self, value):
        # print(value, type(value))
        self.calibrateModel.boardSize = (self.calibrateModel.boardSize[0],value)

    def onVCrossChangedEvent(self, value):
        # print(value, type(value))
        self.calibrateModel.boardSize = (value,self.calibrateModel.boardSize[1])

    def onSWidthChangedEvent(self, value):
        # print(value, type(value))
        self.calibrateModel.squareSize = (self.calibrateModel.squareSize[0], value)

    def onSHeightChangedEvent(self, value):
        # print(value, type(value))
        self.calibrateModel.squareSize = (value, self.calibrateModel.squareSize[1])

    def onScaleChangedEvent(self, value):
        # print(value, type(value))
        self.calibrateModel.undistortScale = value

    def onXoffChangedEvnet(self, value):
        # print(value, type(value))
        self.calibrateModel.undistortOffset = (self.calibrateModel.undistortOffset[0], value)

    def onYoffChangedEvnet(self, value):
        # print(value, type(value))
        self.calibrateModel.undistortOffset = (value, self.calibrateModel.undistortOffset[1])

    def getFileDialogDirectory(self):
        """Returns starting directory for ``QFileDialog`` file open/save"""
        return ''

    def getFileDialogFilter(self):
        """Returns ``str`` standard file open/save filter for ``QFileDialog``"""
        return 'Calibrate (*.xml);;All files (*)'

    def onLoadCalibrateEvent(self):
        fname, filter = QFileDialog.getOpenFileName(self, 'Load the Camera Calibration from file', self.getFileDialogDirectory(), self.getFileDialogFilter())
        if fname != '' and os.path.isfile(fname):
            self.calibrateModel.loadParamsFromXML(fname)
            self.camera_calibrate_filename = fname

    def onGenerateMapEvent(self):
        if self.camera_calibrate_filename and self.camera_calibrate_filename != '':
            self.calibrateModel.setUndistortParams(
                self.calibrateModel.calibrateFlags,
                self.calibrateModel.undistortSize,
                self.calibrateModel.undistortScale,
                self.calibrateModel.undistortOffset
            )
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("XML calibration file is not set.")
            # msg.setInformativeText(str(error))
            msg.setWindowTitle("Mapping table generation failed")
            msg.exec_()

    def onSaveColorEvent(self):
        if self.color_checker_rgb is None: return

        fname, filter = QFileDialog.getSaveFileName(self, 'Save the Reference Color', self.getFileDialogDirectory(), self.getFileDialogFilter())
        if fname != '':
            fs = cv2.FileStorage(fname, cv2.FILE_STORAGE_WRITE)
            fs.write("color_patch_value", self.color_checker_rgb)
            fs.release()

    def onSetColorEvent(self):
        try:
            checker = self.color_checker_detector.getBestColorChecker()
            chartsRGB = checker.getChartsRGB()
            self.color_checker_rgb = chartsRGB[:, 1].copy().reshape(24, 1, 3)
            self.color_checker_rgb /= 255.0
        except Exception as e:
            utils.dumpException(e)

    def readRefColorFromXML(self, filename):
        fs = cv2.FileStorage(filename, cv2.FILE_STORAGE_READ)
        self.color_checker_rgb = fs.getNode("color_patch_value").mat()
        fs.release()
        self.color_correct_filename = filename

    def onLoadColorEvent(self):
        fname, filter = QFileDialog.getOpenFileName(self, 'Load the Reference Color', self.getFileDialogDirectory(), self.getFileDialogFilter())
        if fname != '' and os.path.isfile(fname):
            self.color_correct_filename = fname
            self.readRefColorFromXML(fname)

    def processColorCheckerDetection(self, image:np.ndarray):
        img_draw = image.copy()
        try:
            self.color_checker_detector.process(cv2.cvtColor(image, cv2.COLOR_RGB2BGR), cv2.mcc.MCC24)

            checker = self.color_checker_detector.getBestColorChecker()
            cdraw = cv2.mcc.CCheckerDraw_create(checker)
            cdraw.draw(img_draw)
        except Exception as e:
            utils.dumpException(e)

        return img_draw

    def processColorCorrection(self, image:np.ndarray):
        if self.color_checker_rgb is None: return image

        # print(src.shape)
        # model1 = cv2.ccm_ColorCorrectionModel(src, cv2.mcc.MCC24)
        model1 = cv2.ccm_ColorCorrectionModel(self.color_checker_rgb, cv2.ccm.COLORCHECKER_Macbeth)
        # model1 = cv2.ccm_ColorCorrectionModel(src,src,cv2.ccm.COLOR_SPACE_sRGB)
        model1.run()
        # ccm = model1.getCCM()
        # print("ccm ", ccm)
        # loss = model1.getLoss()
        # print("loss ", loss)

        # rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        rgb_image = image.copy() # RGB format
        rgb_image = rgb_image.astype(np.float64)
        rgb_image = rgb_image / 255
        calibrated_image = model1.infer(rgb_image)
        calibrated_image = calibrated_image * 255
        calibrated_image[calibrated_image < 0] = 0
        calibrated_image[calibrated_image > 255] = 255
        calibrated_image = calibrated_image.astype(np.uint8)

        #res_image = cv2.cvtColor(calibrated_image, cv2.COLOR_RGB2BGR)

        # file, ext = os.path.splitext(image_path)
        # calibratedFilePath = file + '_calibrated' + ext
        # # cv2.imwrite(calibratedFilePath, out_img)
        # cv2.imencode(ext, out_img)[1].tofile(calibratedFilePath)
        # cv2.imshow('out_img', out_img)

        #return res_image
        return calibrated_image

    def processChessboardDetectioin(self, image:np.ndarray):
        detected_image = image.copy()
        res,_ = self.calibrateModel.detectChessboardCorners(detected_image, self.calibrateModel.boardSize, draw_corners=True)
        return detected_image

    def processLensDistortionCorrection(self, image:np.ndarray):
        if self.calibrateModel.xMap is not None and self.calibrateModel.yMap is not None:
            return self.calibrateModel.undistortImage(image)
        return image

if __name__ == "__main__":
    # app = QApplication(sys.argv)
    # win = CalibratePanel()
    # win.show()
    # sys.exit(app.exec_())

    image_path = 'mecbeth_chart.jpeg'

    img = cv2.imdecode(np.fromfile(image_path,dtype=np.uint8),-1)

    # cv2.imshow('img', img)
    # cv2.waitKey(0)

    detector = cv2.mcc.CCheckerDetector_create()

    detector.process(img, cv2.mcc.MCC24)

    # cv2.mcc_CCheckerDetector.getBestColorChecker()
    checker = detector.getBestColorChecker()

    cdraw = cv2.mcc.CCheckerDraw_create(checker)
    img_draw = img.copy()
    cdraw.draw(img_draw)

    cv2.imwrite('detected_image.png', img_draw)

    chartsRGB = checker.getChartsRGB()

    src = chartsRGB[:,1].copy().reshape(24, 1, 3)

    src /= 255.0

    fs = cv2.FileStorage("color_correction.xml", cv2.FILE_STORAGE_WRITE)
    fs.write("color_patch_value", src)
    fs.release()

    print(src.shape)
    # model1 = cv2.ccm_ColorCorrectionModel(src, cv2.mcc.MCC24)
    model1 = cv2.ccm_ColorCorrectionModel(src, cv2.ccm.COLORCHECKER_Macbeth)
    # model1 = cv2.ccm_ColorCorrectionModel(src,src,cv2.ccm.COLOR_SPACE_sRGB)
    model1.run()
    ccm = model1.getCCM()
    print("ccm ", ccm)
    loss = model1.getLoss()
    print("loss ", loss)

    img_ = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_ = img_.astype(np.float64)
    img_ = img_/255
    calibratedImage = model1.infer(img_)
    out_ = calibratedImage * 255
    out_[out_ < 0] = 0
    out_[out_ > 255] = 255
    out_ = out_.astype(np.uint8)

    out_img = cv2.cvtColor(out_, cv2.COLOR_RGB2BGR)

    file, ext = os.path.splitext(image_path)
    calibratedFilePath = file + '_calibrated' + ext
    # cv2.imwrite(calibratedFilePath, out_img)
    cv2.imencode(ext, out_img)[1].tofile(calibratedFilePath)

    # cv2.imshow('out_img', out_img)
    # cv2.waitKey(0)