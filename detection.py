#!/usr/bin/env python
# -*- coding: utf-8 -*-
# detection.py
#
# Author: Yann KOETH
# Created: Mon Jul 14 13:51:02 2014 (+0200)
# Last-Updated: Thu Jul 24 13:50:06 2014 (+0200)
#           By: Yann KOETH
#     Update #: 2186
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
from PyQt5.QtGui import QImage, QPixmap, QColor, QIcon, QPalette

from window_ui import WindowUI
import detector
from detector import Detector, ClassifierParameters
import common
from tree import Tree

class MediaThread(QtCore.QThread):
    def __init__(self, mw):
        super(MediaThread, self).__init__(mw)
        self.mw = mw
        self.stopped = False
        self.capture = None
        self.nextFrame = False
        self.mutex = QtCore.QMutex()
        self.mode = None

    def stop(self):
        """Stop media thread.
        """
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = True

    def clean(self):
        """Clean media thread.
        """
        self.wait()
        del self.capture
        self.capture = None

    def setNextFrameMode(self, enable):
        self.nextFrame = enable

    def main(self, mode, path):
        """Main loop.
        """
        if not self.capture or not self.capture.isOpened() or self.mode != mode:
            self.capture = cv2.VideoCapture(path)

        self.mode = mode

        if not self.capture.isOpened():
            print "Couldn't read media " + path
        while self.capture.isOpened():
            if self.stopped:
                break
            ret, frame = self.capture.read()
            if frame is None:
                #self.capture = cv2.VideoCapture(path)
                #ret, frame = self.capture.read()
                if frame is None:
                    break
            if mode == self.mw.SOURCE_CAMERA:
                cv2.flip(frame, 1, frame)

            self.mw.displayImage(frame)
            QApplication.processEvents()
            if self.nextFrame:
                self.setNextFrameMode(False)
                break

    def run(self):
        """Method Override.
        """
        with QtCore.QMutexLocker(self.mutex):
            self.stopped = False

        mode = self.mw.getSourceMode()
        path = self.mw.sourcePath.text() if mode == self.mw.SOURCE_FILE else 0
        if mode == self.mw.SOURCE_FILE and not path:
            print 'File path is empty'
        else:
            self.main(mode, path)
        self.mw.togglePlayButton(play=False)

class Window(QWidget, WindowUI):

    SOURCE_FILE = 'File'
    SOURCE_CAMERA = 'Camera'

    DISPLAY_INPUT = 'Input'
    DISPLAY_PREPROCESSED = 'Pre-processed'

    SHAPE_RECT = 'Rectangle'
    SHAPE_ELLIPSE = 'Ellipse'

    FILL_NONE = 'None'
    FILL_OUTLINE = 'Outline'
    FILL_COLOR = 'Color'
    FILL_BLUR = 'Blur'
    FILL_IMAGE = 'Image'
    FILL_MASK = 'Mask'

    BG_INPUT = 'Input'
    BG_COLOR = 'Color'
    BG_TRANSPARENT = 'Transparent'
    BG_IMAGE = 'Image'

    __sourceModes = [SOURCE_FILE, SOURCE_CAMERA]
    __displayModes = [DISPLAY_INPUT, DISPLAY_PREPROCESSED]
    __shapeModes = [SHAPE_RECT, SHAPE_ELLIPSE]
    __fillModes = [FILL_NONE, FILL_OUTLINE, FILL_BLUR, FILL_IMAGE, FILL_MASK, FILL_COLOR]
    __bgModes = [BG_INPUT, BG_COLOR, BG_TRANSPARENT, BG_IMAGE]

    IMAGE_FILTERS = '*.jpg *.png *.jpeg *.bmp'
    VIDEO_FILTERS = '*.avi *.mp4 *.mov'
    MASK_PATH = 'other/mask.png'

    debugSignal = QtCore.pyqtSignal(object, int)

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.detector = Detector()
        self.mediaThread = MediaThread(self)
        sys.stdout = common.EmittingStream(textWritten=self.normalOutputWritten)
        self.debugSignal.connect(self.debugTable)
        self.currentFrame = None
        self.bgColor = QColor(255, 255, 255)
        self.bgPath = ''

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
        for bgMode in self.__bgModes:
            self.bgCBox.addItem(bgMode)
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
        self.playButton.clicked.connect(self.play)
        self.refreshButton.clicked.connect(self.refresh)
        self.nextFrameButton.clicked.connect(self.nextFrame)
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
        self.bgColorPicker.clicked.connect(self.bgColorDialog)
        self.bgPathButton.clicked.connect(self.bgPathDialog)
        self.bgCBox.currentIndexChanged.connect(self.toggleBgParams)

    def initUI(self):
        self.showClassifierParameters(None, None)
        self.equalizeHist.setChecked(True)
        self.toggleFillPath()
        self.toggleBgParams(self.bgCBox.currentIndex())
        common.setPickerColor(self.bgColor, self.bgColorPicker)
        self.togglePlayButton(False)

    ########################################################
    # Utils

    def getIcon(self, color):
        """Returns a colored icon.
        """
        pixmap = QPixmap(14, 14)
        pixmap.fill(color)
        return QIcon(pixmap)

    def populateTree(self, node, parent):
        """Create a QTreeView node under 'parent'.
        """
        item = QtGui.QStandardItem(node)
        h, s, v = Detector.getDefaultHSVColor(node)
        color = QColor()
        color.setHsvF(h, s, v)
        item.setIcon(self.getIcon(color))
        # Unique hash for QStandardItem
        key = hash(item)
        while key in self.classifiersParameters:
            key += 1
        item.setData(key)
        cp = ClassifierParameters(item.data(), node, node, color,
                                  self.SHAPE_RECT, self.FILL_OUTLINE)
        self.classifiersParameters[key] = cp
        parent.appendRow(item)
        return item

    def getMask(self, pixmap, x, y, w, h, shape, overlay,
                bg=QtCore.Qt.transparent, fg=QtCore.Qt.black, progressive=False):
        """Create a shape mask with the same size of pixmap.
        """
        mask = QPixmap(pixmap.width(), pixmap.height())
        mask.fill(bg)
        path = QtGui.QPainterPath()

        if progressive:
            progressive = QPixmap(pixmap.width(), pixmap.height())
            progressive.fill(QtCore.Qt.transparent)
            progressiveMask = QPixmap(self.MASK_PATH)
            progressiveMask = progressiveMask.scaled(w, h, QtCore.Qt.IgnoreAspectRatio)
            progressivePainter = QtGui.QPainter(progressive)
            progressivePainter.drawPixmap(x, y, progressiveMask)
            del progressivePainter
            fg = QtGui.QBrush(progressive)

        painter = QtGui.QPainter(mask)
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
        """Draw lines between each position in tracking list.
        """
        if not tracking:
            return
        hashTable = {}
        # Group tracks by item hash
        for track in tracking:
            for rect, hash in track:
                x, y, w, h = common.scaleRect(rect, scale)
                x, y = x + w / 2, y + h / 2
                if hash in hashTable:
                    hashTable[hash].append((x, y))
                else:
                    hashTable[hash] = [(x, y)]
        # Draw
        for hash, points in hashTable.iteritems():
            prev = None
            for point in points:
                if prev:
                    x1, y1 = point
                    x2, y2 = prev
                    painter.drawLine(x1, y1, x2, y2)
                prev = point

    def drawBackground(self, pixmap):
        """Draw background in pixmap.
        """
        w, h = pixmap.width(), pixmap.height()
        mode = self.__bgModes[self.bgCBox.currentIndex()]
        source = QPixmap(pixmap)
        painter = QtGui.QPainter(pixmap)
        if mode == self.BG_COLOR:
            painter.fillRect(0, 0, w, h, self.bgColor)
        if mode == self.BG_TRANSPARENT or mode == self.BG_IMAGE or mode == self.BG_INPUT:
            painter.drawPixmap(0, 0, common.checkerboard(pixmap.size()))
        if mode == self.BG_IMAGE and self.bgPath:
            bgPixmap = QPixmap(self.bgPath)
            if not bgPixmap.isNull():
                bgPixmap = bgPixmap.scaled(w, h, QtCore.Qt.IgnoreAspectRatio)
                painter.drawPixmap(0, 0, bgPixmap)
        if mode == self.BG_INPUT:
            painter.drawPixmap(0, 0, source)

    def fillMask(self, pixmap, painter, roi, param, source):
        """Draw mask in roi.
        """
        x, y, w, h = roi
        masked = self.getMask(pixmap, x, y, w, h, param.shape,
                              source, progressive=True)
        painter.drawPixmap(0, 0, masked)

    def fillBlur(self, pixmap, painter, roi, param, source):
        """Draw blur in roi.
        """
        x, y, w, h = roi
        blurred = self.getMask(pixmap, x, y, w, h, param.shape,
                               common.blurPixmap(pixmap, 20))
        painter.drawPixmap(0, 0, blurred)


    def fillImage(self, pixmap, painter, roi, param, source):
        """Draw image in roi.
        """
        x, y, w, h = roi
        fillPixmap = QPixmap(param.fillPath)
        if not fillPixmap.isNull():
            fillPixmap = fillPixmap.scaled(w, h, QtCore.Qt.IgnoreAspectRatio)
            mask = self.getMask(pixmap, x, y, w, h, param.shape, None,
                                QtCore.Qt.white, QtCore.Qt.black)
            painter.setClipRegion(QtGui.QRegion(QtGui.QBitmap(mask)))
            painter.drawPixmap(x, y, fillPixmap)
            painter.setClipping(False)

    def fillColor(self, pixmap, painter, roi, param, source):
        """Draw color in roi.
        """
        x, y, w, h = roi
        if param.shape == self.SHAPE_ELLIPSE:
            path = QtGui.QPainterPath()
            path.addEllipse(x, y, w, h)
            painter.fillPath(path, param.color)
        elif param.shape == self.SHAPE_RECT:
            painter.fillRect(x, y, w, h, param.color)

    def fillOutline(self, pixmap, painter, roi, param, source):
        """Draw outline in roi.
        """
        x, y, w, h = roi
        drawFunc = painter.drawRect
        if param.shape == self.SHAPE_ELLIPSE:
            drawFunc = painter.drawEllipse
        drawFunc(x, y, w, h)

    def drawRects(self, source, rectsTree, scale):
        """Draw rectangles in 'rectsTree' on 'source'.
        """
        pixmap = QPixmap(source)
        self.drawBackground(pixmap)

        def drawRect(node, parentHash):
            painter = QtGui.QPainter(pixmap)
            roi, param, tracking = node.data
            x, y, w, h = common.scaleRect(roi, scale)
            painter.setPen(param.color)
            funcTable = {
                self.FILL_MASK: self.fillMask,
                self.FILL_BLUR: self.fillBlur,
                self.FILL_IMAGE: self.fillImage,
                self.FILL_COLOR: self.fillColor,
                self.FILL_OUTLINE: self.fillOutline
                         }
            for fill, func in funcTable.iteritems():
                if param.fill == fill:
                    func(pixmap, painter, (x, y, w, h), param, source)
            if param.tracking:
                self.drawTracking(painter, tracking, scale)
            if param.showName:
                painter.drawText(x, y, param.name)
            return param.hash

        h, w = pixmap.height(), pixmap.width()
        rectsTree.map(None, drawRect)
        painter = QtGui.QPainter(source)
        painter.drawPixmap(0, 0, pixmap)

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

    def detect(self, img, autoNeighbors=False, autoNeighborsParam=None):
        """Detect objects in img.
        """
        self.currentFrame = img
        item = None
        indexes = self.objectsTree.selectedIndexes()
        if autoNeighbors and indexes:
            item = self.objectsTree.model().itemFromIndex(indexes[0])
        # Detect on full size image
        tree, extracted = common.getObjectsTree(self.objectsTree,
                                                self.classifiersParameters,
                                                indexes, item)
        equalizeHist = self.equalizeHist.isChecked()
        rectsTree = self.detector.detect(img, tree, equalizeHist,
                                         self.debugEmitter, extracted, autoNeighborsParam)
        return rectsTree

    def displayImage(self, img):
        """Display numpy 'img' in 'mediaLabel'.
        """
        rectsTree = self.detect(img)
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
        if self.mediaThread.isRunning():
            self.mediaThread.stop()
            self.mediaThread.wait()
        sourceMode = self.__sourceModes[self.sourceCBox.currentIndex()]
        self.mediaThread.start()
        self.togglePlayButton(True)

    def getSourceMode(self):
        """Return the current source mode.
        """
        return self.__sourceModes[self.sourceCBox.currentIndex()]

    def getCurrentClassifierParameters(self):
        """Return current classifier parameters.
        """
        index = self.objectsTree.currentIndex()
        item = index.model().itemFromIndex(index)
        param = self.classifiersParameters[item.data()]
        return item, param

    def toggleFillPath(self):
        """Display fill path dialog button if needed.
        """
        index = self.fillCBox.currentIndex()
        fillMode = self.__fillModes[index]
        if fillMode == self.FILL_IMAGE:
            self.fillPath.show()
        else:
            self.fillPath.hide()

    def togglePlayButton(self, play=True):
        """Switch between play and pause icons.
        """
        if play is True:
            self.playButton.setIcon(QIcon('assets/pause.png'))
        else:
            self.playButton.setIcon(QIcon('assets/play.png'))

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

    def play(self):
        """Play current media.
        """
        if self.mediaThread.isRunning():
            self.mediaThread.stop()
            self.mediaThread.wait()
        else:
            self.displayMedia(self.sourcePath.text())

    def refresh(self):
        """Refresh current media.
        """
        if self.mediaThread.isRunning():
            self.mediaThread.stop()
        self.mediaThread.clean()
        self.displayMedia(self.sourcePath.text())

    def nextFrame(self):
        """Go to next frame of current media.
        """
        self.mediaThread.setNextFrameMode(True)
        self.displayMedia(self.sourcePath.text())

    def loadFillPath(self):
        """Display file dialog to choose fill image.
        """
        filters = self.tr('Image (' + self.IMAGE_FILTERS + ')')
        path, filters = QFileDialog.getOpenFileName(self, self.tr('Open file'),
                                                    '.', filters)
        if path:
            item, param = self.getCurrentClassifierParameters()
            param.fillPath = path

    def loadMedia(self):
        """Load image or video.
        """
        filters = ""
        filters = self.tr('Image (' + self.IMAGE_FILTERS + self.VIDEO_FILTERS + ')')
        path, filters = QFileDialog.getOpenFileName(self, self.tr('Open file'), '.',
                                                    filters)
        if path:
            self.sourcePath.setText(path)
            self.mediaThread.stop()
            self.mediaThread.clean()
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
            common.setPickerColor(color, self.colorPicker)
            self.updateClassifierParameters(color=color)

    def bgColorDialog(self):
        """Open color dialog to pick a color.
        """
        color = QColorDialog.getColor()
        if color.isValid():
            self.bgColor = color
            common.setPickerColor(color, self.bgColorPicker)

    def bgPathDialog(self):
        """Open file dialog to select background image.
        """
        filters = self.tr('Image (' + self.IMAGE_FILTERS + ')')
        path, filters = QFileDialog.getOpenFileName(self, self.tr('Open file'),
                                                    '.', filters)
        if path:
            self.bgPath = path

    def toggleBgParams(self, index):
        """Hide / Show color picker and button path for background.
        """
        mode = self.__bgModes[index]
        if mode == self.BG_COLOR:
            self.bgColorPicker.show()
        else:
            self.bgColorPicker.hide()
        if mode == self.BG_IMAGE:
            self.bgPathButton.show()
        else:
            self.bgPathButton.hide()

    def calcNeighbors(self):
        """Automatically calculate minimum neighbors.
        """
        running = False
        if self.mediaThread.isRunning():
            running = True
            self.mediaThread.stop()
            self.mediaThread.wait()
        self.detect(self.currentFrame, autoNeighbors=True,
                    autoNeighborsParam=self.autoNeighborsParam.value())
        self.showClassifierParameters(None, None)
        if running:
            self.displayMedia(self.sourcePath.text())
        else:
            self.displayImage(self.currentFrame)

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
        """Update stabilize classifier parameter.
        """
        running = False
        if self.mediaThread.isRunning():
            running = True
            self.mediaThread.stop()
            self.mediaThread.wait()
        item, param = self.getCurrentClassifierParameters()
        param.stabilize = checked
        self.detect(self.currentFrame)
        if running:
            self.displayMedia(self.sourcePath.text())
        else:
            self.displayImage(self.currentFrame)

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
    app.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
    p = app.palette()
    p.setColor(QPalette.Base, QColor(40, 40, 40))
    p.setColor(QPalette.Window, QColor(55, 55, 55))
    p.setColor(QPalette.Button, QColor(49, 49, 49))
    p.setColor(QPalette.Highlight, QColor(135, 135, 135))
    p.setColor(QPalette.ButtonText, QColor(155, 155, 155))
    p.setColor(QPalette.WindowText, QColor(155, 155, 155))
    p.setColor(QPalette.Text, QColor(155, 155, 155))
    p.setColor(QPalette.Disabled, QPalette.Base, QColor(49, 49, 49))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor(90, 90, 90))
    p.setColor(QPalette.Disabled, QPalette.Button, QColor(42, 42, 42))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(90, 90, 90))
    p.setColor(QPalette.Disabled, QPalette.Window, QColor(49, 49, 49))
    p.setColor(QPalette.Disabled, QPalette.WindowText, QColor(90, 90, 90))
    app.setPalette(p)
    QApplication.addLibraryPath(QApplication.applicationDirPath() + "/../PlugIns")
    main = Window()
    main.setWindowTitle('Detection')
    main.setWindowIcon(QtGui.QIcon('assets/icon.png'))
    main.show()
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()

