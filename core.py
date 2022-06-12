import time
from connections import start_connections


class CoreClass:
    def __init__(self, only_saving):

        self.arduino, self.cameras = start_connections()

        self.only_saving = only_saving

        self.nome_placa, self.teste_iniciado = None, False


def inspection(console, board):
    core_class = CoreClass('')

    while 1:
        time.sleep(10)
