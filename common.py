#!/usr/bin/env python
# -*- coding: utf-8 -*-
# common.py
#
# Author: Yann KOETH
# Created: Wed Jul 16 19:11:21 2014 (+0200)
# Last-Updated: Wed Jul 16 22:31:09 2014 (+0200)
#           By: Yann KOETH
#     Update #: 26
#

import cv2
import os
import urllib2
import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QDesktopWidget

from tree import Tree

class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

def np2Qt(imageBGR):
    """Convert numpy array to QPixmap.
    """
    height, width = imageBGR.shape[:2]
    bytesPerLine = 3 * width

    qimg = QImage(imageBGR.data, width, height,
                  bytesPerLine, QImage.Format_RGB888).rgbSwapped()
    return QPixmap.fromImage(qimg)

def fitImageToScreen(pixmap):
    """Fit pixmap to screen.
    """
    resolution = QDesktopWidget().screenGeometry()
    h, w = resolution.width(), resolution.height()
    w = min(pixmap.width(), w)
    h = min(pixmap.height(), h)
    return pixmap.scaled(QtCore.QSize(w, h), QtCore.Qt.KeepAspectRatio)

def scaleRect(rect, scale):
    """Scale 'rect' with a factor of 'scale'.
    """
    x, y, w, h = rect
    return (x * scale, y * scale, w * scale, h * scale)


def getObjectsTree(qTreeView):
    """Create an object tree representation from QTreeView.
    """
    tree = Tree()
    model = qTreeView.model()
    tree.fromQStandardItemModel(model)
    return tree

def readImage(path):
    """Load image from path.
    Raises exception if path doesn't exist or is not an image.
    """
    img = None
    if not path:
        raise Exception, 'File path is empty '

    if not os.path.isfile(path):
        try:
            req = urllib2.urlopen(path)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.CV_LOAD_IMAGE_COLOR)
        except ValueError:
            raise Exception, 'File not found ' + path
        except urllib2.HTTPError as err:
            raise Exception, err
    else:
        img = cv2.imread(path)
        if img is None:
            raise Exception, 'File not recognized ' + path
    return img
