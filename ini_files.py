import configparser
from configparser import ConfigParser
from serial.tools.list_ports import comports
import warnings
import os
import operator


class ArduinoIni:
    @staticmethod
    def port_connection():
        simulating = True
        com_port = [p.device for p in comports()
                    if any(ard in p.description for ard in ('Arduino', 'CH340'))]

        found_serials = len(com_port)
        if found_serials > 1:
            warnings.warn(f'Multiple connections found, utilizing {com_port[0]} port.')

        elif found_serials == 0:
            if simulating:
                return 'COM3'
            driver = 'https://drive.google.com/drive/folders/1fCUTciTNCfYBJtet1WClLt9V-o6wJ-wu?usp=sharing'
            warnings.warn(f"Arduino not found, make sure the following driver is installed: {driver}")
            com_port.append('Não encontrado')
        return com_port[0]

    @staticmethod
    def parameters():
        ports = {'INPUTS': {}, 'OUTPUTS': {}}
        default_params = {'INPUTS': {'sensor_1': '==|1', 'sensor_2': 'off', 'sensor_3': 'off'},
                          'OUTPUTS': {'inverter': 'on', 'lights': 'on', 'buzzer': 'on',
                                      'valve_1': 'on', 'valve_2': 'off', 'digital_1': 'off',
                                      'digital_2': 'off', 'emergency': 'off'}}

        default_ports = {'INPUTS': {'sensor_1': 'a:0:i', 'sensor_2': 'a:1:i', 'sensor_3': 'a:2:i'},
                         'OUTPUTS': {'inverter': 3, 'lights': 6, 'buzzer': 2,
                                     'valve_1': 8, 'valve_2': 7, 'digital_1': 'a:4:i',
                                     'digital_2': 'a:5:i', 'emergency': 5}}

        ini_file = ConfigParser()
        if os.path.isfile('settings/arduino.ini') is False:  # First run
            ini_file = default_ini(ini_file, default_params, False)
            print('Arquivo arduino.ini gerado em configurações padrão.')

        else:
            try:
                ini_file.read('settings/arduino.ini')
            except configparser.MissingSectionHeaderError:
                warnings.warn('Missing arduino sections, recreating settings/arduino.ini...')
                ini_file = default_ini(ini_file, default_params)

        if any(section not in default_params.keys() for section in ini_file.sections()):
            warnings.warn('Missing arduino sections, recreating settings/arduino.ini...')
            ini_file = default_ini(ini_file, default_params)

        for section in default_params.keys():
            if any(option not in default_params[section].keys() for option in ini_file.options(section)):
                warnings.warn('Missing arduino options, recreating settings/arduino.ini...')
                ini_file = default_ini(ini_file, default_params)

            ports[section] = {option: get_params(default_ports[section][option], ini_file.get(section, option))
                              for option in ini_file.options(section) if ini_file.get(section, option) != 'off'}

        return ports['INPUTS'], ports['OUTPUTS']


def get_params(option, value):
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


def default_ini(ini_file, ports, corrupted=True):
    file = 'settings/arduino.ini'
    if corrupted:
        os.remove(file)

    ini_file.read(file)
    ini_file['INPUTS'] = ports['INPUTS']
    ini_file['OUTPUTS'] = ports['OUTPUTS']

    with open(file, 'w+') as config_file:
        ini_file.write(config_file)
    return ini_file
