#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detector.py
#
# Author: Yann KOETH
# Created: Tue Jul 15 17:48:25 2014 (+0200)
# Last-Updated: Tue Jul 15 22:08:06 2014 (+0200)
#           By: Yann KOETH
#     Update #: 146
#

import cv2
import time

class Detector(object):

    FACE = 'Face'
    EYE = 'Eye'
    FULLBODY = 'Full Body'
    LOWERBODY = 'Lower Body'
    SMILE = 'Smile'

    __filepaths = { FACE: 'haarcascades/haarcascade_frontalface_alt.xml',
                    EYE: 'haarcascades/haarcascade_eye.xml',
                    FULLBODY: 'haarcascades/haarcascade_fullbody.xml',
                    LOWERBODY: 'haarcascades/haarcascade_lowerbody.xml',
                    SMILE: 'haarcascades/haarcascade_smile.xml'
                    }

    @staticmethod
    def getDefaultObjectsTree():
        """List of tuples (object, [children]).
        """
        return [(Detector.FACE, [(Detector.EYE, [])]),
                (Detector.SMILE, [])]

    @staticmethod
    def getDefaultAvailableObjects():
        return [Detector.FULLBODY, Detector.LOWERBODY]

    def __init__(self):
        self.colors = { self.FACE: (0, 255, 0),
                   self.EYE: (255, 0, 0),
                   self.FULLBODY: (255, 255, 0),
                   self.LOWERBODY: (0, 0, 255),
                   self.SMILE: (255, 0, 255)
                   }

    def preprocess(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.equalizeHist(gray)

    def detect(self, img, tree, scaleFactor=1.3, minNeighbors=4, minSize=(24, 24),
               flags=cv2.cv.CV_HAAR_SCALE_IMAGE):
        rects = []
        def detectTree(objects, parentRoi, parent):
            """Recursive function to detect objects in the tree.
            """
            x, y, w, h = parentRoi
            for obj, children in objects:
                objRects = self.detectObject(img[y:y+h, x:x+w], obj, scaleFactor,
                                             minNeighbors, minSize, flags)
                parentName = parent if parent else 'Image'
                print '    {} {} detected in {} x {} region of {}'.format(len(objRects),
                                                                  obj, w, h, parentName)
                rects.append((obj, parentRoi, objRects))
                i = 0
                for roi in objRects:
                    detectTree(children, roi, '{}.{}'.format(obj, i + 1))
                    i += 1
        h, w = img.shape[:2]
        detectTree(tree, (0, 0, w, h), None)
        return rects

    def detectObject(self, img, obj, scaleFactor, minNeighbors, minSize, flags):
        print '{} detecting...'.format(obj),
        start = time.time()
        cascade = cv2.CascadeClassifier(self.__filepaths[obj])
        img = self.preprocess(img)
        rects = cascade.detectMultiScale(img, [], [], scaleFactor=scaleFactor,
                                              minNeighbors=minNeighbors,
                                              minSize=minSize, flags=flags)
        end = time.time()
        print 'in {:.2f} s'.format(end - start)
        return rects
