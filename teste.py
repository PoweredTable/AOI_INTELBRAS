import time

import keyboard
import pyfirmata
from pyfirmata import util

arduino = pyfirmata.Arduino('COM5')
it = util.Iterator(arduino)
it.start()
time.sleep(1)

status = 0
can_change = True
while 1:
    if keyboard.is_pressed('enter') and can_change:
        print('keyboard was pressed')
        print(status)
        arduino.digital[6].write(status)
        status = 0 if status == 1 else 1
        can_change = False

    if keyboard.is_pressed('space'):
        can_change = True

