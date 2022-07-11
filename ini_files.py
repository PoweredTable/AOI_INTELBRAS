import configparser
from console_log import arduino_not_found_error, creating_arduino_file_warn
from configparser import ConfigParser
from serial.tools.list_ports import comports
import warnings
import os
import operator


def get_default_ports(console):
    ports = {'INPUTS': {}, 'OUTPUTS': {}}

    default_params, default_ports = defaults()

    ini_file = ConfigParser()
    if os.path.isfile('settings/arduino.ini') is False:  # First run
        ini_file = default_arduino_ini(ini_file, default_params)
        console.insertHtml(creating_arduino_file_warn)
    else:
        try:
            ini_file.read('settings/arduino.ini')
        except configparser.MissingSectionHeaderError:
            console.insertHtml(creating_arduino_file_warn)
            ini_file = default_arduino_ini(ini_file, default_params)

    if any(section not in ini_file.sections() for section in default_params.keys()):
        console.insertHtml(creating_arduino_file_warn)
        ini_file = default_arduino_ini(ini_file, default_params)

    for section in default_params.keys():
        if any(option not in ini_file.options(section) for option in default_params[section].keys()):
            console.insertHtml(creating_arduino_file_warn)
            ini_file = default_arduino_ini(ini_file, default_params)

        ports[section] = {option: functionality(default_ports[section][option], ini_file.get(section, option))
                          for option in ini_file.options(section) if ini_file.get(section, option) != 'off'}

    return ports['INPUTS'], ports['OUTPUTS']


def get_port_connection(console=None) -> str:
    """
    Procura pelo Arduino conectado no
    computador e retorna sua porta serial COM
    -st-a call:
        from ini_files import get_port_connection
        port = get_port_connection()
    """
    simulating = False
    com_port = [p.device for p in comports()
                if any(ard in p.description for ard in ('Arduino', 'CH340'))]

    found_serials = len(com_port)
    if found_serials > 1:
        warnings.warn(f'Multiple connections found, utilizing {com_port[0]} port.')

    elif found_serials == 0:
        if simulating:
            return 'COM3'

        if console is not None:
            console.insertHtml(arduino_not_found_error)

        com_port.append('Não encontrado')
    return com_port[0]


def functionality(option, value):
    """
    -Retorna a opção ou a opção e o operador matemático de ativação do sensor
    """
    if value == 'on':
        return option

    return option, get_opr(value)


def get_opr(opr=None):
    operators_dict = {'>': operator.gt, '<': operator.lt, '>=': operator.ge,
                      '<=': operator.le, '==': operator.eq}
    if opr is None:
        return operators_dict
    else:
        opr, value = opr.split('|')
        value = int(value)

        return operators_dict[opr], opr, value


def defaults(section=None, requesting_default_port=None):
    """
    -Função que determina as portas, entradas e saídas do Arduino
    -st-a call:
        from ini_files import defaults
        default_values = defaults()
    """
    default_ports = {'INPUTS': {'sensor_1': 'a:0:i', 'sensor_2': 'a:1:i', 'sensor_3': 'a:2:i',
                                'digital_1': 'a:4:i', 'digital_2': 'a:5:i'},
                     'OUTPUTS': {'inverter': 3, 'lights': 6, 'buzzer': 2,
                                 'valve_1': 8, 'valve_2': 7, 'emergency': 5}}
    if requesting_default_port is not None:
        return default_ports[section][requesting_default_port]

    default_params = {'INPUTS': {'sensor_1': '==|1', 'sensor_2': 'off', 'sensor_3': 'off',
                                 'digital_1': 'off', 'digital_2': 'off'},
                      'OUTPUTS': {'inverter': 'on', 'lights': 'on', 'buzzer': 'on',
                                  'valve_1': 'on', 'valve_2': 'off', 'emergency': 'off'}}
    return default_params, default_ports


def default_arduino_ini(ini_file, ports=defaults()[0], corrupted=True):
    file = 'settings/arduino.ini'
    if corrupted:
        os.remove(file)

    ini_file.read(file)
    ini_file['INPUTS'] = ports['INPUTS']
    ini_file['OUTPUTS'] = ports['OUTPUTS']

    with open(file, 'w+') as config_file:
        ini_file.write(config_file)
    return ini_file
