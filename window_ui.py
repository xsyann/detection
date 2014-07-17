#!/usr/bin/env python
# -*- coding: utf-8 -*-
# window_ui.py
#
# Author: Yann KOETH
# Created: Wed Jul 16 19:06:25 2014 (+0200)
# Last-Updated: Thu Jul 17 16:04:32 2014 (+0200)
#           By: Yann KOETH
#     Update #: 122
#

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (QApplication, QWidget, QFileDialog, QPushButton,
                             QHBoxLayout, QVBoxLayout, QDesktopWidget, QScrollArea,
                             QLabel, QLineEdit, QListWidget, QComboBox,
                             QSplitter, QGroupBox, QTextEdit, QAbstractItemView)

from PyQt5.QtGui import QIcon, QDropEvent, QDragMoveEvent

class QTreeView(QtWidgets.QTreeView):
    customSelectionChanged = QtCore.pyqtSignal(QtCore.QItemSelection, QtCore.QItemSelection)

    def __init__(self):
        super(QTreeView, self).__init__()

    def selectionChanged(self, *args, **kwds):
        self.customSelectionChanged.emit(*args, **kwds)
        super(QTreeView, self).selectionChanged(*args, **kwds)

class WindowUI():

    def widgetSource(self):
        """Create source widget.
        """
        hbox = QHBoxLayout()
        sourceLabel = QLabel(self.tr('Source'))

        self.sourceCBox = QComboBox(self)
        self.sourcePath = QLineEdit(self)
        self.sourcePathButton = QPushButton('...')

        self.refreshButton = QPushButton('')
        self.refreshButton.setIcon(QIcon('assets/refresh.png'))
        self.refreshButton.setIconSize(QtCore.QSize(20, 20))
        self.refreshButton.setMinimumSize(QtCore.QSize(20, 20))
        self.refreshButton.setMaximumSize(QtCore.QSize(20, 20))
        css = "QPushButton { border: none; }" \
            "QPushButton:pressed { border: 1px solid gray; background-color: #aaa; }"
        self.refreshButton.setStyleSheet(css)

        self.sourceCBox.setCurrentIndex(0)

        hbox.addWidget(sourceLabel)
        hbox.addWidget(self.sourceCBox)
        hbox.addWidget(self.sourcePath)
        hbox.addWidget(self.sourcePathButton)
        hbox.addWidget(self.refreshButton)
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
        tree = QTreeView()
        tree.header().setHidden(True)
        tree.setDragEnabled(True)
        tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
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
        self.availableObjectsList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.removeButton = QPushButton(self.tr('>>'))
        self.addButton = QPushButton(self.tr('<<'))

        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addWidget(self.addButton)
        vbox.addWidget(self.removeButton)
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

    def widgetClassifierParameters(self):
        """Create classifier parameters widget.
        """
        hbox = QHBoxLayout()
        nameLabel = QLabel(self.tr('Name'))
        self.classifierName = QLineEdit(self)
        self.classifierType = QLabel('')
        hbox.addWidget(nameLabel)
        hbox.addWidget(self.classifierName)
        hbox.addWidget(self.classifierType)

        color = QtGui.QColor(0, 0, 0)
        self.colorPicker = QPushButton('')
        self.colorPicker.setMaximumSize(QtCore.QSize(16, 16))
        hcolor = QHBoxLayout()
        hcolor.addWidget(QLabel(self.tr('Display color')))
        hcolor.addWidget(self.colorPicker)
        hcolor.addStretch(1)

        vbox = QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addLayout(hcolor)
        return vbox

    def widgetParameters(self):
        """Create parameters widget.
        """
        detectBox = QGroupBox(self.tr('Detect'))
        objects = self.widgetObjectList()
        detectBox.setLayout(objects)
        self.parametersBox = QGroupBox(self.tr('Classifier Parameters'))
        parameters = self.widgetClassifierParameters()
        self.parametersBox.setLayout(parameters)
        vbox = QVBoxLayout()
        vbox.addWidget(detectBox)
        vbox.addWidget(self.parametersBox)
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
        self.showDetails.setChecked(1)
        hbox.addWidget(self.showDetails)
        hbox.addStretch(1)

        vbox.addLayout(hbox)
        vbox.addWidget(self.debugText)
        vbox.addStretch(1)

        return vbox

    def setupUI(self):
        """Create User Interface.
        """
        sourceWidget = self.widgetSource()
        frameWidget = self.widgetFrame()
        parametersWidget = self.widgetParameters()

        leftSide = QWidget()
        leftSide.setLayout(parametersWidget)
        rightSide = QWidget()
        rightSide.setLayout(frameWidget)
        self.hsplitter = QSplitter(QtCore.Qt.Horizontal)
        self.hsplitter.addWidget(leftSide)
        self.hsplitter.addWidget(rightSide)
        self.hsplitter.setStretchFactor(0, 1)
        self.hsplitter.setStretchFactor(1, 10)

        downSide = QWidget()
        downSide.setLayout(self.widgetDebug())
        self.vsplitter = QSplitter(QtCore.Qt.Vertical)
        self.vsplitter.addWidget(self.hsplitter)
        self.vsplitter.addWidget(downSide)
        self.vsplitter.setStretchFactor(0, 10)
        self.vsplitter.setStretchFactor(1, 1)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(sourceWidget)
        mainLayout.addWidget(self.vsplitter)
        self.setLayout(mainLayout)
        self.setGeometry(300, 300, 800, 600)
        self.show()
