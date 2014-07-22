#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detection.py
#
# Author: Yann KOETH
# Created: Mon Jul 14 13:51:02 2014 (+0200)
# Last-Updated: Tue Jul 22 13:37:09 2014 (+0200)
#           By: Yann KOETH
#     Update #: 1830
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

    FILL_TRANSPARENT = 'Transparent'
    FILL_COLOR = 'Color'
    FILL_BLUR = 'Blur'
    FILL_IMAGE = 'Image'
    FILL_MASK = 'Mask'

    __sourceModes = [SOURCE_IMAGE, SOURCE_VIDEO, SOURCE_CAMERA]
    __displayModes = [DISPLAY_INPUT, DISPLAY_PREPROCESSED]
    __shapeModes = [SHAPE_RECT, SHAPE_ELLIPSE]
    __fillModes = [FILL_TRANSPARENT, FILL_BLUR, FILL_IMAGE, FILL_MASK, FILL_COLOR]

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
        for fillMode in self.__fillModes:
            self.fillCBox.addItem(fillMode)
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
        self.fillCBox.currentIndexChanged.connect(self.updateFill)
        self.autoNeighbors.clicked.connect(self.calcNeighbors)
        self.stabilize.stateChanged.connect(self.updateStabilize)
        self.tracking.stateChanged.connect(self.updateTracking)
        self.showName.stateChanged.connect(self.updateShowName)
        self.fillPath.clicked.connect(self.loadFillPath)

    def initUI(self):
        self.showClassifierParameters(None, None)
        self.equalizeHist.setChecked(True)
        self.toggleFillPath()

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
        h, s, v = Detector.getDefaultHSVColor(node)
        color = QColor()
        color.setHsvF(h, s, v)
        item.setIcon(self.getIcon(color))
        cp = ClassifierParameters(item.data(), node, node, color,
                                  self.SHAPE_RECT, self.FILL_TRANSPARENT)
        key = hash(item)
        while key in self.classifiersParameters:
            key += 1
        item.setData(key)
        self.classifiersParameters[key] = cp
        parent.appendRow(item)
        return item

    def getMask(self, pixmap, x, y, w, h, shape, overlay,
                bg=QtCore.Qt.transparent, fg=QtCore.Qt.black):
        mask = QPixmap(pixmap.width(), pixmap.height())
        mask.fill(bg)
        painter = QtGui.QPainter(mask)
        path = QtGui.QPainterPath()
        if shape == self.SHAPE_ELLIPSE:
            path.addEllipse(x, y, w, h)
            painter.fillPath(path, fg)
        elif shape == self.SHAPE_RECT:
            painter.fillRect(x, y, w, h, fg)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceAtop)
        if overlay:
            painter.drawPixmap(0, 0, overlay)
        return mask

    def drawTracking(self, painter, tracking, scale):
        if not tracking:
            return
        hashTable = {}
        for track in tracking:
            for rect, hash in track:
                x, y, w, h = common.scaleRect(rect, scale)
                x, y = x + w / 2, y + h / 2
                if hash in hashTable:
                    hashTable[hash].append((x, y))
                else:
                    hashTable[hash] = [(x, y)]
        for hash, points in hashTable.iteritems():
            prev = None
            for point in points:
                if prev:
                    x1, y1 = point
                    x2, y2 = prev
                    painter.drawLine(x1, y1, x2, y2)
                prev = point

    def drawRects(self, source, rectsTree, scale):
        """Draw rectangles in 'rectsTree' on 'pixmap'.
        """
        pixmap = QPixmap(source)
        def drawRect(node, arg):
            painter = QtGui.QPainter(pixmap)
            roi, param, tracking = node.data
            x, y, w, h = common.scaleRect(roi, scale)
            painter.setPen(param.color)
            if param.fill == self.FILL_MASK:
                masked = self.getMask(pixmap, x, y, w, h, param.shape, source)
                if not arg:
                    painter.eraseRect(0, 0, pixmap.width(), pixmap.height())
                    painter.fillRect(0, 0, pixmap.width(), pixmap.height(), QtCore.Qt.transparent)
                painter.drawPixmap(0, 0, masked)
            elif param.fill == self.FILL_BLUR:
                blurred = self.getMask(pixmap, x, y, w, h, param.shape,
                                       common.blurPixmap(pixmap, 20))
                painter.drawPixmap(0, 0, blurred)
            elif param.fill == self.FILL_IMAGE:
                fillPixmap = QPixmap(param.fillPath)
                if not fillPixmap.isNull():
                    fillPixmap = fillPixmap.scaled(w, h, QtCore.Qt.IgnoreAspectRatio)
                    mask = self.getMask(pixmap, x, y, w, h, param.shape, None,
                                        QtCore.Qt.white, QtCore.Qt.black)
                    painter.setClipRegion(QtGui.QRegion(QtGui.QBitmap(mask)))
                    painter.drawPixmap(x, y, fillPixmap)
                    painter.setClipping(False)
            elif param.fill == self.FILL_COLOR:
                if param.shape == self.SHAPE_ELLIPSE:
                    path = QtGui.QPainterPath()
                    path.addEllipse(x, y, w, h)
                    painter.fillPath(path, param.color)
                elif param.shape == self.SHAPE_RECT:
                    painter.fillRect(x, y, w, h, param.color)
            else:
                drawFunc = painter.drawRect
                if param.shape == self.SHAPE_ELLIPSE:
                    drawFunc = painter.drawEllipse
                drawFunc(x, y, w, h)
            if param.tracking:
                self.drawTracking(painter, tracking, scale)
            if param.showName:
                painter.drawText(x, y, param.name)
            return True

        h, w = pixmap.height(), pixmap.width()
        rectsTree.map(None, drawRect)
        return pixmap

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

    def displayImage(self, img, autoNeighbors=False, autoNeighborsParam=None):
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
                                         self.debugEmitter, extracted, autoNeighborsParam)
        displayMode = self.__displayModes[self.displayCBox.currentIndex()]
        if displayMode == self.DISPLAY_PREPROCESSED:
            img = self.detector.preprocessed
        pixmap = common.np2Qt(img)
        w = float(pixmap.width())
        # Scale image
        pixmap = common.fitImageToScreen(pixmap)
        scaleFactor = pixmap.width() / w
        # Draw scaled rectangles
        pixmap = self.drawRects(pixmap, rectsTree, scaleFactor)
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
        except common.CustomException as err:
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

    def toggleFillPath(self):
        index = self.fillCBox.currentIndex()
        fillMode = self.__fillModes[index]
        if fillMode == self.FILL_IMAGE:
            self.fillPath.show()
        else:
            self.fillPath.hide()

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

    def loadFillPath(self):
        filters = self.tr('Image (*.jpg *.png *.jpeg *.bmp)')
        path, filters = QFileDialog.getOpenFileName(self, self.tr('Open file'),
                                                    '.', filters)
        if path:
            item, param = self.getCurrentClassifierParameters()
            param.fillPath = path

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
        self.displayImage(self.currentFrame, autoNeighbors=True,
                          autoNeighborsParam=self.autoNeighborsParam.value())
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

    def updateStabilize(self, checked):
        """Update scale factor classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        param.stabilize = checked

    def updateTracking(self, checked):
        """Update tracking classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        param.tracking = checked

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

    def updateFill(self, index):
        """Update fill classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        param.fill = self.__fillModes[index]
        self.toggleFillPath()

    def updateShowName(self, checked):
        """Update show name classifier parameter.
        """
        item, param = self.getCurrentClassifierParameters()
        param.showName = checked

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
            self.displayBox.setEnabled(True)
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
            self.fillCBox.setCurrentIndex(self.__fillModes.index(param.fill))
            self.stabilize.setChecked(param.stabilize)
            self.showName.setChecked(param.showName)
            self.tracking.setChecked(param.tracking)
        else:
            self.displayBox.setEnabled(False)
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

