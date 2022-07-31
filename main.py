import json
import os
import time
from configparser import ConfigParser
from pyfirmata import ArduinoNano, util

from multiprocessing import Process, SimpleQueue
from threading import Thread

import console_log as c_log

from connections import clean_up_pins
from ini_files import get_ports_from_json, get_opr, defaults, get_port_connection, get_ini_configs
from trigger import generate_trigger_function
from core import inspection

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.core_process, self.queue_reader = None, None
        self.program_started = False
        self.console_queue = SimpleQueue()

        self.calha_nome = get_ini_configs()
        self.setWindowIcon(QIcon('icon_simnext.png'))
        self.setWindowTitle(f'AOI INTELBRAS')

        self.central_widget = QtWidgets.QWidget()
        self.central_layout = QtWidgets.QGridLayout(self.central_widget)
        self.gridLayout = QtWidgets.QGridLayout()

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        font = QtGui.QFont()
        font.setPointSize(14)

        self.arduino_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.arduino_pushButton.setText('ARDUINO')
        self.arduino_pushButton.setSizePolicy(size_policy)
        self.arduino_pushButton.setFont(font)

        self.cameras_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.cameras_pushButton.setText('CÂMERAS')
        self.cameras_pushButton.setSizePolicy(size_policy)
        self.cameras_pushButton.setFont(font)

        self.placas_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.placas_pushButton.setText('PLACAS')
        self.placas_pushButton.setSizePolicy(size_policy)
        self.placas_pushButton.setFont(font)

        size_policy.setHorizontalStretch(1)

        self.cadastro_pushButton = QtWidgets.QPushButton(self.central_widget)
        # TODO: REMOVE USER'S TEMPORARY NAME TAG ID AUTOMATICALLY.
        # TODO: CHECK FUNCTION IF THE NAME TAG READER IS CONNECTED.
        self.cadastro_pushButton.setText('CRACHÁ')
        self.cadastro_pushButton.setSizePolicy(size_policy)
        self.cadastro_pushButton.setFont(font)

        self.cleanLog_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.cleanLog_pushButton.setText('LIMPAR LOG')

        self.scrolling_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.scrolling_pushButton.setText('SCROLLING')
        self.scrolling_pushButton.setCheckable(True)
        self.scrolling_pushButton.setChecked(True)

        self.start_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.start_pushButton.setText('INICIAR')
        self.start_pushButton.setStyleSheet("background-color: rgb(64, 134, 32);\n"
                                            "color: rgb(255, 255, 255);")
        self.start_pushButton.setSizePolicy(size_policy)
        self.start_pushButton.setFont(font)

        self.verify_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.verify_pushButton.setText('VERIFICAR')

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(5)
        size_policy.setVerticalStretch(0)

        font.setPointSize(18)

        self.console_textBrowser = QtWidgets.QTextBrowser(self.central_widget)
        self.console_textBrowser.setReadOnly(True)
        self.console_textBrowser.setSizePolicy(size_policy)
        self.console_textBrowser.setOpenExternalLinks(True)
        self.console_textBrowser.setFont(font)

        self.gridLayout.addWidget(self.arduino_pushButton, 4, 1, 1, 1)
        self.gridLayout.addWidget(self.cameras_pushButton, 5, 1, 1, 1)
        self.gridLayout.addWidget(self.placas_pushButton, 6, 1, 1, 1)
        self.gridLayout.addWidget(self.cadastro_pushButton, 7, 1, 1, 1)
        self.gridLayout.addWidget(self.verify_pushButton, 8, 1, 1, 1)
        self.gridLayout.addWidget(self.cleanLog_pushButton, 9, 1, 1, 1)
        self.gridLayout.addWidget(self.scrolling_pushButton, 10, 1, 1, 1)

        self.gridLayout.addWidget(self.start_pushButton, 4, 2, 7, 1)

        self.gridLayout.addWidget(self.console_textBrowser, 4, 0, 7, 1)

        self.central_layout.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.setCentralWidget(self.central_widget)

        self.insert_title()
        self.console_textBrowser.setTextInteractionFlags(Qt.LinksAccessibleByMouse)

        # MainWindow children
        self.arduino_window = ArduinoWindow(self)

        self.showMaximized()
        self.connect_functions()

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == 16777274:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

    def connect_functions(self):
        self.start_pushButton.clicked.connect(self.run_inspection)
        self.cleanLog_pushButton.clicked.connect(self.clear_text_edit)
        self.arduino_pushButton.clicked.connect(self.show_arduino)

    def run_inspection(self):
        if self.arduino_window.status:
            if self.program_started is False:
                self.program_started = True
                self.console_textBrowser.insertHtml(c_log.manually_starting_inspection)
                self.start_pushButton.setStyleSheet("background-color: rgb(255, 134, 32);\n"
                                                    "color: rgb(255, 255, 255);")
                self.start_pushButton.setText('PARAR')

                self.core_process = Process(target=inspection, args=(self.console_queue, None))
                self.core_process.daemon = True
                self.core_process.start()

                self.queue_reader = Thread(target=self.console_reader)
                self.queue_reader.start()

                self.toggle_buttons(False, [self.scrolling_pushButton, self.start_pushButton, self.cleanLog_pushButton])

            else:
                self.program_started = False
                self.queue_reader.join()

                self.core_process.terminate()
                self.core_process.join()

                self.start_pushButton.setStyleSheet("background-color: rgb(64, 134, 32);\n"
                                                    "color: rgb(255, 255, 255);")
                self.start_pushButton.setText('INICIAR')
                self.toggle_buttons(True)

                self.console_textBrowser.insertHtml(c_log.manually_stopping_inspection)

    def console_reader(self):
        while self.program_started:
            if self.console_queue.empty() is False:
                self.console_textBrowser.append(self.console_queue.get().format(self.calha_nome))
                self.console_scrolling()

            time.sleep(0.3)

    def console_scrolling(self):
        if self.scrolling_pushButton.isChecked():
            self.console_textBrowser.moveCursor(QtGui.QTextCursor.End)

    def toggle_buttons(self, action, let_enabled=None):
        self.arduino_pushButton.setEnabled(action)
        self.cameras_pushButton.setEnabled(action)
        self.placas_pushButton.setEnabled(action)
        self.cadastro_pushButton.setEnabled(action)
        self.cleanLog_pushButton.setEnabled(action)
        self.scrolling_pushButton.setEnabled(action)
        self.start_pushButton.setEnabled(action)
        self.verify_pushButton.setEnabled(action)

        if let_enabled is not None:
            if type(let_enabled) == list:
                for button in let_enabled:
                    button.setEnabled(True)
            else:
                let_enabled.setEnabled(True)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.core_process is not None:
            if self.core_process.is_alive():
                self.core_process.terminate()
                self.core_process.join()

    def clear_text_edit(self):
        msg_box = MsgBox(f'AOI {self.calha_nome}', 'Deseja apagar o console?',
                         (QMessageBox.Ok | QMessageBox.Cancel), QMessageBox.Information)
        return_value = msg_box.exec_()

        if return_value == QMessageBox.Ok:
            self.console_textBrowser.clear()
            self.insert_title()

    def insert_title(self):
        self.console_textBrowser.insertHtml(c_log.main_window_title.format(self.calha_nome))

    def show_arduino(self):
        self.arduino_window.show()


class MsgBox(QMessageBox):
    def __init__(self, name, text, buttons, icon):
        super(MsgBox, self).__init__()
        self.setWindowTitle(name)
        self.setWindowIcon(QIcon('icon_simnext.png'))
        self.setIcon(icon)
        self.setText(text)
        self.setStandardButtons(buttons)


class ArduinoWindow(QtWidgets.QWidget):
    def __init__(self, parent: MainWindow):
        super(ArduinoWindow, self).__init__()
        self.status = True
        self.interacted = False
        # MainWindow -> self.mw is how the child window get access to the parent window
        self.mw = parent

        self.ini_inputs, self.ini_outputs = get_ports_from_json(self.mw.console_textBrowser)
        self.mw.console_scrolling()

        self.com, self.board = None, None
        self.sensors, self.digital_ports = {}, {}

        self.analog_input_reading_window = None
        self.digital_input_reading_window = None

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

        self.setWindowIcon(QIcon('icon_simnext.png'))
        self.setWindowTitle('Configurações')
        self.setFixedSize(415, 620)

        self.central_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout = QtWidgets.QVBoxLayout()

        font = QtGui.QFont()
        font.setPointSize(11)

        self.groupBox = QtWidgets.QGroupBox(self)
        self.groupBox.setTitle('Configurações do Arduino')
        self.groupBox.setFont(font)
        self.groupBox_layout = QtWidgets.QGridLayout(self.groupBox)

        self.porta_label = QtWidgets.QLabel(self.groupBox)
        self.porta_label.setText('Porta do Arduino:')
        self.porta_label.setFont(font)

        self.com_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.com_lineEdit.setFont(font)
        self.com_lineEdit.setAlignment(Qt.AlignCenter)
        size_policy.setHorizontalStretch(4)
        self.com_lineEdit.setSizePolicy(size_policy)
        self.com_lineEdit.setReadOnly(True)

        self.connect_pushButton = QtWidgets.QPushButton(self.groupBox)
        size_policy.setHorizontalStretch(3)
        self.connect_pushButton.setSizePolicy(size_policy)
        self.connect_pushButton.setText('Conectar')
        self.connect_pushButton.setFont(font)

        self.groupBox_layout.addWidget(self.porta_label, 0, 0, 1, 1)
        self.groupBox_layout.addWidget(self.com_lineEdit, 0, 1, 1, 1)
        self.groupBox_layout.addWidget(self.connect_pushButton, 0, 2, 1, 1)

        self.inp_out_tabWidget = QtWidgets.QTabWidget(self.groupBox)
        self.inp_out_tabWidget.setEnabled(False)
        self.inp_out_tabWidget.setFont(font)

        self.inp_tab = QtWidgets.QWidget()
        self.inp_tab_layout = QtWidgets.QGridLayout(self.inp_tab)

        self.simulate_pushButton = QtWidgets.QPushButton(self.inp_tab)
        self.simulate_pushButton.setText('Simular ativação')
        self.inp_tab_layout.addWidget(self.simulate_pushButton, 0, 0, 1, 1)

        self.digitalInputs_pushButton = QtWidgets.QPushButton(self.inp_tab)
        self.digitalInputs_pushButton.setText('Entradas digitais')
        self.inp_tab_layout.addWidget(self.digitalInputs_pushButton, 0, 1, 1, 1)

        if self._no_digital_inputs_active():
            self.mw.console_textBrowser.insertHtml(c_log.no_digital_inputs_active)
            self.digitalInputs_pushButton.setEnabled(False)

        self.inp_tab_frame = QtWidgets.QFrame()
        self.inp_tab_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.inp_tab_frame_layout = QtWidgets.QGridLayout(self.inp_tab_frame)

        # parâmetros do primeiro sensor [sensor_1]
        self.sens1_checkBox = QtWidgets.QCheckBox(self.inp_tab_frame)
        self.sens1_lineEdit = QtWidgets.QLineEdit(self.inp_tab_frame)
        self.sens1_comboBox = QtWidgets.QComboBox(self.inp_tab_frame)
        self.sens1_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.inp_tab_frame)

        self.inp_tab_frame_layout.addWidget(self.sens1_checkBox, 0, 1, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens1_lineEdit, 0, 2, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens1_comboBox, 0, 3, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens1_doubleSpinBox, 0, 4, 1, 1)

        # parâmetros do segundo sensor [sensor_2]
        self.sens2_checkBox = QtWidgets.QCheckBox(self.inp_tab_frame)
        self.sens2_lineEdit = QtWidgets.QLineEdit(self.inp_tab_frame)
        self.sens2_comboBox = QtWidgets.QComboBox(self.inp_tab_frame)
        self.sens2_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.inp_tab_frame)

        self.inp_tab_frame_layout.addWidget(self.sens2_checkBox, 1, 1, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens2_lineEdit, 1, 2, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens2_comboBox, 1, 3, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens2_doubleSpinBox, 1, 4, 1, 1)

        # parâmetros do terceiro sensor [sensor_3]
        self.sens3_checkBox = QtWidgets.QCheckBox(self.inp_tab_frame)
        self.sens3_lineEdit = QtWidgets.QLineEdit(self.inp_tab_frame)
        self.sens3_comboBox = QtWidgets.QComboBox(self.inp_tab_frame)
        self.sens3_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.inp_tab_frame)

        self.inp_tab_frame_layout.addWidget(self.sens3_checkBox, 2, 1, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens3_lineEdit, 2, 2, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens3_comboBox, 2, 3, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens3_doubleSpinBox, 2, 4, 1, 1)

        self.inp_tab_layout.addWidget(self.inp_tab_frame, 1, 0, 1, 2)

        self.construct_inputs()
        self.set_inputs()
        self.prevent_no_sensors()

        self.inp_out_tabWidget.addTab(self.inp_tab, 'Entradas')

        self.out_tab = QtWidgets.QWidget()
        self.out_tab_layout = QtWidgets.QGridLayout(self.out_tab)

        self.out_tab_frame = QtWidgets.QFrame()
        self.out_tab_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.out_tab_frame_layout = QtWidgets.QGridLayout(self.out_tab_frame)

        self.inverter_checkBox = QtWidgets.QCheckBox(self.out_tab_frame)
        self.inverter_lineEdit = QtWidgets.QLineEdit(self.out_tab_frame)
        self.inverter_pushButton = QtWidgets.QPushButton(self.out_tab_frame)

        self.out_tab_frame_layout.addWidget(self.inverter_checkBox, 0, 1, 1, 1)
        self.out_tab_frame_layout.addWidget(self.inverter_lineEdit, 0, 2, 1, 1)
        self.out_tab_frame_layout.addWidget(self.inverter_pushButton, 0, 3, 1, 1)

        self.lights_checkBox = QtWidgets.QCheckBox(self.out_tab_frame)
        self.lights_lineEdit = QtWidgets.QLineEdit(self.out_tab_frame)
        self.lights_pushButton = QtWidgets.QPushButton(self.out_tab_frame)

        self.out_tab_frame_layout.addWidget(self.lights_checkBox, 1, 1, 1, 1)
        self.out_tab_frame_layout.addWidget(self.lights_lineEdit, 1, 2, 1, 1)
        self.out_tab_frame_layout.addWidget(self.lights_pushButton, 1, 3, 1, 1)

        self.valve1_checkBox = QtWidgets.QCheckBox(self.out_tab_frame)
        self.valve1_lineEdit = QtWidgets.QLineEdit(self.out_tab_frame)
        self.valve1_pushButton = QtWidgets.QPushButton(self.out_tab_frame)

        self.out_tab_frame_layout.addWidget(self.valve1_checkBox, 2, 1, 1, 1)
        self.out_tab_frame_layout.addWidget(self.valve1_lineEdit, 2, 2, 1, 1)
        self.out_tab_frame_layout.addWidget(self.valve1_pushButton, 2, 3, 1, 1)

        self.valve2_checkBox = QtWidgets.QCheckBox(self.out_tab_frame)
        self.valve2_lineEdit = QtWidgets.QLineEdit(self.out_tab_frame)
        self.valve2_pushButton = QtWidgets.QPushButton(self.out_tab_frame)

        self.out_tab_frame_layout.addWidget(self.valve2_checkBox, 3, 1, 1, 1)
        self.out_tab_frame_layout.addWidget(self.valve2_lineEdit, 3, 2, 1, 1)
        self.out_tab_frame_layout.addWidget(self.valve2_pushButton, 3, 3, 1, 1)

        self.emergency_checkBox = QtWidgets.QCheckBox(self.out_tab_frame)
        self.emergency_lineEdit = QtWidgets.QLineEdit(self.out_tab_frame)
        self.emergency_pushButton = QtWidgets.QPushButton(self.out_tab_frame)

        self.out_tab_frame_layout.addWidget(self.emergency_checkBox, 4, 1, 1, 1)
        self.out_tab_frame_layout.addWidget(self.emergency_lineEdit, 4, 2, 1, 1)
        self.out_tab_frame_layout.addWidget(self.emergency_pushButton, 4, 3, 1, 1)

        self.buzzer_checkBox = QtWidgets.QCheckBox(self.out_tab_frame)
        self.buzzer_lineEdit = QtWidgets.QLineEdit(self.out_tab_frame)
        self.buzzer_pushButton = QtWidgets.QPushButton(self.out_tab_frame)

        self.out_tab_frame_layout.addWidget(self.buzzer_checkBox, 5, 1, 1, 1)
        self.out_tab_frame_layout.addWidget(self.buzzer_lineEdit, 5, 2, 1, 1)
        self.out_tab_frame_layout.addWidget(self.buzzer_pushButton, 5, 3, 1, 1)

        self.out_tab_layout.addWidget(self.out_tab_frame, 1, 0, 1, 2)

        self.construct_outputs()
        self.set_outputs()

        self.inp_out_tabWidget.addTab(self.out_tab, 'Saídas')

        self.confirm_pushButton = QtWidgets.QPushButton(self.groupBox)
        self.confirm_pushButton.setEnabled(False)
        self.confirm_pushButton.setText('Validar configurações')
        self.confirm_pushButton.setFont(font)

        self.groupBox_layout.addWidget(self.confirm_pushButton, 2, 0, 1, 3)
        self.groupBox_layout.addWidget(self.inp_out_tabWidget, 1, 0, 1, 3)

        self.main_layout.addWidget(self.groupBox)
        self.central_layout.addLayout(self.main_layout)

        self.connect_functions()
        self.connection_attempt()

    def connect_functions(self):
        self.connect_pushButton.clicked.connect(self.connection_attempt)
        self.simulate_pushButton.clicked.connect(self.activation_test)

        self.sens1_checkBox.clicked.connect(lambda: self.toggle_state('sensor_1'))
        self.sens2_checkBox.clicked.connect(lambda: self.toggle_state('sensor_2'))
        self.sens3_checkBox.clicked.connect(lambda: self.toggle_state('sensor_3'))

        self.inverter_checkBox.clicked.connect(lambda: self.toggle_state('inverter'))
        self.buzzer_checkBox.clicked.connect(lambda: self.toggle_state('buzzer'))
        self.lights_checkBox.clicked.connect(lambda: self.toggle_state('lights'))
        self.valve1_checkBox.clicked.connect(lambda: self.toggle_state('valve_1'))
        self.valve2_checkBox.clicked.connect(lambda: self.toggle_state('valve_2'))
        self.emergency_checkBox.clicked.connect(lambda: self.toggle_state('emergency'))

        self.digitalInputs_pushButton.clicked.connect(self.reading_test)

    def _no_digital_inputs_active(self, just_checking=True):
        digital_inputs, none_active = {}, True

        digital = self.ini_inputs.get('digital_1')
        if digital is not None:
            digital_inputs['digital_1'] = digital
            none_active = False

        digital = self.ini_inputs.get('digital_2')
        if digital is not None:
            digital_inputs['digital_2'] = digital
            none_active = False

        return none_active if just_checking else digital_inputs

    def toggle_state(self, key):
        self.interacted = True
        # it toggles all the key widgets to on/off when called
        if key.startswith('sensor'):
            if self.sensors[key] is False:
                # if value is False, it means the sensor's checkbox is not checked,
                # thus it's widgets are disabled, here they'll be enabled
                self.toggle_widgets_state(key, enabled=True)
                self.simulate_pushButton.setEnabled(True)
                self.confirm_pushButton.setEnabled(True)
            else:
                self.toggle_widgets_state(key, enabled=False)

            self.prevent_no_sensors()
        else:
            if self.digital_ports[key] is False:
                self.toggle_widgets_state(key, enabled=True)
            else:
                self.toggle_widgets_state(key, enabled=False)

    def prevent_no_sensors(self):
        # if there's only one sensor left, it won't be allowed to be disabled also
        actives = [sensor for sensor, active in self.sensors.items() if active is True]
        if len(actives) == 1:
            active = actives[0]
            if active == 'sensor_1':
                self.sens1_checkBox.setEnabled(False)
            elif active == 'sensor_2':
                self.sens2_checkBox.setEnabled(False)
            else:
                self.sens3_checkBox.setEnabled(False)
        else:
            self.sens1_checkBox.setEnabled(True)
            self.sens2_checkBox.setEnabled(True)
            self.sens3_checkBox.setEnabled(True)

    def construct_inputs(self):
        self.sens1_lineEdit.setText('sensor_1')
        self.sens1_lineEdit.setAlignment(Qt.AlignCenter)
        self.sens1_lineEdit.setReadOnly(True)

        self.sens1_doubleSpinBox.setDecimals(4)
        self.sens1_doubleSpinBox.setMaximum(1.0)
        self.sens1_doubleSpinBox.setSingleStep(0.025)

        self.sens2_lineEdit.setText('sensor_2')
        self.sens2_lineEdit.setAlignment(Qt.AlignCenter)
        self.sens2_lineEdit.setReadOnly(True)

        self.sens2_doubleSpinBox.setDecimals(4)
        self.sens2_doubleSpinBox.setMaximum(1.0)
        self.sens2_doubleSpinBox.setSingleStep(0.025)

        self.sens3_lineEdit.setText('sensor_3')
        self.sens3_lineEdit.setAlignment(Qt.AlignCenter)
        self.sens3_lineEdit.setReadOnly(True)

        self.sens3_doubleSpinBox.setDecimals(4)
        self.sens3_doubleSpinBox.setMaximum(1.0)
        self.sens3_doubleSpinBox.setSingleStep(0.025)

        for operator, function in get_opr().items():
            self.sens1_comboBox.addItem(operator, function)
            self.sens2_comboBox.addItem(operator, function)
            self.sens3_comboBox.addItem(operator, function)

    def set_inputs(self):
        non_actives = ['sensor_1', 'sensor_2', 'sensor_3']
        for key, params in self.ini_inputs.items():
            if key in non_actives:
                _, (_, opr, value) = params
                if key == 'sensor_1':
                    self.sens1_checkBox.setChecked(True)
                    self.sens1_comboBox.setCurrentText(opr)
                    self.sens1_doubleSpinBox.setValue(value)

                elif key == 'sensor_2':
                    self.sens2_checkBox.setChecked(True)
                    self.sens2_comboBox.setCurrentText(opr)
                    self.sens2_doubleSpinBox.setValue(value)

                elif key == 'sensor_3':
                    self.sens3_checkBox.setChecked(True)
                    self.sens3_comboBox.setCurrentText(opr)
                    self.sens3_doubleSpinBox.setValue(value)
                self.sensors[key] = True
                non_actives.remove(key)

        for non_active in non_actives:
            self.toggle_widgets_state(non_active, enabled=False)

    def toggle_widgets_state(self, key, enabled):
        if key == 'sensor_1':
            self.sens1_lineEdit.setEnabled(enabled)
            self.sens1_comboBox.setEnabled(enabled)
            self.sens1_doubleSpinBox.setEnabled(enabled)
            self.sensors[key] = enabled

        elif key == 'sensor_2':
            self.sens2_lineEdit.setEnabled(enabled)
            self.sens2_comboBox.setEnabled(enabled)
            self.sens2_doubleSpinBox.setEnabled(enabled)
            self.sensors[key] = enabled

        elif key == 'sensor_3':
            self.sens3_lineEdit.setEnabled(enabled)
            self.sens3_comboBox.setEnabled(enabled)
            self.sens3_doubleSpinBox.setEnabled(enabled)
            self.sensors[key] = enabled

        elif key == 'inverter':
            self.inverter_lineEdit.setEnabled(enabled)
            self.inverter_pushButton.setEnabled(enabled)
            self.digital_ports[key] = enabled
            if self.inverter_pushButton.isChecked():
                self.inverter_pushButton.toggle()

        elif key == 'lights':
            self.lights_lineEdit.setEnabled(enabled)
            self.lights_pushButton.setEnabled(enabled)
            self.digital_ports[key] = enabled
            if self.lights_pushButton.isChecked():
                self.lights_pushButton.toggle()

        elif key == 'valve_1':
            self.valve1_lineEdit.setEnabled(enabled)
            self.valve1_pushButton.setEnabled(enabled)
            self.digital_ports[key] = enabled
            if self.valve1_pushButton.isChecked():
                self.valve1_pushButton.toggle()

        elif key == 'valve_2':
            self.valve2_lineEdit.setEnabled(enabled)
            self.valve2_pushButton.setEnabled(enabled)
            self.digital_ports[key] = enabled
            if self.valve2_pushButton.isChecked():
                self.valve2_pushButton.toggle()

        elif key == 'emergency':
            self.emergency_lineEdit.setEnabled(enabled)
            self.emergency_pushButton.setEnabled(enabled)
            self.digital_ports[key] = enabled
            if self.emergency_pushButton.isChecked():
                self.emergency_pushButton.toggle()

        elif key == 'buzzer':
            self.buzzer_lineEdit.setEnabled(enabled)
            self.buzzer_pushButton.setEnabled(enabled)
            self.digital_ports[key] = enabled

    def construct_outputs(self):
        default_output_ports = defaults('OUTPUTS')

        self.inverter_lineEdit.setText('inverter')
        self.inverter_lineEdit.setAlignment(Qt.AlignCenter)
        self.inverter_lineEdit.setReadOnly(True)

        self.inverter_pushButton.setText('LOW')
        self.inverter_pushButton.setCheckable(True)
        self.inverter_pushButton.toggled.connect(lambda: self.toggle_output(default_output_ports['inverter'],
                                                                            self.inverter_pushButton))
        self.lights_lineEdit.setText('lights')
        self.lights_lineEdit.setAlignment(Qt.AlignCenter)
        self.lights_lineEdit.setReadOnly(True)

        self.lights_pushButton.setText('LOW')
        self.lights_pushButton.setCheckable(True)
        self.lights_pushButton.toggled.connect(lambda: self.toggle_output(default_output_ports['lights'],
                                                                          self.lights_pushButton))
        self.valve1_lineEdit.setText('valve_1')
        self.valve1_lineEdit.setAlignment(Qt.AlignCenter)
        self.valve1_lineEdit.setReadOnly(True)

        self.valve1_pushButton.setText('LOW')
        self.valve1_pushButton.setCheckable(True)
        self.valve1_pushButton.toggled.connect(lambda: self.toggle_output(default_output_ports['valve_1'],
                                                                          self.valve1_pushButton))
        self.valve2_lineEdit.setText('valve_2')
        self.valve2_lineEdit.setAlignment(Qt.AlignCenter)
        self.valve2_lineEdit.setReadOnly(True)

        self.valve2_pushButton.setText('LOW')
        self.valve2_pushButton.setCheckable(True)
        self.valve2_pushButton.toggled.connect(lambda: self.toggle_output(default_output_ports['valve_2'],
                                                                          self.valve2_pushButton))
        self.emergency_lineEdit.setText('emergency')
        self.emergency_lineEdit.setAlignment(Qt.AlignCenter)
        self.emergency_lineEdit.setReadOnly(True)

        self.emergency_pushButton.setText('LOW')
        self.emergency_pushButton.setCheckable(True)
        self.emergency_pushButton.toggled.connect(lambda: self.toggle_output(default_output_ports['emergency'],
                                                                             self.emergency_pushButton))
        self.buzzer_lineEdit.setText('buzzer')
        self.buzzer_lineEdit.setAlignment(Qt.AlignCenter)
        self.buzzer_lineEdit.setReadOnly(True)

        self.buzzer_pushButton.setText('BEEP')

    def set_outputs(self):
        non_actives = list(defaults('OUTPUTS'))
        for key, port in self.ini_outputs.items():
            if key in non_actives:
                if key == 'inverter':
                    self.inverter_checkBox.setChecked(True)
                elif key == 'lights':
                    self.lights_checkBox.setChecked(True)
                elif key == 'valve_1':
                    self.valve1_checkBox.setChecked(True)
                elif key == 'valve_2':
                    self.valve2_checkBox.setChecked(True)
                elif key == 'emergency':
                    self.emergency_checkBox.setChecked(True)
                elif key == 'buzzer':
                    self.buzzer_checkBox.setChecked(True)

                self.digital_ports[key] = True
                non_actives.remove(key)

        for non_active in non_actives:
            self.toggle_widgets_state(non_active, enabled=False)

    def toggle_if_active(self):
        if self.inverter_pushButton.isChecked():
            self.inverter_pushButton.toggle()

        if self.lights_pushButton.isChecked():
            self.lights_pushButton.toggle()

        if self.valve1_pushButton.isChecked():
            self.valve1_pushButton.toggle()

        if self.valve2_pushButton.isChecked():
            self.valve2_pushButton.toggle()

        if self.emergency_pushButton.isChecked():
            self.emergency_pushButton.toggle()

    def toggle_output(self, port, pushButton):
        if pushButton.isChecked():
            self.board.digital[port].write(1)
            pushButton.setText('HIGH')
        else:
            self.board.digital[port].write(0)
            pushButton.setText('LOW')

    def connection_attempt(self):
        self.com = get_port_connection(self.mw.console_textBrowser)
        self.mw.console_scrolling()

        self.com_lineEdit.setText(self.com)
        if 'COM' not in self.com:  # check if COM is now connected
            self.status = False
            self.mw.start_pushButton.hide()

        else:
            if self.status is False:
                self.status = True
                self.mw.start_pushButton.show()

            if self.board is None:
                self.board = ArduinoNano(self.com)

                util.Iterator(self.board).start()
                time.sleep(0.2)

                self.mw.start_pushButton.setHidden(False)
                self.connect_pushButton.setText('Desconectar')

                self.inverter_pushButton.toggle()
                self.lights_pushButton.toggle()

                self.inp_out_tabWidget.setEnabled(True)
                self.confirm_pushButton.setEnabled(True)

            else:
                self.mw.start_pushButton.hide()
                self.toggle_if_active()
                self.board.exit()
                self.board = None
                self.com_lineEdit.setText('Não conectado')
                self.connect_pushButton.setText('Conectar')
                self.inp_out_tabWidget.setEnabled(False)
                self.confirm_pushButton.setEnabled(False)

    def activation_test(self):
        self.analog_input_reading_window = AnalogReadingSimulation(self.board)
        self.analog_input_reading_window.initialize(self.generate_input_configs())
        self.analog_input_reading_window.show()

    def reading_test(self):
        self.digital_input_reading_window = DigitalReadingSimulation(self.board)
        self.digital_input_reading_window.initialize()
        self.digital_input_reading_window.show()

    def get_trigger_function(self):
        return {sensor: generate_trigger_function(trigger)
                for sensor, trigger in self.generate_input_configs().items()}

    def generate_input_configs(self):
        input_configs = {}
        default_input_ports = defaults('INPUTS')
        for port in self.sensors:
            if self.sensors[port]:
                if port == 'sensor_1':
                    func, opr, value = self.sens1_comboBox.currentData(), self.sens1_comboBox.currentText(), \
                                       self.sens1_doubleSpinBox.value()
                elif port == 'sensor_2':
                    func, opr, value = self.sens2_comboBox.currentData(), self.sens2_comboBox.currentText(), \
                                       self.sens2_doubleSpinBox.value()
                else:
                    func, opr, value = self.sens3_comboBox.currentData(), self.sens3_comboBox.currentText(), \
                                       self.sens3_doubleSpinBox.value()

                input_configs[port] = (self.board.get_pin(default_input_ports[port]).read, func, opr, value)
        return input_configs

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.interacted:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle('Configurações')
            msg_box.setText('Deseja sair sem validar as configurações?')

            msg_box.addButton('Salvar', QMessageBox.NoRole)
            msg_box.addButton('Cancelar', QMessageBox.ApplyRole)
            msg_box.addButton('Sair', QMessageBox.RejectRole)

            reply = msg_box.exec_()

            if reply == 0:
                self.interacted = False
                self.confirm_pushButton.click()
            elif reply == 1:
                a0.ignore()



class AnalogReadingSimulation(QtWidgets.QWidget):
    def __init__(self, board):
        super(AnalogReadingSimulation, self).__init__()
        self.board = board

        self._input_widgets = {}
        self._triggers = {}

        self.setWindowTitle('Simulação')
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.setWindowIcon(QIcon('icon_simnext.png'))

        self.central_layout = QtWidgets.QGridLayout(self)

        self.finish_pushButton = QtWidgets.QPushButton(self)
        self.finish_pushButton.clicked.connect(self.close)
        self.finish_pushButton.setText('Finalizar simulação')

        self.keep_reading = True

    def initialize(self, inputs):
        self._triggers = {sensor: generate_trigger_function(inputs[sensor], True) for sensor in inputs}
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        font = QtGui.QFont()

        c = 0
        for i, sensor in enumerate(self._triggers):
            lineEdit_name = QtWidgets.QLineEdit(self)
            font.setPointSize(9)
            lineEdit_name.setText(sensor)
            lineEdit_name.setFont(font)
            lineEdit_name.setAlignment(Qt.AlignCenter)
            size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
            lineEdit_name.setSizePolicy(size_policy)
            lineEdit_name.setReadOnly(True)

            lineEdit_value = QtWidgets.QLineEdit(self)
            font.setPointSize(11)
            lineEdit_value.setFont(font)
            lineEdit_value.setAlignment(Qt.AlignCenter)
            size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Fixed)
            lineEdit_value.setSizePolicy(size_policy)
            lineEdit_value.setReadOnly(True)

            self._input_widgets[sensor] = Thread(target=self._reader,
                                                 args=(lineEdit_name, inputs[sensor][0], lineEdit_value,
                                                       self._triggers[sensor]))

            self.central_layout.addWidget(lineEdit_name, 0, c, 1, 1)
            self.central_layout.addWidget(lineEdit_value, 1, c, 1, 1)
            c += 1

        self.central_layout.addWidget(self.finish_pushButton, 2, 0, 1, c)

        font.setPointSize(10)
        self.finish_pushButton.setFont(font)
        self._resize_accordingly()

        for thread in self._input_widgets.values():
            thread.start()

    def _reader(self, sensor_name, reader, sensor_value, trigger_func):
        # TODO: Try to create a C function for better reading performance.
        current_sensor = sensor_name.text()
        reading = False
        for _ in range(6):
            try:
                trigger_func()
            except TypeError:
                pass
            else:
                reading = True
                break

        if not reading:
            sensor_value.setText("retornou nulo!")

        else:
            loadings = ('-----', '----', '---', '--', '-')
            i, loadings_amount = 0, len(loadings) - 1

            while self.keep_reading:
                sensor_name.setText(f'{loadings[i]} {current_sensor} {loadings[i]}')
                sensor_value.setText(f'{reader():.4f}')

                if trigger_func():
                    sensor_name.setText(f'O {current_sensor} O')
                    time.sleep(2)

                i = 0 if i == loadings_amount else 1 + i
                time.sleep(0.03)

    def _resize_accordingly(self):
        sensors = len(self._input_widgets)
        if sensors == 1:
            self.resize(200, 238)
        elif sensors == 2:
            self.resize(317, 238)
        else:
            self.resize(423, 238)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.keep_reading:
            self.exit()

    def exit(self):
        self.board.taken['analog'] = clean_up_pins()
        self.keep_reading = False

        self._input_widgets = {}
        self._triggers = {}

        for thread in self._input_widgets.values():
            thread.join()
        self.close()


class DigitalReadingSimulation(QtWidgets.QWidget):
    def __init__(self, board):
        super(DigitalReadingSimulation, self).__init__()
        self.board = board

        self.setWindowTitle('Simulação')
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.setWindowIcon(QIcon('icon_simnext.png'))

        self.central_layout = QtWidgets.QGridLayout(self)

        self.finish_pushButton = QtWidgets.QPushButton(self)
        self.finish_pushButton.clicked.connect(self.close)
        self.finish_pushButton.setText('Finalizar simulação')

    def initialize(self):
        pass


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    root = MainWindow()
    root.show()
    sys.exit(app.exec_())
