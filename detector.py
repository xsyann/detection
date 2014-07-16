#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detector.py
#
# Author: Yann KOETH
# Created: Tue Jul 15 17:48:25 2014 (+0200)
# Last-Updated: Wed Jul 16 23:04:19 2014 (+0200)
#           By: Yann KOETH
#     Update #: 206
#

import cv2
import time
from tree import Tree, Node

class Detector(object):

    FACE = 'Face'
    EYE = 'Eye'
    FULLBODY = 'Full Body'
    LOWERBODY = 'Lower Body'
    UPPERBODY = 'Upper Body'
    SMILE = 'Smile'
    NOSE = 'Nose'
    LEFTEYE = 'Left eye'
    RIGHTEYE = 'Right eye'
    EYEPAIRBIG = 'Eye pair big'
    EYEPAIRSMALL = 'Eye pair small'
    LEFTEAR = 'Left ear'
    RIGHTEAR = 'Right ear'
    MOUTH = 'Mouth'
    PROFILFACE = 'Profil face'

    __classifiersPaths = { FACE: 'haarcascades/haarcascade_frontalface_alt.xml',
                           EYE: 'haarcascades/haarcascade_eye.xml',
                           FULLBODY: 'haarcascades/haarcascade_fullbody.xml',
                           LOWERBODY: 'haarcascades/haarcascade_lowerbody.xml',
                           UPPERBODY: 'haarcascades/haarcascade_mcs_upperbody.xml',
                           SMILE: 'haarcascades/haarcascade_smile.xml',
                           NOSE: 'haarcascades/haarcascade_mcs_nose.xml',
                           LEFTEYE: 'haarcascades/haarcascade_mcs_lefteye.xml',
                           RIGHTEYE: 'haarcascades/haarcascade_mcs_right.xml',
                           EYEPAIRBIG: 'haarcascades/haarcascade_mcs_eyepair_small.xml',
                           EYEPAIRSMALL: 'haarcascades/haarcascade_mcs_eyepair_big.xml',
                           LEFTEAR: 'haarcascades/haarcascade_mcs_leftear.xml',
                           RIGHTEAR: 'haarcascades/haarcascade_mcs_rightear.xml',
                           MOUTH: 'haarcascades/haarcascade_mcs_mouth.xml',
                           PROFILFACE: 'haarcascades/haarcascade_profileface.xml',
                           }

    @staticmethod
    def getDefaultObjectsTree():
        """List of tuples (object, [children]).
        """
        tree = Tree()
        tree[Detector.FACE][Detector.EYE]
        tree[Detector.FACE][Detector.MOUTH]
        tree[Detector.FACE][Detector.NOSE]
        return tree

    @staticmethod
    def getDefaultAvailableObjects():
        return [Detector.FULLBODY, Detector.LOWERBODY,
                Detector.UPPERBODY, Detector.SMILE, Detector.LEFTEYE,
                Detector.RIGHTEYE, Detector.EYEPAIRBIG, Detector.EYEPAIRSMALL,
                Detector.LEFTEAR, Detector.RIGHTEAR, Detector.PROFILFACE]

    def __init__(self):
        self.colors = { self.FACE: (0, 255, 0),
                        self.EYE: (255, 0, 0),
                        self.FULLBODY: (255, 255, 0),
                        self.LOWERBODY: (0, 0, 255),
                        self.UPPERBODY: (200, 125, 50),
                        self.SMILE: (255, 0, 255),
                        self.NOSE: (50, 125, 200),
                        self.LEFTEYE: (125, 50, 200),
                        self.RIGHTEYE: (50, 200, 125),
                        self.EYEPAIRBIG: (125, 200, 50),
                        self.EYEPAIRSMALL: (230, 200, 150),
                        self.LEFTEAR: (200, 230, 150),
                        self.RIGHTEAR: (0, 172, 230),
                        self.MOUTH: (172, 0, 230),
                        self.PROFILFACE: (230, 57, 0)
                   }

    def preprocess(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.equalizeHist(gray)

    def detect(self, img, tree, scaleFactor=1.3, minNeighbors=4, minSize=(24, 24),
               flags=cv2.cv.CV_HAAR_SCALE_IMAGE):

        def detectTree(tree, parentRoi, roiTree):
            """Recursive function to detect objects in the tree.
            """
            x, y, w, h = parentRoi
            cropped = img[y:y+h, x:x+w]
            for node, children in tree.iteritems():
                objRects = self.detectObject(cropped, node, scaleFactor,
                                             minNeighbors, minSize, flags)
                for roi in objRects:
                    roiNode = Node(node, roi)
                    roiTree[roiNode]
                    detectTree(children, roi, roiTree[roiNode])

        h, w = img.shape[:2]
        roiTree = Tree()
        detectTree(tree, (0, 0, w, h), roiTree)
        return roiTree

    def detectObject(self, img, obj, scaleFactor, minNeighbors, minSize, flags):
        print '{} detecting...'.format(obj),
        start = time.time()
        cascade = cv2.CascadeClassifier(self.__classifiersPaths[obj])
        img = self.preprocess(img)
        rects = cascade.detectMultiScale(img, [], [], scaleFactor=scaleFactor,
                                              minNeighbors=minNeighbors,
                                              minSize=minSize, flags=flags)
        end = time.time()
        print 'in {:.2f} s'.format(end - start)
        return rects
