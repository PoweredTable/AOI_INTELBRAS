import json
import os
import time

import serial.serialutil
from PyQt5 import QtCore, QtGui, QtWidgets
from configparser import ConfigParser
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from pyfirmata import Arduino, util

from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QSizePolicy

from core import inspection
from multiprocessing import Process, SimpleQueue
from threading import Thread


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
                users = {'users': [{'name': admin, 'id': str(admin_id), 'editor': True}]}

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
        self.setWindowIcon(QIcon('icon_simnext.png'))
        self.calha_nome = get_ini_configs()

        self.second_window = None

        self.setWindowTitle(f'AOI GUI {self.calha_nome}')

        self.central_widget = QtWidgets.QWidget()
        self.gridLayout_2 = QtWidgets.QGridLayout(self.central_widget)
        self.gridLayout = QtWidgets.QGridLayout()

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        size_policy.setHorizontalStretch(0)
        size_policy.setVerticalStretch(0)

        font = QtGui.QFont()
        font.setPointSize(14)

        self.arduino_button = QtWidgets.QPushButton(self.central_widget)
        self.arduino_button.setSizePolicy(size_policy)
        self.arduino_button.setFont(font)

        self.cameras_button = QtWidgets.QPushButton(self.central_widget)
        self.cameras_button.setSizePolicy(size_policy)
        size_policy.setHorizontalStretch(0)
        self.cameras_button.setFont(font)

        self.webcam_button = QtWidgets.QPushButton(self.central_widget)
        self.webcam_button.setSizePolicy(size_policy)
        self.webcam_button.setFont(font)

        self.start_program = QtWidgets.QPushButton(self.central_widget)
        size_policy.setHorizontalStretch(1)
        self.start_program.setSizePolicy(size_policy)
        self.start_program.setFont(font)

        self.placas_button = QtWidgets.QPushButton(self.central_widget)
        self.placas_button.setSizePolicy(size_policy)
        self.placas_button.setFont(font)
        self.gridLayout.addWidget(self.placas_button, 7, 1, 1, 1)

        self.cadastro_button = QtWidgets.QPushButton(self.central_widget)
        self.cadastro_button.setSizePolicy(size_policy)
        self.cadastro_button.setFont(font)

        self.clean_log_button = QtWidgets.QPushButton(self.central_widget)

        font.setPointSize(10)
        self.clean_log_button.setFont(font)

        self.console_textEdit = QtWidgets.QTextEdit(self.central_widget)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(5)
        size_policy.setVerticalStretch(0)
        self.console_textEdit.setSizePolicy(size_policy)

        font.setPointSize(18)
        self.console_textEdit.setFont(font)

        self.scrolling_button = QtWidgets.QPushButton(self.central_widget)
        self.scrolling_button.setCheckable(True)
        self.scrolling_button.setChecked(True)

        self.debugging_button = QtWidgets.QPushButton(self.central_widget)
        self.debugging_button.setObjectName('debugging')
        self.debugging_button.setCheckable(True)
        self.only_save_button = QtWidgets.QPushButton(self.central_widget)
        self.only_save_button.setCheckable(True)

        self.verify_button = QtWidgets.QPushButton(self.central_widget)

        self.gridLayout.addWidget(self.verify_button, 9, 2, 1, 1)
        self.gridLayout.addWidget(self.only_save_button, 11, 2, 1, 1)
        self.gridLayout.addWidget(self.debugging_button, 10, 2, 1, 1)
        self.gridLayout.addWidget(self.arduino_button, 4, 1, 1, 1)
        self.gridLayout.addWidget(self.start_program, 4, 2, 5, 1)
        self.gridLayout.addWidget(self.cadastro_button, 8, 1, 2, 1)
        self.gridLayout.addWidget(self.clean_log_button, 10, 1, 1, 1)
        self.gridLayout.addWidget(self.console_textEdit, 4, 0, 8, 1)
        self.gridLayout.addWidget(self.webcam_button, 6, 1, 1, 1)
        self.gridLayout.addWidget(self.cameras_button, 5, 1, 1, 1)
        self.gridLayout.addWidget(self.scrolling_button, 11, 1, 1, 1)

        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.setCentralWidget(self.central_widget)

        self.set_text()
        self._clicks()
        self.settings_verification()
        self.showFullScreen()

    def set_text(self):
        self.verify_button.setText('VERIFICAR')
        self.only_save_button.setText('APENAS SALVAR')
        self.placas_button.setText('PLACAS')
        self.debugging_button.setText('DEBUGGING')
        self.arduino_button.setText('ARDUINO')
        self.start_program.setText('INICIAR')
        self.webcam_button.setText('WEBCAM')
        self.cameras_button.setText('CÂMERAS')
        self.clean_log_button.setText('LIMPAR LOG')
        self.cadastro_button.setText('CRACHÁ')
        self.scrolling_button.setText('SCROLLING')

        self.console_textEdit.setReadOnly(True)

    def _clicks(self):
        self.start_program.clicked.connect(self.run_inspection)
        self.debugging_button.clicked.connect(self.configs_verify)
        self.only_save_button.clicked.connect(self.configs_verify)
        self.clean_log_button.clicked.connect(self.clear_text_edit)
        self.arduino_button.clicked.connect(self.show_arduino)

    def run_inspection(self):
        if self.program_started is False:
            debugging = self.debugging_button.isChecked()
            only_saving = self.only_save_button.isChecked()

            self.program_started = True
            print('color to 255, 134, 32')
            self.start_program.setStyleSheet("background-color: rgb(255, 134, 32);\n"
                                             "color: rgb(255, 255, 255);")
            self.start_program.setText('PARAR')

            self.core_process = Process(target=inspection, args=(self.console_queue, debugging, only_saving))
            self.core_process.daemon = True
            self.core_process.start()

            self.queue_reader = Thread(target=self.console_reader)
            self.queue_reader.start()

            self.turn_buttons(False, [self.scrolling_button, self.start_program, self.clean_log_button])

        else:
            self.program_started = False
            self.queue_reader.join()

            self.core_process.terminate()
            self.core_process.join()
            self.start_program.setStyleSheet("background-color: rgb(64, 134, 32);\n"
                                             "color: rgb(255, 255, 255);")

            print('color has changed to (64, 134, 32)')
            self.start_program.setText('INICIAR')
            self.turn_buttons(True)

    def console_reader(self):
        while self.program_started:
            if self.console_queue.empty() is False:

                self.console_textEdit.append(self.console_queue.get().format(self.calha_nome))
                if self.scrolling_button.isChecked():
                    self.console_textEdit.moveCursor(QtGui.QTextCursor.End)
            time.sleep(0.3)

    def configs_verify(self):
        clicked = self.sender().objectName()
        if clicked == 'debugging':
            if self.only_save_button.isChecked():
                self.only_save_button.setChecked(False)

        else:
            if self.debugging_button.isChecked():
                self.debugging_button.setChecked(False)

    def turn_buttons(self, action, let_enabled=None):
        self.arduino_button.setEnabled(action)
        self.cameras_button.setEnabled(action)
        self.webcam_button.setEnabled(action)
        self.placas_button.setEnabled(action)
        self.cadastro_button.setEnabled(action)
        self.clean_log_button.setEnabled(action)
        self.scrolling_button.setEnabled(action)

        self.start_program.setEnabled(action)

        self.verify_button.setEnabled(action)
        self.debugging_button.setEnabled(action)
        self.only_save_button.setEnabled(action)

        if let_enabled is not None:
            if type(let_enabled) == list:
                for button in let_enabled:
                    button.setEnabled(True)
            else:
                let_enabled.setEnabled(True)

    def clear_text_edit(self):
        msg_box = MsgBox(f'AOI {self.calha_nome}', 'Deseja apagar o console?',
                         (QMessageBox.Ok | QMessageBox.Cancel), QMessageBox.Information)
        return_value = msg_box.exec_()

        if return_value == QMessageBox.Ok:
            self.console_textEdit.clear()

    def settings_verification(self):
        settings = (('arduino.json', self.arduino_button), ('cameras.json', self.cameras_button))
        unset_settings = []

        for i, setting in enumerate(settings):
            if os.path.isfile(f'settings/{setting[0]}') is False:
                unset_settings.append(setting[1])
                setting[1].setStyleSheet("background-color: rgb(207, 217, 15)")

        if len(unset_settings) != 0:
            self.turn_buttons(False, unset_settings)
            txt = '_' * 10 + f'_ AOI {self.calha_nome} - arquivos de configuração inexistentes _' + '_' * 10 + '\n'
            self.console_textEdit.append(txt)
            txt = '__ __  __  _ Por favor, realize as configurações necessárias ao lado _  __  __ __'
            self.console_textEdit.append(txt)

        else:
            self.start_program.setStyleSheet("background-color: rgb(64, 134, 32);\n"
                                             "color: rgb(255, 255, 255);")

    def show_arduino(self):
        self.second_window = ArduinoWindow()
        self.second_window.show()


class MsgBox(QMessageBox):
    def __init__(self, name, text, buttons, icon):
        super(MsgBox, self).__init__()
        self.setWindowTitle(name)
        self.setWindowIcon(QIcon('icon_simnext.png'))
        self.setIcon(icon)
        self.setText(text)
        self.setStandardButtons(buttons)


class ArduinoWindow(QtWidgets.QWidget):
    def __init__(self):
        super(ArduinoWindow, self).__init__()
        self.succeeded_connection = None
        self.inputs = []
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.reader = None

        self.main_widget_layout = QtWidgets.QVBoxLayout(self)  # verticalLayout_2
        self.main_layout = QtWidgets.QVBoxLayout()  # main_layout

        self.window_icon = QIcon('icon_simnext.png')
        self.setWindowIcon(self.window_icon)
        self.setWindowTitle('Configurações')

        font = QtGui.QFont()
        font.setPointSize(11)
        self.setFixedSize(415, 620)
        self.groupBox = QtWidgets.QGroupBox(self)
        self.groupBox.setFont(font)
        self.groupBox.setTitle('Configurações do Arduino')
        self.groupBox_layout = QtWidgets.QGridLayout(self.groupBox)

        self.porta_label = QtWidgets.QLabel(self.groupBox)
        self.porta_label.setText('Porta do Arduino:')
        self.porta_label.setFont(font)
        self.groupBox_layout.addWidget(self.porta_label, 0, 0, 1, 1)

        self.COMS_comboBox = QtWidgets.QComboBox(self.groupBox)
        com_ports = ('COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7')
        self.COMS_comboBox.addItems(com_ports)
        self.COMS_comboBox.setFont(font)
        self.groupBox_layout.addWidget(self.COMS_comboBox, 0, 1, 1, 1)

        self.connect_button = QtWidgets.QPushButton(self.groupBox)
        self.connect_button.setText('Conectar')
        self.connect_button.setFont(font)
        self.groupBox_layout.addWidget(self.connect_button, 0, 2, 1, 1)

        self.addInput_button = QtWidgets.QPushButton(self.groupBox)
        self.addInput_button.setText('Adicionar entrada')
        self.addInput_button.setEnabled(False)
        self.addInput_button.setFont(font)
        self.groupBox_layout.addWidget(self.addInput_button, 1, 0, 1, 2)

        self.remove_button = QtWidgets.QPushButton(self.groupBox)
        self.remove_button.setText('Remover')
        self.remove_button.setEnabled(False)
        self.remove_button.setFont(font)
        self.groupBox_layout.addWidget(self.remove_button, 1, 2, 1, 1)

        self.groupBox2 = QtWidgets.QGroupBox(self.groupBox)
        self.groupBox2.setTitle('Entradas adicionadas')
        self.groupBox2.setFont(font)
        self.groupBox2.setEnabled(False)
        self.groupBox2_layout = QtWidgets.QGridLayout(self.groupBox2)
        self.groupBox_layout.addWidget(self.groupBox2, 2, 0, 1, 3)

        self.outputs_button = QtWidgets.QPushButton(self.groupBox)
        self.outputs_button.setText('Saídas...')
        self.outputs_button.setFont(font)
        self.groupBox_layout.addWidget(self.outputs_button, 3, 0, 1, 1)

        self.confirm_button = QtWidgets.QPushButton(self.groupBox)
        self.confirm_button.setText('Validar configurações')
        self.confirm_button.setFont(font)
        self.groupBox_layout.addWidget(self.confirm_button, 3, 1, 1, 2)

        self.main_layout.addWidget(self.groupBox)
        self.main_widget_layout.addLayout(self.main_layout)
        self._clicks()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.succeeded_connection is not None:
            self.succeeded_connection.exit()

    def _clicks(self):
        self.connect_button.clicked.connect(self._connection_test)
        self.addInput_button.clicked.connect(self.add_inputs)
        self.remove_button.clicked.connect(self.remove_inputs)

    def _connection_test(self):
        if self.succeeded_connection is None:
            port = self.COMS_comboBox.currentText()
            try:
                arduino = Arduino(port)
                it = util.Iterator(arduino)
                it.start()
                time.sleep(0.2)

            except serial.serialutil.SerialException as e:
                error_msg = MsgBox('Arduino', f'Conexão não sucedida! {e}', QMessageBox.Ok, QMessageBox.Warning)
                error_msg.exec_()

            else:
                self.succeeded_connection = arduino
                self.connect_button.setText('Desconectar')
                self.COMS_comboBox.setEnabled(False)
                self.addInput_button.setEnabled(True)
                self.groupBox2.setEnabled(True)

                if len(self.inputs) != 0:
                    self.remove_button.setEnabled(True)
        else:
            self.succeeded_connection.exit()
            self.succeeded_connection = None
            self.connect_button.setText('Conectar')
            self.COMS_comboBox.setEnabled(True)
            self.addInput_button.setEnabled(False)
            self.groupBox2.setEnabled(False)
            self.remove_button.setEnabled(False)

    def add_inputs(self):
        rows = len(self.inputs)

        if rows < 5:
            label = QtWidgets.QLabel(self.groupBox2)
            label.setText('Nome referência:')
            self.groupBox2_layout.addWidget(label, rows, 0, 1, 1)

            input_type = QtWidgets.QComboBox(self.groupBox2)
            input_type.addItems(('SEN1', 'SEN2', 'SEN3', 'BTN1', 'BTN2', 'BTN3'))
            self.groupBox2_layout.addWidget(input_type, rows, 1, 1, 1)

            input_port = QtWidgets.QComboBox(self.groupBox2)
            for i in range(6):
                input_port.addItem(f'A{i}', f'a:{i}:i')
            self.groupBox2_layout.addWidget(input_port, rows, 2, 1, 1)

            test_button = QtWidgets.QPushButton(self.groupBox2)
            test_button.clicked.connect(lambda event, r=rows: self.reading_test(r))
            test_button.setText('Testar')
            self.groupBox2_layout.addWidget(test_button, rows, 3, 1, 1)

            new_input_row = (label, input_type, input_port, test_button)
            self.inputs.append(new_input_row)

            self.remove_button.setEnabled(True)
            if rows > 3:
                self.addInput_button.setEnabled(False)

    def remove_inputs(self):
        self.addInput_button.setEnabled(True)
        for widget in self.inputs[-1]:
            self.groupBox2_layout.removeWidget(widget)
            widget.deleteLater()

        self.inputs.pop(-1)

        if len(self.inputs) == 0:
            self.remove_button.setEnabled(False)

    def reading_test(self, input_row):
        index = self.inputs[input_row][2].currentIndex()
        port = self.inputs[input_row][2].itemData(index)

        self.reader = InputReader(self.succeeded_connection, port)
        self.reader.show()


class InputReader(QtWidgets.QWidget):
    def __init__(self, nano, port):
        super(InputReader, self).__init__()
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        window_icon = QIcon('icon_simnext.png')
        self.setWindowIcon(window_icon)
        self.setWindowTitle('Leitura de valores')
        self.setFixedSize(271, 147)

        self.main_widget_layout = QtWidgets.QGridLayout(self)
        self.gridLayout = QtWidgets.QGridLayout()

        font = QtGui.QFont()
        font.setPointSize(14)

        self.pushButton = QtWidgets.QPushButton(self)
        self.pushButton.setText('OK')
        self.pushButton.clicked.connect(self.exit)
        self.pushButton.setFont(font)
        self.gridLayout.addWidget(self.pushButton, 1, 0, 1, 1)

        self.label = QtWidgets.QLabel(self)
        font.setPointSize(28)
        self.label.setFont(font)
        self.label.setAlignment(Qt.AlignCenter)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.main_widget_layout.addLayout(self.gridLayout, 0, 0, 1, 1)

        nano.taken['analog'] = {x: False for x in nano.taken['analog']}

        self.keep_reading = True
        self.pin = nano.get_pin(port)
        self.running = Thread(target=self.run)
        self.running.start()

    def run(self):
        while self.keep_reading:
            self.label.setText(str(self.pin.read()))
            time.sleep(0.05)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.exit()

    def exit(self):
        self.keep_reading = False
        self.running.join()
        self.close()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    root = MainWindow()
    root.show()
    sys.exit(app.exec_())
