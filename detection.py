#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detection.py
#
# Author: Yann KOETH
# Created: Mon Jul 14 13:51:02 2014 (+0200)
# Last-Updated: Wed Jul 16 23:00:05 2014 (+0200)
#           By: Yann KOETH
#     Update #: 1056
#

import sys
import os
import cv2
import time
import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QApplication, QWidget, QFileDialog, QPushButton,
                             QHBoxLayout, QVBoxLayout, QScrollArea,
                             QLabel, QLineEdit, QListWidget, QComboBox,
                             QSplitter, QGroupBox, QTextEdit, QAbstractItemView,
                             QFrame, QSizePolicy, QSlider, QTreeView)
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

        self.setupUI()
        self.populateUI()
        self.connectUI()

        sys.stdout = common.EmittingStream(textWritten=self.normalOutputWritten)
        self.videoThread = VideoThread(self)

    def __del__(self):
        sys.stdout = sys.__stdout__

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()

    def populateUI(self):
        self.availableObjectsList.addItems(Detector.getDefaultAvailableObjects())
        for sourceMode in self.__sourceModes:
            self.sourceCBox.addItem(sourceMode)

        def populateTree(node, parent):
            item = QtGui.QStandardItem(node)
            item.setIcon(self.getIcon(node))
            parent.appendRow(item)
            return item

        model = QtGui.QStandardItemModel(self)
        Detector.getDefaultObjectsTree().map(model, populateTree)
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

    ########################################################
    # Utils

    def getIcon(self, obj):
        """Returns a colored icon for 'obj'.
        """
        pixmap = QPixmap(14, 14)
        r, g, b = self.detector.colors[obj]
        pixmap.fill(QColor(r, g, b))
        return QIcon(pixmap)

    def drawRects(self, pixmap, rectsTree, scale):
        """Draw rectangles in 'rectsTree' on 'pixmap'.
        """
        painter = QtGui.QPainter(pixmap)

        def drawRect(node, parentRoi):
            x, y, w, h = common.scaleRect(node.data, scale)
            cx, cy, cw, ch = parentRoi
            x += cx
            y += cy
            cx, cy = x, y
            cx, cy, cw, ch = common.scaleRect((cx, cy, cw, ch), scale)
            print node.name, x, cx
            r, g, b = self.detector.colors[node.name]
            painter.setPen(QColor(r, g, b))
            painter.drawRect(x, y, w, h)
            return (x, y, w, h)

        h, w = pixmap.height(), pixmap.width()
        rectsTree.map((0, 0, w, h), drawRect)

    def displayImage(self, img):
        """Display numpy 'img' in 'mediaLabel'.
        """
        # Detect on full size image
        rectsTree = self.detector.detect(img,
                                         common.getObjectsTree(self.objectsTree))
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

    def addObject(self):
        """Add object to detect.
        """
        selected = self.availableObjectsList.selectedItems()
        for item in selected:
            self.availableObjectsList.takeItem(self.availableObjectsList.row(item))
            obj = QtGui.QStandardItem(item.text())
            obj.setIcon(self.getIcon(item.text()))
            self.objectsTree.model().appendRow(obj)

    def removeObject(self):
        """Remove object to detect.
        """
        index = self.objectsTree.currentIndex()
        if index.model():
            item = index.model().itemFromIndex(index)

            def transferChildren(obj):
                """Recursive function to remove children.
                """
                self.availableObjectsList.addItem(obj.text())
                childCount = obj.rowCount()
                for i in xrange(childCount):
                    child = obj.child(i)
                    transferChildren(child)
            transferChildren(item)

            if item.parent():
                index.model().removeRow(item.row(), item.parent().index())
            else:
                index.model().removeRow(item.row())

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

