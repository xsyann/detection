#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detection.py
#
# Author: Yann KOETH
# Created: Mon Jul 14 13:51:02 2014 (+0200)
# Last-Updated: Tue Jul 15 21:46:32 2014 (+0200)
#           By: Yann KOETH
#     Update #: 942
#

import sys
import os
import cv2
import time
import urllib2
import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QApplication, QWidget, QFileDialog, QPushButton,
                             QHBoxLayout, QVBoxLayout, QDesktopWidget,
                             QLabel, QLineEdit, QListWidget, QComboBox, QScrollArea,
                             QSplitter, QGroupBox, QTextEdit, QAbstractItemView,
                             QFrame, QSizePolicy, QSlider, QTreeView)
from PyQt5.QtGui import QImage, QPixmap, QColor, QIcon

import detector

class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

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
                print "[Error] Couldn't read movie file {}".format(path)
                break
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
                print '[Error] File path is empty'
                return
        elif mode == self.mw.SOURCE_CAMERA:
            path = 0

        self.main(mode, path)


class Window(QWidget):

    SOURCE_IMAGE = 'Image'
    SOURCE_VIDEO = 'Video'
    SOURCE_CAMERA = 'Camera'

    __sourceModes = [SOURCE_IMAGE, SOURCE_VIDEO, SOURCE_CAMERA]

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.detector = detector.Detector()

        self.initUI()

        sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)
        self.videoThread = VideoThread(self)

    def __del__(self):
        sys.stdout = sys.__stdout__

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()

    ########################################################
    # Utils

    def np2Qt(self, imageBGR):
        """Convert numpy array to QPixmap.
        """
        height, width = imageBGR.shape[:2]
        bytesPerLine = 3 * width

        qimg = QImage(imageBGR.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        return QPixmap.fromImage(qimg)

    def fitImageToScreen(self, pixmap):
        """Fit pixmap to screen.
        """
        resolution = QDesktopWidget().screenGeometry()
        h, w = resolution.width(), resolution.height()
        w = min(pixmap.width(), w)
        h = min(pixmap.height(), h)
        return pixmap.scaled(QtCore.QSize(w, h), QtCore.Qt.KeepAspectRatio)

    def getIcon(self, obj):
        """Returns a colored icon for 'obj'.
        """
        pixmap = QPixmap(14, 14)
        r, g, b = self.detector.colors[obj]
        pixmap.fill(QColor(r, g, b))
        return QIcon(pixmap)

    def scaleRect(self, rect, scale):
        x, y, w, h = rect
        return (x * scale, y * scale, w * scale, h * scale)

    def drawRects(self, pixmap, rects, scale):
        if rects is None:
            return
        painter = QtGui.QPainter(pixmap)
        for obj, roi, objRects in rects:
            for (x, y, w, h) in objRects:
                x, y, w, h = self.scaleRect((x, y, w, h), scale)
                cx, cy, cw, ch = self.scaleRect(roi, scale)
                r, g, b = self.detector.colors[obj]
                painter.setPen(QColor(r, g, b))
                painter.drawRect(x + cx, y + cy, w, h)

    def displayImage(self, img):
        """Display numpy 'img' in 'mediaLabel'.
        """
        rects = self.detector.detect(img, self.getObjectsTree())
        pixmap = self.np2Qt(img)
        w = float(pixmap.width())
        pixmap = self.fitImageToScreen(pixmap)
        scaleFactor = pixmap.width() / w
        self.drawRects(pixmap, rects, scaleFactor)
        self.mediaLabel.setPixmap(pixmap)
        self.mediaLabel.setFixedSize(pixmap.size())

    def getObjectsTree(self):
        """Create an object tree representation from QTreeView.
        """
        def addChildren(obj):
            """Recursive function to create tree.
            """
            objs = []
            childCount = obj.rowCount()
            if childCount == 0:
                return ((obj.text(), []))
            for i in xrange(childCount):
                child = obj.child(i)
                objs.append(addChildren(child))
            return (obj.text(), objs)
        tree = []
        for i in xrange(self.objectsTree.model().rowCount()):
            rootIndex = self.objectsTree.model().index(i, 0)
            rootItem = self.objectsTree.model().itemFromIndex(rootIndex)
            tree.append(addChildren(rootItem))
        return tree


    def readImage(self, path):
        """Load image from path.
        Raises OSError exception if path doesn't exist or is not an image.
        """
        img = None
        if not os.path.isfile(path):
            try:
                req = urllib2.urlopen(path)
                arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.CV_LOAD_IMAGE_COLOR)
            except ValueError:
                raise OSError(2, 'File not found', path)
        else:
            img = cv2.imread(path)
        if img is None:
            raise OSError(2, 'File not recognized', path)
        return img

    def displayMedia(self, path):
        """Load and display media.
        """
        sourceMode = self.getSourceMode()
        if self.videoThread.isRunning():
            self.videoThread.stop()
        self.videoThread.clean()
        if sourceMode == self.SOURCE_IMAGE:
            try:
                img = self.readImage(path)
            except (OSError, urllib2.HTTPError) as err:
                print err
                return
            self.displayImage(img)
        elif sourceMode == self.SOURCE_VIDEO or sourceMode == self.SOURCE_CAMERA:
            self.videoThread.start()

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

    ########################################################
    # Widgets

    def widgetSource(self):
        """Create source widget.
        """
        hbox = QHBoxLayout()
        sourceLabel = QLabel(self.tr('Source'))

        self.sourceCBox = QComboBox(self)
        for sourceMode in self.__sourceModes:
            self.sourceCBox.addItem(sourceMode)
        self.sourceCBox.currentIndexChanged.connect(self.togglePath)

        self.sourcePath = QLineEdit(self)

        self.sourcePathButton = QPushButton('...')
        self.sourcePathButton.clicked.connect(self.loadMedia)

        refreshButton = QPushButton('')
        refreshButton.setIcon(QIcon('assets/refresh.png'))
        refreshButton.setIconSize(QtCore.QSize(20, 20))
        refreshButton.setMinimumSize(QtCore.QSize(20, 20))
        refreshButton.setMaximumSize(QtCore.QSize(20, 20))
        refreshButton.setStyleSheet("QPushButton { border: none; }"
                                "QPushButton:pressed { border: 1px solid gray; background-color: #aaa; }")
        refreshButton.clicked.connect(self.refresh)

        self.sourceCBox.setCurrentIndex(0)

        hbox.addWidget(sourceLabel)
        hbox.addWidget(self.sourceCBox)
        hbox.addWidget(self.sourcePath)
        hbox.addWidget(self.sourcePathButton)
        hbox.addWidget(refreshButton)
        hbox.setAlignment(QtCore.Qt.AlignLeft)
        return hbox

    def widgetFrame(self):
        """Create main display widget.
        """
        vbox = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setAlignment(QtCore.Qt.AlignCenter)
        self.mediaLabel = QLabel(self)
        scroll.setWidget(self.mediaLabel)
        vbox.addWidget(scroll)
        return vbox

    def widgetTree(self):
        """Create selected objects tree.
        """
        model = QtGui.QStandardItemModel(self)

        def appendTree(objects, parent):
            """Recursive function to populate the tree.
            """
            for obj, children in objects:
                item = QtGui.QStandardItem(obj)
                item.setIcon(self.getIcon(obj))
                parent.appendRow(item)
                appendTree(children, item)

        appendTree(detector.Detector.getDefaultObjectsTree(), model)

        tree = QTreeView()
        tree.setModel(model)
        tree.header().setHidden(True)
        tree.setDragEnabled(True)
        tree.setDefaultDropAction(QtCore.Qt.MoveAction)
        tree.setDragDropMode(QAbstractItemView.InternalMove)
        tree.setAcceptDrops(True)
        tree.setDropIndicatorShown(True)
        return tree

    def widgetObjectList(self):
        """Create objects list widget.
        """
        self.objectsTree = self.widgetTree()
        self.availableObjectsList = QListWidget(self)
        self.availableObjectsList.addItems(detector.Detector.getDefaultAvailableObjects())
        removeButton = QPushButton(self.tr('>>'))
        removeButton.clicked.connect(self.removeObject)
        addButton = QPushButton(self.tr('<<'))
        addButton.clicked.connect(self.addObject)
        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addWidget(addButton)
        vbox.addWidget(removeButton)
        vbox.addStretch(1)

        vboxSelected = QVBoxLayout()
        selectedLabel = QLabel(self.tr('Selected'))
        selectedLabel.setAlignment(QtCore.Qt.AlignCenter)
        vboxSelected.addWidget(selectedLabel)
        vboxSelected.addWidget(self.objectsTree)
        vboxAvailable = QVBoxLayout()
        availableLabel = QLabel(self.tr('Available'))
        availableLabel.setAlignment(QtCore.Qt.AlignCenter)
        vboxAvailable.addWidget(availableLabel)
        vboxAvailable.addWidget(self.availableObjectsList)
        hbox = QHBoxLayout()
        hbox.addLayout(vboxSelected)
        hbox.addLayout(vbox)
        hbox.addLayout(vboxAvailable)
        return hbox

    def widgetParameters(self):
        """Create parameters widget.
        """
        detectBox = QGroupBox(self.tr('Detect'))
        objects = self.widgetObjectList()
        detectBox.setLayout(objects)
        vbox = QVBoxLayout()
        vbox.addWidget(detectBox)
        return vbox

    def widgetDebug(self):
        """Create debug infos widget.
        """
        self.debugText = QTextEdit(self)
        css = "QTextEdit { background-color: #FFF; color: #222; }"
        self.debugText.setStyleSheet(css)
        vbox = QVBoxLayout()
        hbox = QHBoxLayout()
        self.showDetails = QPushButton(self.tr('Details >>>'))
        self.showDetails.setCheckable(True)
        self.showDetails.clicked[bool].connect(self.toggleDebugInfo)
        self.showDetails.setChecked(1)
        hbox.addWidget(self.showDetails)
        hbox.addStretch(1)
        self.toggleDebugInfo(True)

        vbox.addLayout(hbox)
        vbox.addWidget(self.debugText)
        vbox.addStretch(1)

        return vbox

    def initUI(self):
        """Create User Interface.
        """
        sourceWidget = self.widgetSource()
        frameWidget = self.widgetFrame()
        parametersWidget = self.widgetParameters()

        leftSide = QWidget()
        leftSide.setLayout(parametersWidget)
        rightSide = QWidget()
        rightSide.setLayout(frameWidget)
        hsplitter = QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(leftSide)
        hsplitter.addWidget(rightSide)
        hsplitter.splitterMoved.connect(self.splitterMoved)
        hsplitter.setStretchFactor(0, 1)
        hsplitter.setStretchFactor(1, 10)

        downSide = QWidget()
        downSide.setLayout(self.widgetDebug())
        vsplitter = QSplitter(QtCore.Qt.Vertical)
        vsplitter.addWidget(hsplitter)
        vsplitter.addWidget(downSide)
        vsplitter.splitterMoved.connect(self.splitterMoved)
        vsplitter.setStretchFactor(0, 10)
        vsplitter.setStretchFactor(1, 1)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(sourceWidget)
        mainLayout.addWidget(vsplitter)
        self.setLayout(mainLayout)
        self.setGeometry(300, 300, 800, 600)
        self.show()


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

