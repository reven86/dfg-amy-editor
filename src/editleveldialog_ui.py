# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'editleveldialog.ui'
#
# Created: Thu Nov 18 09:59:08 2010
#      by: PyQt4 UI code generator 4.7.7
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_EditLevelDialog(object):
    def setupUi(self, EditLevelDialog):
        EditLevelDialog.setObjectName(_fromUtf8("EditLevelDialog"))
        EditLevelDialog.resize(400, 345)
        EditLevelDialog.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.verticalLayout = QtGui.QVBoxLayout(EditLevelDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(EditLevelDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.comboBox = QtGui.QComboBox(EditLevelDialog)
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.comboBox.addItem(_fromUtf8(""))
        self.horizontalLayout.addWidget(self.comboBox)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.levelList = QtGui.QListWidget(EditLevelDialog)
        self.levelList.setObjectName(_fromUtf8("levelList"))
        self.verticalLayout.addWidget(self.levelList)
        self.buttonBox = QtGui.QDialogButtonBox(EditLevelDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(EditLevelDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), EditLevelDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), EditLevelDialog.reject)
        QtCore.QObject.connect(self.levelList, QtCore.SIGNAL(_fromUtf8("itemDoubleClicked(QListWidgetItem*)")), EditLevelDialog.accept)
        QtCore.QObject.connect(self.comboBox, QtCore.SIGNAL(_fromUtf8("currentIndexChanged(int)")), EditLevelDialog.comboSelectionChanged)
        QtCore.QMetaObject.connectSlotsByName(EditLevelDialog)

    def retranslateUi(self, EditLevelDialog):
        EditLevelDialog.setWindowTitle(QtGui.QApplication.translate("EditLevelDialog", "Select level to edit...", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("EditLevelDialog", "Select level to edit:", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox.setItemText(0, QtGui.QApplication.translate("EditLevelDialog", "All Levels", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox.setItemText(1, QtGui.QApplication.translate("EditLevelDialog", "Custom Levels Only", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox.setItemText(2, QtGui.QApplication.translate("EditLevelDialog", "Original Levels Only", None, QtGui.QApplication.UnicodeUTF8))

