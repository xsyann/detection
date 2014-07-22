#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detector.py
#
# Author: Yann KOETH
# Created: Tue Jul 15 17:48:25 2014 (+0200)
# Last-Updated: Tue Jul 22 19:10:11 2014 (+0200)
#           By: Yann KOETH
#     Update #: 608
#

import cv2
import numpy as np
import time
from tree import Tree, Node

class ClassifierParameters:
    def __init__(self, hash, classifier, name, color, shape, fill, fillPath="",
                 stabilize=False, tracking=False, showName=True,
                 scaleFactor=1.3, minNeighbors=4, minSize=(0, 0)):
        self.hash = hash
        self.classifier = classifier
        self.shape = shape
        self.name = name
        self.color = color
        self.scaleFactor = scaleFactor
        self.minNeighbors = minNeighbors
        self.minSize = minSize
        self.fill = fill
        self.fillPath = fillPath
        self.stabilize = stabilize
        self.tracking = tracking
        self.showName = showName

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
    DUCK_HAAR = 'Duck Haar'

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
                           DUCK_HAAR: 'classifier/cascade.xml'
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
        self.stored = {}

    def preprocess(self, img, equalizeHist):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return (cv2.equalizeHist(gray) if equalizeHist else gray)

    def dist(self, a, b):
        x1, y1, w1, h1 = a
        x2, y2, w2, h2 = b
        return np.sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2))

    def getNearest(self, rect, rects):
        nearest, dist = None, 0
        for r in rects:
            d = self.dist(r, rect)
            if nearest is None or d < dist:
                nearest, dist = r, d
        return nearest

    def retreiveRect(self, rect, current, previous):
        nearest = self.getNearest(rect, current)
        previous = list(zip(*previous)[0])
        current = list(current)
        near = None
        while previous and nearest:
            near = self.getNearest(nearest, previous)
            if near != rect:
                previous.remove(near)
                current.remove(nearest)
                nearest = self.getNearest(rect, current)
            else:
                return nearest
        return nearest

    def retreiveRects(self, current, previous):
        rects, hashs = [], []
        for i, (previousRect, hash) in enumerate(previous):
            nearestRect = self.retreiveRect(previousRect, current, previous[i:])
            if not nearestRect:
                nearestRect = previousRect
            else:
                del current[current.index(nearestRect)]
            rects.append(nearestRect)
            hashs.append(hash)
        return rects, hashs

    def stabilize(self, param, parentHash, rects):
        key = (param.hash, parentHash)
        hashs = None
        if not param.stabilize and not param.tracking:
            if key in self.stored:
                del self.stored[key]
            return None
        if key in self.stored:
            prevRects = self.stored[key][-1]
            rects, hashs = self.retreiveRects(rects, prevRects)
        else:
            self.stored[key] = []
            hashs = [tuple(rect) for rect in rects]
        if param.tracking:
            self.stored[key].append(zip(rects, hashs))
        else:
            self.stored[key] = [zip(rects, hashs)]
        return self.stored[key]

    def globalizeCoords(self, rects, parent):
        for i, roi in enumerate(rects):
            x, y, w, h = roi
            x1, y1, w1, h1 = parent
            rects[i] = (x + x1, y + y1, w, h)

    def detect(self, img, tree, equalizeHist=True, debugTable=None, autoNeighbors=None,
               autoNeighborsParam=0):

        def detectTree(tree, parentRoi, parentName, parentHash, roiTree):
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
                    rects = self.detectObject(cropped,
                                                 param.classifier,
                                                 param.scaleFactor,
                                                 param.minNeighbors,
                                                 param.minSize,
                                                 cv2.CASCADE_SCALE_IMAGE)
                    if isinstance(rects, np.ndarray):
                        rects = rects.tolist()

                    self.globalizeCoords(rects, parentRoi)

                    hashs = None
                    tracking = None
                    if not autoNeighbors:
                        res = self.stabilize(param, parentHash, rects)
                        if res:
                            rects, hashs = zip(*res[-1]) if res[-1] else ([], [])
                            tracking = res[:-1]

                    if debugTable and not autoNeighbors:
                        end = time.time()
                        col = '{} found in {:.2f} s'.format(len(rects),
                                                        end - start)
                        debugTable([(col, 0)], append=True)

                    if autoNeighbors and node == autoNeighbors and len(rects) > autoNeighborsParam:
                        param.minNeighbors += 1
                    else:
                        incNeighbors = False

                for i, roi in enumerate(rects):
                    hash = hashs[i] if hashs else None
                    roiNode = Node(param.classifier, (roi, param, tracking))
                    roiTree[roiNode]
                    name = parentName + ' > ' + param.name
                    detectTree(children, roi, name, hash, roiTree[roiNode])

        img = self.preprocess(img, equalizeHist)
        self.preprocessed = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        h, w = img.shape[:2]
        roiTree = Tree()
        detectTree(tree, (0, 0, w, h), 'Root', None, roiTree)
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
