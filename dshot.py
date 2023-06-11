# Translate to C if needed

import time
import micropython

# Calibrate (also try floats, idk if it'll work)
T1H = 5
T1L = 2
T0H = 2
T0L = 5

M1_PIN = _____
M2_PIN = _____

@micropython.viper
def write_speeds(m1: int, m2: int):
    for i in range(15, -1, -1):
        m1s = (m1 >> i) & 1
        m2s = (m2 >> i) & 1
        M1_PIN.value(1)
        M2_PIN.value(1)
        if m1s and m2s:
            time.sleep_us(T1H)
            M1_PIN.value(0)
            M2_PIN.value(0)
            time.sleep_us(T1L)
        elif m1s and not m2s:
            time.sleep_us(T0H)
            M2_PIN.value(0)
            time.sleep_us(T1H - T0H)
            M1_PIN.value(0)
            time.sleep(T1L)
        elif not m1s and m2s:
            time.sleep_us(T0H)
            M1_PIN.value(0)
            time.sleep_us(T1H - T0H)
            M2_PIN.value(0)
            time.sleep(T1L)
        elif m1s and m2s:
            time.sleep_us(T0H)
            M1_PIN.value(0)
            M2_PIN.value(0)
            time.sleep_us(T0L)

def mainloop():
    global M1_THROTTLE   # When translating to C, use FIFO
    global M2_THROTTLE
    while True:
        write_speeds(M1_THROTTLE, M2_THROTTLE)
