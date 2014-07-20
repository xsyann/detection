#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detection.py
#
# Author: Yann KOETH
# Created: Mon Jul 14 13:51:02 2014 (+0200)
# Last-Updated: Sun Jul 20 21:44:36 2014 (+0200)
#           By: Yann KOETH
#     Update #: 1642
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
from detector import Detector, ClassifierParameters
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

            if not self.capture.isOpened():
                print "Couldn't read movie file " + path
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
                print 'File path is empty'
                return
        elif mode == self.mw.SOURCE_CAMERA:
            path = 0

        self.main(mode, path)

class Window(QWidget, WindowUI):

    SOURCE_IMAGE = 'Image'
    SOURCE_VIDEO = 'Video'
    SOURCE_CAMERA = 'Camera'

    DISPLAY_INPUT = 'Input'
    DISPLAY_PREPROCESSED = 'Pre-processed'

    SHAPE_RECT = 'Rectangle'
    SHAPE_ELLIPSE = 'Ellipse'

    __sourceModes = [SOURCE_IMAGE, SOURCE_VIDEO, SOURCE_CAMERA]
    __displayModes = [DISPLAY_INPUT, DISPLAY_PREPROCESSED]
    __shapeModes = [SHAPE_RECT, SHAPE_ELLIPSE]

    debugSignal = QtCore.pyqtSignal(object, int)

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.detector = Detector()
        self.videoThread = VideoThread(self)
        sys.stdout = common.EmittingStream(textWritten=self.normalOutputWritten)
        self.debugSignal.connect(self.debugTable)
        self.currentFrame = None

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
        for displayMode in self.__displayModes:
            self.displayCBox.addItem(displayMode)
        for shapeMode in self.__shapeModes:
            self.shapeCBox.addItem(shapeMode)
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
        self.scaleFactor.valueChanged.connect(self.updateScaleFactor)
        self.minNeighbors.valueChanged.connect(self.updateMinNeighbors)
        self.minWidth.valueChanged.connect(self.updateMinWidth)
        self.minHeight.valueChanged.connect(self.updateMinHeight)
        self.shapeCBox.currentIndexChanged.connect(self.updateShape)
        self.blur.stateChanged.connect(self.updateBlur)
        self.autoNeighbors.clicked.connect(self.calcNeighbors)

    def initUI(self):
        self.showClassifierParameters(None, None)
        self.equalizeHist.setChecked(True)

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
        self.classifiersParameters[item.data()] = ClassifierParameters(node, node,
                                                                       color, self.SHAPE_RECT)
        parent.appendRow(item)
        return item

    def getBlur(self, pixmap, x, y, w, h, shape):
        mask = QPixmap(pixmap.width(), pixmap.height())
        mask.fill(QtCore.Qt.transparent);
        painter = QtGui.QPainter(mask)
        path = QtGui.QPainterPath()
        if shape == self.SHAPE_ELLIPSE:
            path.addEllipse(x, y, w, h)
            painter.fillPath(path, QtGui.QColor(0, 0, 0))
        elif shape == self.SHAPE_RECT:
            painter.fillRect(x, y, w, h, QtGui.QColor(0, 0, 0))
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceAtop)
        painter.drawPixmap(0, 0, common.blurPixmap(pixmap, 20))
        return mask

    def drawRects(self, pixmap, rectsTree, scale):
        """Draw rectangles in 'rectsTree' on 'pixmap'.
        """
        painter = QtGui.QPainter(pixmap)

        def drawRect(node, parentRoi):
            roi, param = node.data
            x, y, w, h = common.scaleRect(roi, scale)
            cx, cy, cw, ch = parentRoi
            painter.setPen(param.color)
            x, y = cx + x, cy + y
            if param.blur:
                blurred = self.getBlur(pixmap, x, y, w, h, param.shape)
                painter.drawPixmap(0, 0, blurred)
            else:
                painter.drawText(x, y, param.name)
                drawFunc = painter.drawRect
                if param.shape == self.SHAPE_ELLIPSE:
                    drawFunc = painter.drawEllipse
                drawFunc(x, y, w, h)
            return (x, y, w, h)

        h, w = pixmap.height(), pixmap.width()
        rectsTree.map((0, 0, w, h), drawRect)

    def debugTable(self, args, append=False):
        """Display debug info into table.
        """
        rows = len(args)
        if not append:
            self.debugCursor = self.debugText.textCursor()
            format = QtGui.QTextTableFormat()
            constraints = [QtGui.QTextLength(QtGui.QTextLength.FixedLength,
                                             size) for arg, size in args]
            format.setColumnWidthConstraints(constraints)
            format.setBorder(0)
            format.setCellPadding(2)
            format.setCellSpacing(0)
            self.debugCursor.insertTable(1, rows, format)
        scroll = self.debugText.verticalScrollBar()
        for arg, size in args:
            if arg:
                self.debugCursor.insertText(arg)
                self.debugCursor.movePosition(QtGui.QTextCursor.NextCell)
                scroll.setSliderPosition(scroll.maximum())

    def debugEmitter(self, args, append=False):
        """Debug signal to allow threaded debug infos.
        """
        self.debugSignal.emit(args, append)

    def displayImage(self, img, autoNeighbors=False):
        """Display numpy 'img' in 'mediaLabel'.
        """
        self.currentFrame = img
        item = None
        if autoNeighbors:
            indexes = self.objectsTree.selectedIndexes()
            if indexes:
                item = self.objectsTree.model().itemFromIndex(indexes[0])
        # Detect on full size image
        tree, extracted = common.getObjectsTree(self.objectsTree,
                                                self.classifiersParameters,
                                                item)
        equalizeHist = self.equalizeHist.isChecked()
        rectsTree = self.detector.detect(img, tree, equalizeHist,
                                         self.debugEmitter, extracted)
        displayMode = self.__displayModes[self.displayCBox.currentIndex()]
        if displayMode == self.DISPLAY_PREPROCESSED:
            img = self.detector.preprocessed
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

    def getCurrentClassifierParameters(self):
        index = self.objectsTree.currentIndex()
        item = index.model().itemFromIndex(index)
        param = self.classifiersParameters[item.data()]
        return item, param

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

    def calcNeighbors(self):
        if self.videoThread.isRunning():
            self.videoThread.stop()
        self.videoThread.clean()
        self.displayImage(self.currentFrame, autoNeighbors=True)
        self.showClassifierParameters(None, None)
        self.refresh()

    def updateClassifierParameters(self, name=None, color=None):
        """Update classifier parameters.
        """
        item, param = self.getCurrentClassifierParameters()
        if name:
            item.setText(name)
            param.name = name
        if color:
            item.setIcon(self.getIcon(color))
            param.color = color

    def updateScaleFactor(self, value):
        """Update scale factor classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        param.scaleFactor = value

    def updateShape(self, index):
        """Update shape classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        param.shape = self.__shapeModes[index]

    def updateBlur(self, checked):
        """Update blur classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        param.blur = checked

    def updateMinNeighbors(self, value):
        """Update min neighbors classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        param.minNeighbors = value

    def updateMinWidth(self, value):
        """Update minimum width classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        w, h = param.minSize
        param.minSize = (value, h)

    def updateMinHeight(self, value):
        """Update minimum height classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        w, h = param.minSize
        param.minSize = (w, value)

    def showClassifierParameters(self, selected, deselected):
        """Show the selected classifier parameters.
        """
        selectedCount = len(self.objectsTree.selectedIndexes())
        if selectedCount == 1:
            self.parametersBox.setEnabled(True)
            index = self.objectsTree.currentIndex()
            item = index.model().itemFromIndex(index)
            param = self.classifiersParameters[item.data()]
            self.classifierName.setText(param.name)
            common.setPickerColor(param.color, self.colorPicker)
            self.classifierType.setText('(' + param.classifier + ')')
            self.scaleFactor.setValue(param.scaleFactor)
            self.minNeighbors.setValue(param.minNeighbors)
            w, h = param.minSize
            self.minWidth.setValue(w)
            self.minHeight.setValue(h)
            self.shapeCBox.setCurrentIndex(self.__shapeModes.index(param.shape))
            self.blur.setChecked(param.blur)
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
    QApplication.addLibraryPath(QApplication.applicationDirPath() + "/../PlugIns")
    main = Window()
    main.setWindowTitle('Detection')
    main.show()
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

