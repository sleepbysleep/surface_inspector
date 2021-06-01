import sys
import os
import cv2
import numpy as np

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from toggle_switch import Switch

class TemplatePanel(QWidget):
    def __init__(self, template_filename:str=None, matching:bool=False, parent=None):
        super().__init__(parent)

        self.filename = template_filename
        self.need_matching = matching
        self.template_images = None

        self.initAssets()
        self.initUI()

    def initAssets(self):
        pass

    def initUI(self):
        pass

    def matchTemplates(self, image:np.ndarray, templates:list):
        base_h,base_w = image.shape[:2]

        ### Plain
        hit_scores = np.zeros(len(templates), dtype=np.float32)
        hit_locs = []
        for i,template in enumerate(templates):
            #print(template)
            temp_h,temp_w = template.shape[:2]
            if template is None or temp_h > base_h or temp_w > base_w:
                hit_scores[i] = -1.0
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TemplatePanel()
    win.show()
    sys.exit(app.exec_())

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
    for i, roi in enumerate(self.imageROIs):
        y, yend, x, xend = [roi[1], roi[1] + roi[3], roi[0], roi[0] + roi[2]]
        roi_image = image[y:yend, x:xend, :]
        yuv_image = cv2.cvtColor(roi_image, cv2.COLOR_RGB2YUV)
        bin_image = cv2.inRange(yuv_image, bin_range[0], bin_range[1])

        i, score, loc = self.matchTemplates(bin_image, [item['image'] for item in self.templateFeatures])

        # Eye candies
        template = self.templateFeatures[i]['image']
        temp_h, temp_w = template.shape[:2]
        template_mask = np.zeros(bin_image.shape, dtype=np.uint8)
        template_mask[loc[1]:loc[1] + temp_h, loc[0]:loc[0] + temp_w] = template

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

        # cv2.drawContours(copied, [np.array([[x,y], [xend-1,y], [xend-1,yend-1], [x,yend-1]])], 0, self.roiColors[i], 1)
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
