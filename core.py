import time
from connections import start_connections


class CoreClass:
    def __init__(self, console, debugging, only_saving):

        self.arduino, self.cameras = start_connections(console, debugging)

        self.debugging = debugging
        self.only_saving = only_saving

        self.nome_placa, self.teste_iniciado = None, False


def inspection(console, debugging, only_saving):
    core_class = CoreClass(console, debugging, only_saving)

    i = 0
    while 1:
        console.put(str(i))
        i += 1
        time.sleep(1)









