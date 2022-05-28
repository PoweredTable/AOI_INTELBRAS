import time
from connections import start_connections


class CoreClass:
    def __init__(self, only_saving):

        self.arduino, self.cameras = start_connections()

        self.only_saving = only_saving

        self.nome_placa, self.teste_iniciado = None, False


def inspection(console, only_saving):
    core_class = CoreClass(only_saving)

    while 1:
        time.sleep(1)
# [INPUTS]
# sens_1 = 0|>=|0.95
# sens_2 = off
# sens_3 = off
#
# [OUTPUTS]
# ctr_est = on
# pin_pne = on
# ctr_luz = on
# alr_est = on
# alr_mqn = on