# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'newleveldialog.ui'
#
# Created: Sun Nov 16 21:36:26 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_NewLevelDialog(object):
    def setupUi(self, NewLevelDialog):
        NewLevelDialog.setObjectName("NewLevelDialog")
        NewLevelDialog.resize(313,95)
        self.verticalLayout = QtGui.QVBoxLayout(NewLevelDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtGui.QLabel(NewLevelDialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.levelName = QtGui.QLineEdit(NewLevelDialog)
        self.levelName.setMaxLength(100)
        self.levelName.setObjectName("levelName")
        self.verticalLayout.addWidget(self.levelName)
        self.buttonBox = QtGui.QDialogButtonBox(NewLevelDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)
        self.label.setBuddy(self.levelName)

        self.retranslateUi(NewLevelDialog)
        QtCore.QObject.connect(self.buttonBox,QtCore.SIGNAL("accepted()"),NewLevelDialog.accept)
        QtCore.QObject.connect(self.buttonBox,QtCore.SIGNAL("rejected()"),NewLevelDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(NewLevelDialog)

    def retranslateUi(self, NewLevelDialog):
        NewLevelDialog.setWindowTitle(QtGui.QApplication.translate("NewLevelDialog", "Create New Level", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("NewLevelDialog", "&New level name (directory name):", None, QtGui.QApplication.UnicodeUTF8))

