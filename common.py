#!/usr/bin/env python
# -*- coding: utf-8 -*-
# common.py
#
# Author: Yann KOETH
# Created: Wed Jul 16 19:11:21 2014 (+0200)
# Last-Updated: Tue Jul 22 13:32:59 2014 (+0200)
#           By: Yann KOETH
#     Update #: 108
#

import cv2
import os
import urllib2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QDesktopWidget, QLabel, QGraphicsBlurEffect, QGraphicsPixmapItem

from tree import Tree

class CustomException(Exception):
    pass

class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

def setPickerColor(color, colorPicker):
    """Set the color picker color.
    """
    css = 'QWidget { background-color: %s; border-width: 1px; \
        border-radius: 2px; border-color: #555; border-style: outset; }'
    colorPicker.setStyleSheet(css % color.name())

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

def blurPixmap(pixmap, radius):
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius)
    buffer = QPixmap(pixmap)
    item = QGraphicsPixmapItem(buffer)
    item.setGraphicsEffect(effect)
    output = QPixmap(pixmap.width(), pixmap.height())
    painter = QtGui.QPainter(output)
    scene = QtWidgets.QGraphicsScene()
    view = QtWidgets.QGraphicsView(scene)
    scene.addItem(item)
    scene.render(painter)
    return output

def scaleRect(rect, scale):
    """Scale 'rect' with a factor of 'scale'.
    """
    x, y, w, h = rect
    return (x * scale, y * scale, w * scale, h * scale)

def getObjectsTree(qTreeView, table, extract):
    """Create an object tree representation from QTreeView.
    """
    tree = Tree()
    model = qTreeView.model()
    extracted = tree.fromQStandardItemModel(model, table, extract)
    return tree, extracted

def readImage(path):
    """Load image from path.
    Raises exception if path doesn't exist or is not an image.
    """
    img = None
    if not path:
        raise CustomException, 'File path is empty '

    if not os.path.isfile(path):
        try:
            req = urllib2.urlopen(path)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except ValueError:
            raise CustomException, 'File not found ' + path
        except urllib2.HTTPError as err:
            raise CustomException, err
    else:
        img = cv2.imread(path)
        if img is None:
            raise CustomException, 'File not recognized ' + path
    return img
