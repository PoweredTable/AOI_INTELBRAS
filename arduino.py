# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'arduino_window.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_the_form(object):
    def setupUi(self, the_form):
        the_form.resize(403, 528)

        self.verticalLayout_2 = QtWidgets.QVBoxLayout(the_form)

        self.main_layout = QtWidgets.QVBoxLayout()

        self.groupBox = QtWidgets.QGroupBox(the_form)



        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox)

        self.addInput_button = QtWidgets.QPushButton(self.groupBox)
        self.addInput_button.setEnabled(False)


        self.gridLayout_2.addWidget(self.addInput_button, 1, 0, 1, 3)
        self.porta_label = QtWidgets.QLabel(self.groupBox)

        self.gridLayout_2.addWidget(self.porta_label, 0, 0, 1, 1)
        self.conect_button = QtWidgets.QPushButton(self.groupBox)

        self.gridLayout_2.addWidget(self.conect_button, 0, 2, 1, 1)
        self.comsComboBox = QtWidgets.QComboBox(self.groupBox)


        self.comsComboBox.addItem("")
        self.comsComboBox.addItem("")
        self.comsComboBox.addItem("")
        self.comsComboBox.addItem("")
        self.comsComboBox.addItem("")
        self.comsComboBox.addItem("")
        self.gridLayout_2.addWidget(self.comsComboBox, 0, 1, 1, 1)
        self.groupBox_2 = QtWidgets.QGroupBox(self.groupBox)

        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox_2)

        self.added_groupBox = QtWidgets.QGridLayout()

        self.gridLayout_3.addLayout(self.added_groupBox, 0, 0, 1, 1)
        self.gridLayout_2.addWidget(self.groupBox_2, 2, 0, 1, 3)
        self.outputs_button = QtWidgets.QPushButton(self.groupBox)



        self.gridLayout_2.addWidget(self.outputs_button, 3, 0, 1, 1)
        self.confirm_button = QtWidgets.QPushButton(self.groupBox)


        self.confirm_button.setObjectName("confirm_button")
        self.gridLayout_2.addWidget(self.confirm_button, 3, 1, 1, 2)
        self.main_layout.addWidget(self.groupBox)
        self.verticalLayout_2.addLayout(self.main_layout)

        self.retranslateUi(the_form)
        QtCore.QMetaObject.connectSlotsByName(the_form)

    def retranslateUi(self, the_form):
        _translate = QtCore.QCoreApplication.translate
        the_form.setWindowTitle(_translate("the_form", "Form"))
        self.groupBox.setTitle(_translate("the_form", "Configurações do Arduino"))
        self.addInput_button.setText(_translate("the_form", "Adicionar entrada"))
        self.porta_label.setText(_translate("the_form", "Porta do arduino:"))
        self.conect_button.setText(_translate("the_form", "Conectar"))
        self.comsComboBox.setItemText(0, _translate("the_form", "COM1"))
        self.comsComboBox.setItemText(1, _translate("the_form", "COM2"))
        self.comsComboBox.setItemText(2, _translate("the_form", "COM3"))
        self.comsComboBox.setItemText(3, _translate("the_form", "COM4"))
        self.comsComboBox.setItemText(4, _translate("the_form", "COM5"))
        self.comsComboBox.setItemText(5, _translate("the_form", "COM6"))
        self.groupBox_2.setTitle(_translate("the_form", "Entradas adicionadas"))
        self.outputs_button.setText(_translate("the_form", "Saídas..."))
        self.confirm_button.setText(_translate("the_form", "Validar configurações"))
