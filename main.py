import json
import os
import time

from configparser import ConfigParser
from pyfirmata import ArduinoNano, util

from multiprocessing import Process, SimpleQueue
from threading import Thread

from console_log import manually_starting_inspection, manually_stopping_inspection, \
    main_window_title, no_digital_inputs_active

from connections import clean_up_pins
from ini_files import ArduinoIni, get_opr, defaults
from trigger import generate_trigger_function
from core import inspection

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox


# TODO: MOVE THIS FUNCTION TO THE ini_files.py MODULE.
def get_ini_configs():
    config = ConfigParser()
    file = 'settings/configs.ini'
    config.read(file)

    if len(config.sections()) == 0:
        config.add_section('GERAIS')
        print('_-_-_ Configurações iniciais da AOI -_-_-_')

        users = False if os.path.exists('settings/users.json') else None
        while 1:
            calha = input('\nDigite o nome da linha de produção: ').strip().upper()

            if users is None:
                admin = input('Digite seu nome de administrador: ').strip().upper()
                admin_id = int(input('Passe seu crachá: '))
                users = {'users': [{'name': admin, 'id': str(admin_id), 'editor': True, 'operator': True}]}

            stop_secs = float(input('Digite o tempo de parada do pino: '))

            done = input('Digite 1 para confirmar as configurações: ')

            if done == '1':
                if calha != '' and stop_secs <= 2.5:
                    break
                else:
                    print('Configurações inválidas!')

            print('Por favor, digite novamente as configurações!')

        config.set('GERAIS', 'NOME', calha)
        config.set('GERAIS', 'PARADA', str(stop_secs))

        if os.path.exists('settings') is False:
            os.mkdir('settings')

        with open(file, 'w+') as config_file:
            config.write(config_file)

        with open('settings/users.json', 'w+') as user_file:
            json.dump(users, user_file, indent=3)

        print('Configuração concluída!\n')
        return config['GERAIS']['NOME']

    return config['GERAIS']['NOME']


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.core_process, self.queue_reader = None, None
        self.program_started = False
        self.console_queue = SimpleQueue()

        self.calha_nome = get_ini_configs()
        self.setWindowIcon(QIcon('icon_simnext.png'))
        self.setWindowTitle(f'AOI {self.calha_nome}')

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
        #TODO: REMOVE USER'S TEMPORARY NAME TAG ID AUTOMATICALLY.
        #TODO: CHECK FUNCTION IF THE NAME TAG READER IS CONNECTED.
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

        #MainWindow children
        self.arduino_window = ArduinoWindow(self)

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
                self.console_textBrowser.insertHtml(manually_starting_inspection)
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

                self.console_textBrowser.insertHtml(manually_stopping_inspection)

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
        self.console_textBrowser.insertHtml(main_window_title.format(self.calha_nome))

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

        self.mw = parent

        self.ini_inputs, self.ini_outputs = ArduinoIni.parameters(self.mw.console_textBrowser)
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
            self.mw.console_textBrowser.insertHtml(no_digital_inputs_active)
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

        self.inputs_frame_grid = QtWidgets.QGridLayout()
        self.inp_tab_frame_layout.addLayout(self.inputs_frame_grid, 0, 0, 1, 1)
        self.inp_tab_layout.addWidget(self.inp_tab_frame, 1, 0, 1, 2)

        self.construct_inputs()
        self.set_inputs()
        self.check_actives()

        self.inp_out_tabWidget.addTab(self.inp_tab, 'Entradas')

        self.out_tab = QtWidgets.QWidget()

        self.inverter_checkBox = QtWidgets.QCheckBox(self.out_tab)
        self.inverter_lineEdit = QtWidgets.QLineEdit(self.out_tab)
        self.inverter_lineEdit2 = QtWidgets.QLineEdit(self.out_tab)
        self.inverter_pushButton = QtWidgets.QPushButton(self.out_tab)

        self.lights_checkBox = QtWidgets.QCheckBox(self.out_tab)
        self.lights_lineEdit = QtWidgets.QLineEdit(self.out_tab)
        self.lights_lineEdit2 = QtWidgets.QLineEdit(self.out_tab)
        self.lights_pushButton = QtWidgets.QPushButton(self.out_tab)

        self.buzzer_checkBox = QtWidgets.QCheckBox(self.out_tab)
        self.buzzer_lineEdit = QtWidgets.QLineEdit(self.out_tab)
        self.buzzer_lineEdit2 = QtWidgets.QLineEdit(self.out_tab)
        self.buzzer_pushButton = QtWidgets.QPushButton(self.out_tab)

        self.valve1_checkBox = QtWidgets.QCheckBox(self.out_tab)
        self.valve1_lineEdit = QtWidgets.QLineEdit(self.out_tab)
        self.valve1_lineEdit2 = QtWidgets.QLineEdit(self.out_tab)
        self.valve1_pushButton = QtWidgets.QPushButton(self.out_tab)

        self.valve2_checkBox = QtWidgets.QCheckBox(self.out_tab)
        self.valve2_lineEdit = QtWidgets.QLineEdit(self.out_tab)
        self.valve2_lineEdit2 = QtWidgets.QLineEdit(self.out_tab)
        self.valve2_pushButton = QtWidgets.QPushButton(self.out_tab)

        self.emergency_checkBox = QtWidgets.QCheckBox(self.out_tab)
        self.emergency_lineEdit = QtWidgets.QLineEdit(self.out_tab)
        self.emergency_lineEdit2 = QtWidgets.QLineEdit(self.out_tab)
        self.emergency_pushButton = QtWidgets.QPushButton(self.out_tab)

        self.out_tab_layout = QtWidgets.QGridLayout(self.out_tab)

        self.inp_out_tabWidget.addTab(self.out_tab, 'Saídas')

        self.confirm_button = QtWidgets.QPushButton(self.groupBox)
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText('Validar configurações')
        self.confirm_button.setFont(font)

        self.groupBox_layout.addWidget(self.confirm_button, 2, 0, 1, 3)
        self.groupBox_layout.addWidget(self.inp_out_tabWidget, 1, 0, 1, 3)

        self.main_layout.addWidget(self.groupBox)
        self.central_layout.addLayout(self.main_layout)

        self.connect_functions()
        self.connection_attempt()

    def connect_functions(self):
        self.connect_pushButton.clicked.connect(self.connection_attempt)
        self.simulate_pushButton.clicked.connect(self.activation_test)

        self.sens1_checkBox.clicked.connect(lambda state: self.get_state('sensor_1'))
        self.sens2_checkBox.clicked.connect(lambda state: self.get_state('sensor_2'))
        self.sens3_checkBox.clicked.connect(lambda state: self.get_state('sensor_3'))

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

    def get_state(self, key):
        if self.sensors[key] is False:
            self.toggle_widgets_state(key, True)
            self.simulate_pushButton.setEnabled(True)
            self.confirm_button.setEnabled(True)
        else:
            self.toggle_widgets_state(key)

        self.check_actives()

    def check_actives(self):
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
        for port, params in self.ini_inputs.items():
            if port == 'sensor_1':
                self.sens1_checkBox.setChecked(True)
                self.sens1_comboBox.setCurrentText(params[1][1])
                self.sens1_doubleSpinBox.setValue(params[1][2])
                self.sensors['sensor_1'] = True
                non_actives.remove(port)

            elif port == 'sensor_2':
                self.sens2_checkBox.setChecked(True)
                self.sens2_comboBox.setCurrentText(params[1][1])
                self.sens2_doubleSpinBox.setValue(params[1][2])
                self.sensors['sensor_2'] = True
                non_actives.remove(port)

            elif port == 'sensor_3':
                self.sens3_checkBox.setChecked(True)
                self.sens3_comboBox.setCurrentText(params[1][1])
                self.sens3_doubleSpinBox.setValue(params[1][2])
                self.sensors['sensor_3'] = True
                non_actives.remove(port)

        for non_active in non_actives:
            self.toggle_widgets_state(non_active)

    def toggle_widgets_state(self, key, enabled=False):
        if key == 'sensor_1':
            self.sens1_lineEdit.setEnabled(enabled)
            self.sens1_comboBox.setEnabled(enabled)
            self.sens1_doubleSpinBox.setEnabled(enabled)

        elif key == 'sensor_2':
            self.sens2_lineEdit.setEnabled(enabled)
            self.sens2_comboBox.setEnabled(enabled)
            self.sens2_doubleSpinBox.setEnabled(enabled)

        elif key == 'sensor_3':
            self.sens3_lineEdit.setEnabled(enabled)
            self.sens3_comboBox.setEnabled(enabled)
            self.sens3_doubleSpinBox.setEnabled(enabled)

        self.sensors[key] = enabled

    def connection_attempt(self):
        self.com = ArduinoIni.port_connection(self.mw.console_textBrowser)
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

                self.connect_pushButton.setText('Desconectar')
                self.inp_out_tabWidget.setEnabled(True)
                self.confirm_button.setEnabled(True)

            else:
                self.board.exit()
                self.board = None
                self.com_lineEdit.setText('Não conectado')
                self.connect_pushButton.setText('Conectar')
                self.inp_out_tabWidget.setEnabled(False)
                self.confirm_button.setEnabled(False)

    def toggle_lights(self, toggle):
        pass

    def activation_test(self):
        self.analog_input_reading_window = AnalogReadingSimulation(self.board)
        self.analog_input_reading_window.initialize(self.generate_input_configs())
        self.analog_input_reading_window.show()

    def reading_test(self):
        self.digital_input_reading_window = DigitalReadingSimulation(self.board)
        self.digital_input_reading_window.initialize()
        self.digital_input_reading_window.show()

    # def active_valve(self):
    #     key = [key for key in self.ini_outputs if key.startswith('valve')]
    #     if len(key) == 2:
    #         warnings.warn(f'Multiple valves are active, utilizing {key[0]}.')
    #     return self.ini_outputs[key[0]]

    def return_trigger_function(self):
        return generate_trigger_function(self._generate_input_configs())[0]

    def generate_input_configs(self):
        input_configs = {}
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

                input_configs[port] = (self.board.get_pin(defaults('INPUTS', port)).read, func, opr, value)
        return input_configs


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
