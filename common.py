#!/usr/bin/env python
# -*- coding: utf-8 -*-
# common.py
#
# Author: Yann KOETH
# Created: Wed Jul 16 19:11:21 2014 (+0200)
# Last-Updated: Tue Jul 22 15:01:01 2014 (+0200)
#           By: Yann KOETH
#     Update #: 110
#

import cv2
import os
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
