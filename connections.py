
class ArduinoCon:
    def __init__(self, debugging, parameters):
        self.debugging = debugging

        if not self.debugging:
            print('_ Carregamento padrão, iniciando conexões externas _')
            self._connection_verification()

        else:
            print('____ AOI debugging, conexões externas ignoradas ____')

    def _connection_verification(self):
        pass


class CamerasCon:
    def __init__(self, debugging, parameters):
        self.debugging = debugging


def start_connections(debugging):
    return ArduinoCon(debugging,'arduino'), CamerasCon(debugging, 'cameras')
