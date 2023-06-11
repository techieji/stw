# Translate to C if needed

import utime
import micropython
import gc

# Calibrate
# switch to utime.ticks_cpu()
# Pico clock frequency: 125 MHz
T1H = 625 # 5 us
T1L = 209 # 1.67 us
T0H = 313 # 2.5 us
T0L = 521 # 4.17 us

TOLERANCE = 20

M1_PIN = _____
M2_PIN = _____

def sleep_clock(n: int):
    c = utime.ticks_cpu()
    # Busy wait
    while utime.ticks_diff(utime.ticks_cpu(), c) - TOLERANCE < n: pass

@micropython.viper
def write_speeds(m1: int, m2: int):
    for i in range(15, -1, -1):
        m1s = (m1 >> i) & 1
        m2s = (m2 >> i) & 1
        M1_PIN.value(1)
        M2_PIN.value(1)
        if m1s and m2s:
            sleep_clock(T1H)
            M1_PIN.value(0)
            M2_PIN.value(0)
            sleep_clock(T1L)
        elif m1s and not m2s:
            sleep_clock(T0H)
            M2_PIN.value(0)
            sleep_clock(T1H - T0H)
            M1_PIN.value(0)
            sleep_clock(T1L)
        elif not m1s and m2s:
            sleep_clock(T0H)
            M1_PIN.value(0)
            sleep_clock(T1H - T0H)
            M2_PIN.value(0)
            sleep_clock(T1L)
        elif m1s and m2s:
            sleep_clock(T0H)
            M1_PIN.value(0)
            M2_PIN.value(0)
            sleep_clock(T0L)

def raw_speed_to_packet(s: float) -> int:
    pass

def mainloop():
    gc.disable()
    global M1_THROTTLE   # When translating to C, use FIFO
    global M2_THROTTLE
    while True:
        write_speeds(M1_THROTTLE, M2_THROTTLE)
