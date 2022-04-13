

def start_connections(console, debugging):

    class ArduinoCon:
        def __init__(self, parameters):
            self.debugging = debugging

            if not self.debugging:
                console.put('_ ___ _ _ AOI {} - iniciando conexões externas _ _ ____')
                self._connection_verification()

            else:
                console.put('___ AOI {} - debugging, conexões externas ignoradas ___')

        def _connection_verification(self):
            pass

    class CamerasCon:
        def __init__(self, parameters):
            self.debugging = debugging

    return ArduinoCon('arduino'), CamerasCon('cameras')
