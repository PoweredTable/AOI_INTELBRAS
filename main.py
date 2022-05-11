import json
import os
import time
from ini_files import ArduinoIni, return_operators

from PyQt5 import QtCore, QtGui, QtWidgets
from configparser import ConfigParser
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from pyfirmata import ArduinoNano, util

from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox
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

        self.arduino_window = None

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

        self.webcam_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.webcam_pushButton.setText('WEBCAM')
        self.webcam_pushButton.setSizePolicy(size_policy)
        self.webcam_pushButton.setFont(font)

        self.placas_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.placas_pushButton.setText('PLACAS')
        self.placas_pushButton.setSizePolicy(size_policy)
        self.placas_pushButton.setFont(font)

        size_policy.setHorizontalStretch(1)

        self.cadastro_pushButton = QtWidgets.QPushButton(self.central_widget)
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
        self.start_pushButton.setSizePolicy(size_policy)
        self.start_pushButton.setFont(font)

        self.verify_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.verify_pushButton.setText('VERIFICAR')

        self.onlySave_pushButton = QtWidgets.QPushButton(self.central_widget)
        self.onlySave_pushButton.setText('APENAS SALVAR')
        self.onlySave_pushButton.setCheckable(True)

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(5)
        size_policy.setVerticalStretch(0)

        font.setPointSize(18)

        self.console_textEdit = QtWidgets.QTextEdit(self.central_widget)
        self.console_textEdit.setReadOnly(True)
        self.console_textEdit.setSizePolicy(size_policy)
        self.console_textEdit.setFont(font)

        self.gridLayout.addWidget(self.arduino_pushButton, 4, 1, 1, 1)
        self.gridLayout.addWidget(self.cameras_pushButton, 5, 1, 1, 1)
        self.gridLayout.addWidget(self.webcam_pushButton, 6, 1, 1, 1)
        self.gridLayout.addWidget(self.placas_pushButton, 7, 1, 1, 1)
        self.gridLayout.addWidget(self.cadastro_pushButton, 8, 1, 1, 1)
        self.gridLayout.addWidget(self.cleanLog_pushButton, 9, 1, 1, 1)
        self.gridLayout.addWidget(self.scrolling_pushButton, 10, 1, 1, 1)

        self.gridLayout.addWidget(self.start_pushButton, 4, 2, 5, 1)
        self.gridLayout.addWidget(self.verify_pushButton, 9, 2, 1, 1)
        self.gridLayout.addWidget(self.onlySave_pushButton, 10, 2, 1, 1)

        self.gridLayout.addWidget(self.console_textEdit, 4, 0, 7, 1)

        self.central_layout.addLayout(self.gridLayout, 0, 0, 1, 1)
        self.setCentralWidget(self.central_widget)

        self.assing_functions()

        # checks if creating or editing a necessary config file is needed
        self.settings_verification()
        self.showFullScreen()

    def assing_functions(self):
        self.start_pushButton.clicked.connect(self.run_inspection)
        self.cleanLog_pushButton.clicked.connect(self.clear_text_edit)
        self.arduino_pushButton.clicked.connect(self.show_arduino)

    def run_inspection(self):
        if self.program_started is False:
            self.program_started = True

            # retrieves a boolean if the button is pressed or not
            # if true it means I won't inspect any board at all
            only_saving: bool = self.onlySave_pushButton.isChecked()

            self.start_pushButton.setStyleSheet("background-color: rgb(255, 134, 32);\n"
                                                "color: rgb(255, 255, 255);")
            self.start_pushButton.setText('PARAR')

            # separate process to prevent GUI freezing
            self.core_process = Process(target=inspection, args=(self.console_queue, only_saving))
            self.core_process.daemon = True
            self.core_process.start()

            self.queue_reader = Thread(target=self.console_reader)
            self.queue_reader.start()

            self.turn_buttons(False, [self.scrolling_pushButton, self.start_pushButton, self.cleanLog_pushButton])

        else:
            self.program_started = False
            self.queue_reader.join()

            self.core_process.terminate()
            self.core_process.join()
            self.start_pushButton.setStyleSheet("background-color: rgb(64, 134, 32);\n"
                                                "color: rgb(255, 255, 255);")
            self.start_pushButton.setText('INICIAR')
            self.turn_buttons(True)

    def console_reader(self):
        while self.program_started:
            if self.console_queue.empty() is False:

                self.console_textEdit.append(self.console_queue.get().format(self.calha_nome))
                if self.scrolling_pushButton.isChecked():
                    self.console_textEdit.moveCursor(QtGui.QTextCursor.End)
            time.sleep(0.3)

    def turn_buttons(self, action, let_enabled=None):
        self.arduino_pushButton.setEnabled(action)
        self.cameras_pushButton.setEnabled(action)
        self.webcam_pushButton.setEnabled(action)
        self.placas_pushButton.setEnabled(action)
        self.cadastro_pushButton.setEnabled(action)
        self.cleanLog_pushButton.setEnabled(action)
        self.scrolling_pushButton.setEnabled(action)
        self.start_pushButton.setEnabled(action)
        self.verify_pushButton.setEnabled(action)
        self.onlySave_pushButton.setEnabled(action)

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
        self.arduino_window = ArduinoWindow()
        #arduino_settings = ArduinoIni().get_settings()
        #self.arduino_window = ArduinoWindow(*arduino_settings)

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
    def __init__(self):
        super(ArduinoWindow, self).__init__()

        self.com, self.ports = None, ArduinoIni.parameters()
        self.board = None
        self.readers = {}

        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

        self.setWindowIcon(QIcon('icon_simnext.png'))
        self.setWindowTitle('Configurações')
        self.setFixedSize(415, 620)

        self.central_layout = QtWidgets.QVBoxLayout(self)  # verticalLayout_2
        self.main_layout = QtWidgets.QVBoxLayout()  # main_layout

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
        self.inp_tab_layout = QtWidgets.QGridLayout(self.inp_tab)  # first layout

        self.simulate_pushButton = QtWidgets.QPushButton(self.inp_tab)
        self.simulate_pushButton.setText('Simular ativação')
        self.inp_tab_layout.addWidget(self.simulate_pushButton, 0, 0, 1, 2)

        self.inp_tab_frame = QtWidgets.QFrame()
        self.inp_tab_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.inp_tab_frame_layout = QtWidgets.QGridLayout(self.inp_tab_frame)

        for r in range(3):
            label = QtWidgets.QLabel(self.inp_tab_frame)
            label.setText("Sensor:")

            line_edit = QtWidgets.QLineEdit(self.inp_tab_frame)
            line_edit.setText(f"SENS_{r+1}") 
            line_edit.setAlignment(Qt.AlignCenter)
            line_edit.setEnabled(False)

            self.inp_tab_frame_layout.addWidget(label, r, 0, 1, 1)
            self.inp_tab_frame_layout.addWidget(line_edit, r, 1, 1, 1)
        
        # parâmetros do primeiro sensor [SENS_1]
        self.sens1_comboBox = QtWidgets.QComboBox(self.inp_tab_frame)

        self.sens1_spinBox = QtWidgets.QDoubleSpinBox(self.inp_tab_frame)

        self.sens1_pushButton = QtWidgets.QPushButton(self.inp_tab_frame)
        self.sens1_pushButton.setText("Ler")

        self.inp_tab_frame_layout.addWidget(self.sens1_comboBox, 0, 2, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens1_spinBox, 0, 3, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens1_pushButton, 0, 4, 1, 1)

        # parâmetros do segundo sensor [SENS_2]
        self.sens2_comboBox = QtWidgets.QComboBox(self.inp_tab_frame)

        self.sens2_spinBox = QtWidgets.QDoubleSpinBox(self.inp_tab_frame)

        self.sens2_pushButton = QtWidgets.QPushButton(self.inp_tab_frame)
        self.sens2_pushButton.setText("Ler")

        self.inp_tab_frame_layout.addWidget(self.sens2_comboBox, 1, 2, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens2_spinBox, 1, 3, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens2_pushButton, 1, 4, 1, 1)

        # parâmetros do tereiro sensor [SENS_3]
        self.sens3_comboBox = QtWidgets.QComboBox(self.inp_tab_frame)

        self.sens3_spinBox = QtWidgets.QDoubleSpinBox(self.inp_tab_frame)
        self.sens3_pushButton = QtWidgets.QPushButton(self.inp_tab_frame)
        self.sens3_pushButton.setText("Ler")

        self.inp_tab_frame_layout.addWidget(self.sens3_comboBox, 2, 2, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens3_spinBox, 2, 3, 1, 1)
        self.inp_tab_frame_layout.addWidget(self.sens3_pushButton, 2, 4, 1, 1)

        # adding operators and data items
        for operator, function in return_operators().items():
            self.sens1_comboBox.addItem(operator, function)
            self.sens2_comboBox.addItem(operator, function)
            self.sens3_comboBox.addItem(operator, function)

        self.inputs_frame_grid = QtWidgets.QGridLayout()
        self.inp_tab_frame_layout.addLayout(self.inputs_frame_grid, 0, 0, 1, 1)
        self.inp_tab_layout.addWidget(self.inp_tab_frame, 1, 0, 1, 2)

        self.inp_out_tabWidget.addTab(self.inp_tab, 'Entradas')

        self.out_tab = QtWidgets.QWidget()
        self.out_tab_layout = QtWidgets.QGridLayout(self.out_tab)

        outputs = ('Controle esteira', 'Pino pneumático', 'Controle luzes', 'Alarme esteira', 'Alarme máquina')
        digitalis = [(f'digital {x}', x) for x in range(2, 13)]
        r, c, rs, cs = 0, 0, 1, 1
        for output in outputs:
            label = QtWidgets.QLabel(self.out_tab)
            label.setText(output + ':')
            self.out_tab_layout.addWidget(label, r, c, rs, cs)
            combo_box = QtWidgets.QComboBox(self.out_tab)

            self.out_tab_layout.addWidget(combo_box, r, c + 1, rs, cs)

            push_button = QtWidgets.QPushButton(self.out_tab)
            push_button.clicked.connect(lambda click, index=r: self.digital_test(index))
            if r > 2:
                spin_box = QtWidgets.QSpinBox(self.out_tab)
                spin_box.setMinimum(1)
                spin_box.setMaximum(18)
                self.out_tab_layout.addWidget(spin_box, r, c + 2, rs, cs)

                self.out_tab_layout.addWidget(push_button, r, c + 3, rs, cs)

                push_button.setText('tocar')

                if r > 3:
                    combo_box.addItem('desativado', False)
                    combo_box.currentIndexChanged.connect(lambda change, p_button=push_button:
                                                          self._alarm_switch(p_button))
                    spin_box.setEnabled(False)
                    push_button.setEnabled(False)
            else:
                self.out_tab_layout.addWidget(push_button, r, c + 2, rs, cs + 1)
                push_button.setText('ativar')

            for digital in digitalis:
                combo_box.addItem(*digital)
            r += 1

        self.inp_out_tabWidget.addTab(self.out_tab, 'Saídas')

        self.confirm_button = QtWidgets.QPushButton(self.groupBox)
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText('Validar configurações')
        self.confirm_button.setFont(font)

        self.groupBox_layout.addWidget(self.confirm_button, 2, 0, 1, 3)
        self.groupBox_layout.addWidget(self.inp_out_tabWidget, 1, 0, 1, 3)

        self.main_layout.addWidget(self.groupBox)
        self.central_layout.addLayout(self.main_layout)

        self.assing_functions()
        self.connection_attempt(True)
        
    def assing_functions(self):
        self.connect_pushButton.clicked.connect(self.connection_attempt)
        self.confirm_button.clicked.connect(self.connections_verify)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        for reader in list(self.readers.values()):
            reader.close()

    def connection_attempt(self, first_run=False):
        self.com = ArduinoIni.port_connection()
        self.com_lineEdit.setText(self.com)
        if 'COM' not in self.com:  # check if COM is now connected
            if not first_run:
                error_msg = MsgBox('Arduino', f'Conexão não sucedida, arduino não encontrado!',
                                   QMessageBox.Ok, QMessageBox.Warning)
                error_msg.exec_()
            return

        if self.board is None:
            self.board = ArduinoNano(self.com)
            it = util.Iterator(self.board)
            it.start()
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

    def _alarm_switch(self, push_button):
        index = self.outputs[4][0].currentIndex()
        action = True if index != 0 else False

        push_button.setEnabled(action)
        self.outputs[4][1].setEnabled(action)

    def add_inputs(self):
        rows = len(self.inputs)

        if rows < 6:
            label = QtWidgets.QLabel(self.inp_tab_frame)
            label.setText('Referência:')
            self.inp_tab_frame_layout.addWidget(label, rows, 0, 1, 1)

            input_type = QtWidgets.QComboBox(self.inp_tab_frame)
            input_type.addItems(('SEN1', 'SEN2', 'SEN3', 'BTN1', 'BTN2', 'BTN3'))
            self.inp_tab_frame_layout.addWidget(input_type, rows, 1, 1, 1)

            input_port = QtWidgets.QComboBox(self.inp_tab_frame)
            for i in range(6):
                input_port.addItem(f'A{i}', f'a:{i}:i')
            self.inp_tab_frame_layout.addWidget(input_port, rows, 2, 1, 1)

            test_button = QtWidgets.QPushButton(self.inp_tab_frame)
            test_button.clicked.connect(lambda click, r=rows: self.reading_test(r))
            test_button.setText('Testar')
            self.inp_tab_frame_layout.addWidget(test_button, rows, 3, 1, 1)

            new_input_row = (label, input_type, input_port, test_button)
            self.inputs.append(new_input_row)

            self.remove_pushButton.setEnabled(True)
            if rows > 4:
                self.add_pushButton.setEnabled(False)

    def remove_inputs(self):
        self.add_pushButton.setEnabled(True)
        for widget in self.inputs[-1]:
            self.inp_tab_frame_layout.removeWidget(widget)
            widget.deleteLater()

        self.inputs.pop(-1)
        if len(self.inputs) == 0:
            self.remove_pushButton.setEnabled(False)

    def reading_test(self, input_row):
        index = self.inputs[input_row][2].currentIndex()
        port = self.inputs[input_row][2].itemData(index)

        if port not in self.readers:
            self.confirm_button.setEnabled(False)
            self.connect_pushButton.setEnabled(False)
            self.readers[port] = InputReader(self.board, port)
            self.readers[port].signal.connect(self._reading_test_close)
            self.readers[port].show()

    def _reading_test_close(self, port):
        self.readers.pop(port)
        if len(self.readers) == 0:
            self.confirm_button.setEnabled(True)
            self.connect_pushButton.setEnabled(True)

    def digital_test(self, output_row):
        combo_box = self.outputs[output_row][0]
        digital = combo_box.itemData(combo_box.currentIndex())

        if output_row <= 2:
            push_button = self.outputs[output_row][1]
            status = 1 if push_button.text() == 'ativar' else 0
            text = 'desativar' if status == 1 else 'ativar'
            push_button.setText(text)
            self.board.digital[digital].write(status)

        else:
            bipes = self.outputs[output_row][1].value()
            for _ in range(bipes):
                self.board.digital[digital].write(1)
                time.sleep(0.11)
                self.board.digital[digital].write(0)
                time.sleep(0.07)

    def connections_verify(self):
        advises, json_dict = Validation(self.board, self.inputs, self.outputs).check()

        if advises['any'] is False:
            with open('settings/arduino.json', 'w') as f:
                f.write(json.dumps(json_dict, indent=3))

            MsgBox('Arduino', 'Configurações salvas, para aplicá-las é necessário reiniciar, reiniciar agora?',
                   (QMessageBox.Yes | QMessageBox.No), QMessageBox.Information).exec_()
        else:
            inp_warning, inp_critical = advises['inputs']['warning'], advises['inputs']['critical']
            digital_warning = advises['digital_warning']
            if inp_warning != 0:
                adv_one = 'Referênicas ou portas analógicas duplicadas' if inp_warning > 1 else \
                          'Referência ou porta analógica duplicada'

                MsgBox('Erro de validação', adv_one + ', verifique as entradas inseridas e tente novamente!',
                       QMessageBox.Ok, QMessageBox.Warning).exec_()

            if digital_warning != 0:
                adv_three = 'Portas digitais duplicadas' if digital_warning > 1 else 'Porta digital duplicada'
                MsgBox('Erro de validação', adv_three + ', verifique as saídas inseridas e tente novamente!',
                       QMessageBox.Ok, QMessageBox.Warning).exec_()

            if len(inp_critical) != 0:
                adv_two = f'Portas analógicas {inp_critical} não retornam valores' if len(inp_critical) > 1 else \
                          f'Porta analógica {inp_critical[0]} não retorna valores'
                MsgBox('Erro de validação', adv_two + ', verifique as conexões do arduino e tente novamente!',
                       QMessageBox.Ok, QMessageBox.Critical).exec_()


class Validation:
    def __init__(self, nano, inputs, outputs):
        self._inputs = [(input_v[1], input_v[2]) for input_v in inputs]
        self._outputs = [output[0] for output in outputs]
        self.nano = nano
        self.c_thread = None

        self.json_dict = {'port': self.nano.name, 'inputs': {}, 'outputs': {}}
        self.advises = {'any': False, 'inputs': {'warning': 0, 'critical': []}, 'digital_warning': 0}

    def check(self):
        self.c_thread = Thread(target=self._checking)
        self.c_thread.start()
        self.c_thread.join()

        return self.advises, self.json_dict

    def _checking(self):
        inputs = {'input_type': {'seen': set()}, 'input_port': {'seen': set()}}
        digital_ports = set()

        for input_type, input_port in self._inputs:
            type_txt, key = input_type.currentText(), 'input_type'
            input_type_ok = True
            if type_txt not in inputs[key]['seen']:
                inputs[key]['seen'].add(type_txt)
            else:
                input_type_ok = False
                self.advises['any'] = True
                self.advises['inputs']['warning'] += 1

            port_txt, key = input_port.itemData(input_port.currentIndex()), 'input_port'
            input_port_ok = True
            if port_txt not in inputs[key]['seen']:
                inputs[key]['seen'].add(port_txt)
            else:
                input_port_ok = False
                self.advises['any'] = True
                self.advises['inputs']['warning'] += 1

            if input_type_ok and input_port_ok:
                returning_values = self._reading_test(port_txt)
                if not returning_values:
                    self.advises['any'] = True
                    self.advises['inputs']['critical'].append(input_port.currentText())

                else:
                    self.json_dict['inputs'][type_txt] = port_txt

        digital_references = ('CTR_EST', 'PIN_PNE', 'CTR_LUZ', 'ALR_EST', 'ALR_MQN')
        for digital_port, reference in zip(self._outputs, digital_references):
            port = digital_port.itemData(digital_port.currentIndex())
            if port not in digital_ports:
                digital_ports.add(port)
            else:
                self.advises['any'] = True
                self.advises['digital_warning'] += 1

            if self.advises['any'] is not True:
                self.json_dict['outputs'][reference] = port

    def _reading_test(self, input_port: str) -> bool:
        taken_port: int = int(input_port.split(':')[1])
        pin, value = self.nano.get_pin(input_port), None
        for _ in range(10):
            value = pin.read()
            time.sleep(0.125)
        self.nano.taken['analog'][taken_port] = False
        return True if value is not None else False


class InputReader(QtWidgets.QWidget):
    signal = QtCore.pyqtSignal(str)

    def __init__(self, nano, port):
        super(InputReader, self).__init__()
        self.nano, self.taken_port = nano, int(port.split(':')[1])

        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.setWindowIcon(QIcon('icon_simnext.png'))
        self.setWindowTitle(f'Leitura de {port}')
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

        self.keep_reading = True
        self.pin = nano.get_pin(port)
        self.running = Thread(target=self.run)
        self.running.start()

    def run(self):
        while self.keep_reading:
            pin_value = self.pin.read()
            text = f'{pin_value:.4f}' if pin_value is not None else pin_value
            self.label.setText(text)
            time.sleep(0.05)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.keep_reading:
            self.exit()

    def exit(self):
        self.nano.taken['analog'][self.taken_port] = False
        self.signal.emit(f'a:{self.taken_port}:i')
        self.keep_reading = False
        self.running.join()
        self.close()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    root = MainWindow()
    root.show()
    sys.exit(app.exec_())
