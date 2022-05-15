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
        default_ports = {'INPUTS': {'opt': ['sens_1', 'sens_2', 'sens_3'],
                                    'def': ['0|>|0.1', '1|>|0.1', '2|>|0.1']},
                         'OUTPUTS': {'opt': ['ctr_est', 'pin_pne', 'ctr_luz', 'alr_est', 'alr_mqn'],
                                     'def': [3, 8, 6, 2, 'off']}}
        ini_file = ConfigParser()
        if os.path.isfile('settings/arduino.ini') is False:  # First run
            ini_file = default_ini(ini_file, default_ports, False)
            print('Arquivo arduino.ini gerado em configurações padrão.')

        else:
            try:
                ini_file.read('settings/arduino.ini')
            except configparser.MissingSectionHeaderError:
                warnings.warn('Missing arduino sections, recreating settings/arduino.ini...')
                ini_file = default_ini(ini_file, default_ports)

        if any(section not in ('INPUTS', 'OUTPUTS') for section in ini_file.sections()):
            warnings.warn('Missing arduino sections, recreating settings/arduino.ini...')
            ini_file = default_ini(ini_file, default_ports)

        for section in ('INPUTS', 'OUTPUTS'):
            options = default_ports[section]['opt']
            if options != ini_file.options(section):
                warnings.warn('Missing arduino options, recreating settings/arduino.ini...')
                ini_file = default_ini(ini_file, default_ports)

            defaults = default_ports[section]['def']
            for option, default in zip(options, defaults):
                params = ini_file.get(section, option)

                is_valid = validate_ports(params, section)
                if is_valid is False:
                    warnings.warn(f"Option {option} in [{section}] doesn't have a "
                                  f"valid value, using default value {default} instead!")
                    params = default

                elif is_valid is None:
                    params = False
                    ports[section][option] = params
                    continue

                if section == 'INPUTS':
                    port, opr, value = params.split('|')
                    params = [f'a:{port}:i', return_operators(opr), float(value)]

                ports[section][option] = params

        check_duplicates(ports)
        return ports['INPUTS'], ports['OUTPUTS']


def return_operators(opr=None):
    operators_dict = {'>': operator.gt, '<': operator.lt, '>=': operator.ge,
                      '<=': operator.le, '==': operator.eq}
    if opr is None:
        return operators_dict
    return operators_dict[opr], opr


def validate_ports(params, section):
    if params != '':  # params can't be empty
        if params != 'off':  # it could be 'off', meaning that the port is not active
            if section == 'INPUTS':
                params = params.split('|')
                if len(params) == 3 and type(params) is list:
                    port, cond, value = params  # the params are: analogical port, operator (condition) and float value
                    try:
                        if port.isnumeric() and any(cond == opr for opr in
                                                    ('>=', '<=', '>', '<', '==')) and type(float(value)) is float:
                            if int(port) <= 7:
                                return True  # maximum analogical ports of Arduino Nano
                    except ValueError:
                        pass
            else:
                if params.isnumeric():  # digital section doesn't need conditional activation
                    if int(params) <= 13:
                        return True  # maximum digital ports of Arduino Nano
        else:
            return None
    return False


def check_duplicates(ports):
    seen = []
    for value in ports['INPUTS'].values():
        if value is not False:
            if value[0] in seen:
                raise IOError('Configuration file arduino.ini has duplicated analogical values!')
            seen.append(value[0])

    seen = []
    for value in ports['OUTPUTS'].values():
        if value is not False:
            if value in seen:
                raise IOError('Configuration file arduino.ini has duplicated digital values!')
            seen.append(value)


def default_ini(ini_file, ports, corrupted=True):
    # cria um arquivo arduino.ini de acordo com a placa padrão
    file = 'settings/arduino.ini'
    if corrupted:
        os.remove(file)

    ini_file.read(file)
    inputs, outputs = ports['INPUTS'], ports['OUTPUTS']

    ini_file['INPUTS'] = {option: default for option, default in zip(inputs['opt'], inputs['def'])}
    ini_file['OUTPUTS'] = {option: default for option, default in zip(outputs['opt'], outputs['def'])}

    with open(file, 'w+') as config_file:
        ini_file.write(config_file)
    return ini_file
