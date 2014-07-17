#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detection.py
#
# Author: Yann KOETH
# Created: Mon Jul 14 13:51:02 2014 (+0200)
# Last-Updated: Thu Jul 17 17:03:14 2014 (+0200)
#           By: Yann KOETH
#     Update #: 1364
#

import sys
import os
import cv2
import time
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (QApplication, QWidget, QFileDialog, QPushButton,
                             QHBoxLayout, QVBoxLayout, QScrollArea, QColorDialog,
                             QLabel, QLineEdit, QListWidget, QComboBox,
                             QSplitter, QGroupBox, QTextEdit, QAbstractItemView,
                             QFrame, QSizePolicy, QSlider)
from PyQt5.QtGui import QImage, QPixmap, QColor, QIcon

from window_ui import WindowUI
import detector
from detector import Detector
import common
from tree import Tree

class VideoThread(QtCore.QThread):
    def __init__(self, mw):
        super(VideoThread, self).__init__(mw)
        self.mw = mw
        self.stopped = False
        self.capture = None
        self.mutex = QtCore.QMutex()

    def stop(self):
        """Stop video thread.
        """
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True

    def clean(self):
        """Clean video thread.
        """
        self.wait()
        del self.capture
        self.capture = None

    def main(self, mode, path):
        """Main loop.
        """
        while True:
            if self.stopped:
                break
            self.capture = cv2.VideoCapture(path)
            fps = self.capture.get(cv2.cv.CV_CAP_PROP_FPS)

            if not self.capture.isOpened():
                raise Exception, "Couldn't read movie file " + path
            while self.capture.isOpened():
                if self.stopped:
                    break
                ret, frame = self.capture.read()
                if frame is None:
                    self.stop()
                    break
                if mode == self.mw.SOURCE_CAMERA:
                    cv2.flip(frame, 1, frame)

                self.mw.displayImage(frame)
                QApplication.processEvents()

    def run(self):
        """Method Override.
        """
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = False

        mode = self.mw.getSourceMode()
        if mode == self.mw.SOURCE_VIDEO:
            path = self.mw.sourcePath.text()
            if not path:
                raise Exception, 'File path is empty'
        elif mode == self.mw.SOURCE_CAMERA:
            path = 0

        self.main(mode, path)

class Window(QWidget, WindowUI):

    SOURCE_IMAGE = 'Image'
    SOURCE_VIDEO = 'Video'
    SOURCE_CAMERA = 'Camera'

    __sourceModes = [SOURCE_IMAGE, SOURCE_VIDEO, SOURCE_CAMERA]

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.detector = Detector()
        self.videoThread = VideoThread(self)
        sys.stdout = common.EmittingStream(textWritten=self.normalOutputWritten)

        self.classifiersParameters = {}

        self.setupUI()
        self.populateUI()
        self.connectUI()
        self.initUI()

    def __del__(self):
        sys.stdout = sys.__stdout__

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()

    def populateUI(self):
        self.availableObjectsList.addItems(Detector.getDefaultAvailableObjects())
        for sourceMode in self.__sourceModes:
            self.sourceCBox.addItem(sourceMode)

        model = QtGui.QStandardItemModel(self)
        func = lambda node, parent: self.populateTree(node, parent)
        Detector.getDefaultObjectsTree().map(model, func)
        self.objectsTree.setModel(model)

    def connectUI(self):
        self.hsplitter.splitterMoved.connect(self.splitterMoved)
        self.vsplitter.splitterMoved.connect(self.splitterMoved)
        self.showDetails.clicked[bool].connect(self.toggleDebugInfo)
        self.addButton.clicked.connect(self.addObject)
        self.removeButton.clicked.connect(self.removeObject)
        self.sourceCBox.currentIndexChanged.connect(self.togglePath)
        self.sourcePathButton.clicked.connect(self.loadMedia)
        self.refreshButton.clicked.connect(self.refresh)
        self.objectsTree.customSelectionChanged.connect(self.showClassifierParameters)
        self.colorPicker.clicked.connect(self.colorDialog)
        self.classifierName.textChanged.connect(self.updateClassifierParameters)

    def initUI(self):
        self.showClassifierParameters(None, None)

    ########################################################
    # Utils

    def getIcon(self, color):
        """Returns a colored icon.
        """
        pixmap = QPixmap(14, 14)
        pixmap.fill(color)
        return QIcon(pixmap)

    def populateTree(self, node, parent):
        item = QtGui.QStandardItem(node)
        item.setData(hash(item))
        h, s, v = Detector.getDefaultHSVColor(node)
        color = QColor()
        color.setHsvF(h, s, v)
        item.setIcon(self.getIcon(color))
        self.classifiersParameters[item.data()] = (node, node, color)
        parent.appendRow(item)
        return item

    def drawRects(self, pixmap, rectsTree, scale):
        """Draw rectangles in 'rectsTree' on 'pixmap'.
        """
        painter = QtGui.QPainter(pixmap)

        def drawRect(node, parentRoi):
            roi, name, color = node.data
            x, y, w, h = common.scaleRect(roi, scale)
            cx, cy, cw, ch = parentRoi
            painter.setPen(color)
            painter.drawText(x + cx, y + cy, name)
            painter.drawRect(x + cx, y + cy, w, h)
            return (x, y, w, h)

        h, w = pixmap.height(), pixmap.width()
        rectsTree.map((0, 0, w, h), drawRect)

    def displayImage(self, img):
        """Display numpy 'img' in 'mediaLabel'.
        """
        # Detect on full size image
        table = { k: param for (k, param) in self.classifiersParameters.iteritems() }
        table = self.classifiersParameters
        tree = common.getObjectsTree(self.objectsTree, table)
        rectsTree = self.detector.detect(img, tree)

        pixmap = common.np2Qt(img)
        w = float(pixmap.width())
        # Scale image
        pixmap = common.fitImageToScreen(pixmap)
        scaleFactor = pixmap.width() / w
        # Draw scaled rectangles
        self.drawRects(pixmap, rectsTree, scaleFactor)
        self.mediaLabel.setPixmap(pixmap)
        self.mediaLabel.setFixedSize(pixmap.size())

    def displayMedia(self, path):
        """Load and display media.
        """
        sourceMode = self.getSourceMode()
        if self.videoThread.isRunning():
            self.videoThread.stop()
        self.videoThread.clean()
        try:
            if sourceMode == self.SOURCE_IMAGE:
                img = common.readImage(path)
                self.displayImage(img)
            elif sourceMode == self.SOURCE_VIDEO or sourceMode == self.SOURCE_CAMERA:
                self.videoThread.start()
        except Exception as err:
            print '[Error]', err

    def getSourceMode(self):
        """Return the current source mode.
        """
        return self.__sourceModes[self.sourceCBox.currentIndex()]

    def updateClassifierParameters(self, name=None, color=None):
        index = self.objectsTree.currentIndex()
        item = index.model().itemFromIndex(index)
        base, oldName, oldColor = self.classifiersParameters[item.data()]
        if name:
            item.setText(name)
            self.classifiersParameters[item.data()] = (base, name, oldColor)
        if color:
            item.setIcon(self.getIcon(color))
            self.classifiersParameters[item.data()] = (base, oldName, color)

    ########################################################
    # Signals handlers

    def normalOutputWritten(self, text):
        """Append text to debug infos.
        """
        cursor = self.debugText.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.debugText.setTextCursor(cursor)
        QApplication.processEvents()

    def refresh(self):
        """Refresh with current media.
        """
        self.displayMedia(self.sourcePath.text())

    def loadMedia(self):
        """Load image or video.
        """
        filters = ""
        sourceMode = self.getSourceMode()
        if sourceMode == self.SOURCE_IMAGE:
            filters = self.tr('Image (*.jpg *.png *.jpeg *.bmp)')
        if sourceMode == self.SOURCE_VIDEO:
            filters = self.tr('Video (*.avi *.mp4 *.mov)')
        path, filters = QFileDialog.getOpenFileName(self, self.tr('Open file'), '.',
                                                    filters)
        if path:
            self.sourcePath.setText(path)
            self.displayMedia(path)

    def togglePath(self, index):
        """Hide path for camera mode.
        """
        if self.__sourceModes[index] == self.SOURCE_CAMERA:
            self.sourcePath.hide()
            self.sourcePathButton.hide()
            self.displayMedia(self.sourcePath.text())
        else:
            self.sourcePath.show()
            self.sourcePathButton.show()

    def colorDialog(self):
        """Open color dialog to pick a color.
        """
        color = QColorDialog.getColor()

        if color.isValid():
            self.backgroundColor = color
            common.setPickerColor(color, self.colorPicker)
            self.updateClassifierParameters(color=color)

    def showClassifierParameters(self, selected, deselected):
        """Show the selected classifier parameters.
        """
        selectedCount = len(self.objectsTree.selectedIndexes())
        if selectedCount == 1:
            self.parametersBox.setEnabled(True)
            index = self.objectsTree.currentIndex()
            item = index.model().itemFromIndex(index)
            base, name, color = self.classifiersParameters[item.data()]
            self.classifierName.setText(name)
            common.setPickerColor(color, self.colorPicker)
            self.classifierType.setText('(' + base + ')')
        else:
            self.parametersBox.setEnabled(False)

    def addObject(self):
        """Add object to detect.
        """
        selected = self.availableObjectsList.selectedItems()
        for item in selected:
            row = (self.availableObjectsList.row(item) + 1) % self.availableObjectsList.count()
            self.availableObjectsList.setCurrentRow(row)
            node = item.text()
            self.populateTree(node, self.objectsTree.model())

    def removeObject(self):
        """Remove object to detect.
        """
        selected = self.objectsTree.selectedIndexes()
        while selected and selected[0].model():
            index = selected[0]
            item = index.model().itemFromIndex(index)
            del self.classifiersParameters[item.data()]
            if item.parent():
                index.model().removeRow(item.row(), item.parent().index())
            else:
                index.model().removeRow(item.row())
            selected = self.objectsTree.selectedIndexes()

    def splitterMoved(self, pos, index):
        """Avoid segfault when QListWidget has focus and
        is going to be collapsed.
        """
        focusedWidget = QApplication.focusWidget()
        if focusedWidget:
            focusedWidget.clearFocus()

    def toggleDebugInfo(self, pressed):
        """Toggle debug infos widget.
        """
        if pressed:
            self.debugText.show()
            self.showDetails.setText(self.tr('Details <<<'))
        else:
            self.debugText.hide()
            self.showDetails.setText(self.tr('Details >>>'))


def main():

    app = QApplication(sys.argv)
    main = Window()
    main.setWindowTitle('Detection')
    main.show()
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

