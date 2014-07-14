#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detection.py
#
# Author: Yann KOETH
# Created: Mon Jul 14 13:51:02 2014 (+0200)
# Last-Updated: Mon Jul 14 22:56:01 2014 (+0200)
#           By: Yann KOETH
#     Update #: 466
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

class VideoThread(QtCore.QThread):
    def __init__(self, mw):
        super(VideoThread, self).__init__(mw)
        self.mw = mw

    def run(self):
        mode = self.mw.getSourceMode()
        if mode == self.mw.SOURCE_VIDEO:
            path = self.mw.sourcePath.text()
            if not path:
                print '[Error] File path is empty'
                return
        elif mode == self.mw.SOURCE_CAMERA:
            path = 0
        print "thread"
        while True:
            if self.mw.stopVideoThread:
                break
            cap = cv2.VideoCapture(path)
            fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)

            while cap.isOpened():
                if self.mw.stopVideoThread:
                    break
                ret, frame = cap.read()
                if frame is None:
                    break
                if mode == self.mw.SOURCE_CAMERA:
                    cv2.flip(frame, 1, frame)
                pixmap = self.mw.np2Qt(frame)
                self.mw.displayImage(pixmap)
                QApplication.processEvents()
                if mode == self.mw.SOURCE_VIDEO:
                    time.sleep(1. / fps)
            print "release"
            cap.release()
            print "out"
        print "end"


class Window(QWidget):

    SOURCE_IMAGE = 'Image'
    SOURCE_VIDEO = 'Video'
    SOURCE_CAMERA = 'Camera'

    D_FACE = 'Face'
    D_EYE = 'Eye'
    D_NOSE = 'Nose'
    D_BANANA = 'Banana'

    __sourceModes = [SOURCE_IMAGE, SOURCE_VIDEO, SOURCE_CAMERA]

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.__availableObjects = [self.D_NOSE]
        # List of tuple (object, [children])
        self.__detectObjects = [(self.D_FACE, [(self.D_EYE, [])]),
                                (self.D_BANANA, [])]

        self.__colors = { self.D_FACE: QColor(0, 255, 0),
                          self.D_EYE: QColor(255, 0, 0),
                          self.D_NOSE: QColor(255, 255, 0),
                          self.D_BANANA: QColor(0, 0, 255)
                          }

        self.initUI()

        self.videoThread = VideoThread(self)
        self.stopVideoThread = False

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

        imageRGB = cv2.cvtColor(imageBGR, cv2.COLOR_BGR2RGB)
        qimg = QImage(imageRGB.data, width, height, bytesPerLine, QImage.Format_RGB888)
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
        pixmap.fill(self.__colors[obj])
        return QIcon(pixmap)

    def displayImage(self, pixmap):
        pixmap = self.fitImageToScreen(pixmap)
        self.mediaLabel.setPixmap(pixmap)
        self.mediaLabel.setFixedSize(pixmap.size())

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
        sourceMode = self.getSourceMode()
        while self.videoThread.isRunning():
            self.stopVideoThread = True
        self.stopVideoThread = False
        if sourceMode == self.SOURCE_IMAGE:
            img = self.readImage(path)
            pixmap = self.np2Qt(img)
            self.displayImage(pixmap)
        elif sourceMode == self.SOURCE_VIDEO or sourceMode == self.SOURCE_CAMERA:
            self.videoThread.start()

    def getSourceMode(self):
        return self.__sourceModes[self.sourceCBox.currentIndex()]

    ########################################################
    # Signals handlers

    def run(self):
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

        self.sourceCBox.setCurrentIndex(0)

        hbox.addWidget(sourceLabel)
        hbox.addWidget(self.sourceCBox)
        hbox.addWidget(self.sourcePath)
        hbox.addWidget(self.sourcePathButton)
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
            for object, children in objects:
                item = QtGui.QStandardItem(object)
                item.setIcon(self.getIcon(object))
                parent.appendRow(item)
                appendTree(children, item)

        appendTree(self.__detectObjects, model)

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
        self.availableObjectsList.addItems(self.__availableObjects)
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
        runButton = QPushButton(self.tr('Run'))
        runButton.clicked.connect(self.run)
        runButton.setMinimumSize(QtCore.QSize(120, 35))
        runButton.setMaximumSize(QtCore.QSize(220, 35))
        vbox = QVBoxLayout()
        vbox.addWidget(detectBox)
        vbox.addWidget(runButton, 0, QtCore.Qt.AlignHCenter)
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
        splitter = QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(leftSide)
        splitter.addWidget(rightSide)
        splitter.splitterMoved.connect(self.splitterMoved)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(sourceWidget)
        mainLayout.addWidget(splitter)
        self.setLayout(mainLayout)
        self.setGeometry(300, 300, 300, 150)
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

