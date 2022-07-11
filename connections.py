from ini_files import get_port_c
class ArduinoCon:
    def __init__(self, parameters):
        pass

    def _connection_verification(self):
        pass


def clean_up_pins(signal='analog'):
    if signal == 'digital':
        pass
    return {0: False, 1: False, 2: False, 3: False, 4: False, 5: False, 6: False, 7: False}


class CamerasCon:
    def __init__(self, parameters):
        pass


def start_connections():
    return ArduinoCon('arduino'), CamerasCon('cameras')
