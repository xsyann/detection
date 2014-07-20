#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detector.py
#
# Author: Yann KOETH
# Created: Tue Jul 15 17:48:25 2014 (+0200)
# Last-Updated: Sun Jul 20 20:55:00 2014 (+0200)
#           By: Yann KOETH
#     Update #: 378
#

import cv2
import numpy as np
import time
from tree import Tree, Node

class ClassifierParameters:
    def __init__(self, classifier, name, color, shape, blur=False,
                 scaleFactor=1.3, minNeighbors=4, minSize=(0, 0)):
        self.classifier = classifier
        self.shape = shape
        self.name = name
        self.color = color
        self.scaleFactor = scaleFactor
        self.minNeighbors = minNeighbors
        self.minSize = minSize
        self.blur = blur

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
    DUCKSMALL_LBP = 'Duck small LBP'
    DUCKBIG_LBP = 'Duck big LBP'

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
                           DUCKSMALL_LBP: 'haarcascades/duck_25x24.xml',
                           DUCKBIG_LBP: 'haarcascades/duck_50x48.xml',
                           }

    @staticmethod
    def getDefaultObjectsTree():
        """List of tuples (object, [children]).
        """
        tree = Tree()
        tree[Detector.FACE][Detector.EYE]
        tree[Detector.FACE][Detector.NOSE]
        return tree

    @staticmethod
    def getDefaultAvailableObjects():
        return Detector.__classifiersPaths.keys()

    @staticmethod
    def getDefaultHSVColor(classifier):
        classifiers = Detector.__classifiersPaths.keys()
        return (classifiers.index(classifier) / float(len(classifiers)), 1, 1)

    def __init__(self):
        self.preprocessed = None

    def preprocess(self, img, equalizeHist):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return (cv2.equalizeHist(gray) if equalizeHist else gray)

    def detect(self, img, tree, equalizeHist=True, debugTable=None, autoNeighbors=None):

        def detectTree(tree, parentRoi, parentName, roiTree):
            """Recursive function to detect objects in the tree.
            """
            x, y, w, h = parentRoi
            cropped = img[y:y+h, x:x+w]
            for node, children in tree.iteritems():
                param = node.data
                incNeighbors = True
                while incNeighbors:
                    if debugTable and not autoNeighbors:
                        col1 = '{} ({})'.format(param.classifier, param.name)
                        col2 = 'detecting in {}x{} ({})...'.format(w, h, parentName)
                        debugTable([(col1, 200), (col2, 300), ('', 200)])
                        start = time.time()
                    objRects = self.detectObject(cropped,
                                                 param.classifier,
                                                 param.scaleFactor,
                                                 param.minNeighbors,
                                                 param.minSize,
                                                 cv2.CASCADE_SCALE_IMAGE)

                    if debugTable and not autoNeighbors:
                        end = time.time()
                        col = '{} found in {:.2f} s'.format(len(objRects),
                                                        end - start)
                        debugTable([(col, 0)], append=True)

                    if autoNeighbors and node == autoNeighbors and isinstance(objRects, np.ndarray) and objRects.any():
                        param.minNeighbors += 1
                    else:
                        incNeighbors = False

                for roi in objRects:
                    roiNode = Node(param.classifier, (roi, param))
                    roiTree[roiNode]
                    name = parentName + ' > ' + param.name
                    detectTree(children, roi, name, roiTree[roiNode])

        img = self.preprocess(img, equalizeHist)
        self.preprocessed = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        h, w = img.shape[:2]
        roiTree = Tree()
        detectTree(tree, (0, 0, w, h), 'Root', roiTree)
        return roiTree

    def detectObject(self, img, obj, scaleFactor, minNeighbors, minSize, flags):
        cascade = cv2.CascadeClassifier(self.__classifiersPaths[obj])
        if cascade.empty():
            print "Classifier error for {}".format(obj)
            return []
        rects = cascade.detectMultiScale(img, scaleFactor=scaleFactor,
                                              minNeighbors=minNeighbors,
                                              flags=flags, minSize=minSize)
        return rects
