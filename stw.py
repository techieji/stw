# General reference: https://docs.micropython.org/en/latest/rp2/quickref.html
# Accelerometer library: https://github.com/adafruit/Adafruit_CircuitPython_LIS331

# Units (unless otherwise noted):
#   Length: inches
#   Time:   minute
#   Speed:  inches per minute

from math import pi, sin, sqrt
from collections import namedtuple
from time import time, sleep
from machine import Pin, PWM, Timer
from busio import I2C
import micropython
import _thread
import board
import gc

gc.disable()

### Constants ###############################

DELAY_TIME = 0            # As fast as possible    (in seconds)
DIAMETER = 8
MAX_RPM = 2000            # Not true max, but rather maximum sustainable rpm (cruising)

# DShot stuff
TOLERANCE = 20      # Number of clock cycles dshot can tolerate an error

# Number of clock cycles to wait for high and low
T1H = 625 # 5 us
T1L = 209 # 1.67 us
T0H = 313 # 2.5 us
T0L = 521 # 4.17 us

# idk what pull-up and pull-down are used for, so FIXME

M1_PIN = Pin(_____, Pin.OUT)    # idk what this and below should be, so just Pin for now
M2_PIN = Pin(_____, Pin.OUT)

# Using H3LIS331DL
SDA = Pin(_____, Pin.OUT)
SCL = Pin(_____, Pin.OUT)
ACCELEROMETER_I2C = I2C(sda=SDA, scl=SCL)

TRANSMITTER_CH1P = Pin(______, Pin.IN)
TRANSMITTER_CH2P = Pin(______, Pin.IN)
TRANSMITTER_CH3P = Pin(______, Pin.IN)
TRANSMITTER_CH4P = Pin(______, Pin.IN)

# May need to set freq and duty cycle
TRANSMITTER_CH1  = PWM(TRANSMITTER_CH1P)
TRANSMITTER_CH2  = PWM(TRANSMITTER_CH2P)
TRANSMITTER_CH3  = PWM(TRANSMITTER_CH3P)
TRANSMITTER_CH4  = PWM(TRANSMITTER_CH4P)

### Types ###################################

direction = namedtuple('direction', 'mag theta')
accelerometer_data = namedtuple('accelerometer_data', 'x y z')
raw_controller_data = namedtuple('raw_controller_data', 'ch1 ch2 ch3 ch4')    # Replace with actual names

### Global variables ########################

heading = 0

_m1_packet = 48
_m2_packet = 48

### I/O functions ###########################

def get_accelerometer() -> accelerometer_data:
    # TODO: use raw I2C
    return accelerometer_data(____________)

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

def dshot_mainloop():
    gc.disable()
    while True:
        write_speeds(_m1_packet, _m2_packet)

@micropython.native    # Maybe viper?
def make_dshot_packet(throttle: int, telemetry: int = 0):
    packet = (throttle << 1) | telemetry
    crc = 0     # CRC code copied from https://github.com/dmrlawson/raspberrypi-dshot/blob/master/dshotmodule.c
    packet_copy = packet
    for _ in range(3):
        crc ^= packet_copy
        packet_copy >>= 3
    crc &= 0xf
    packet = (packet << 4) | crc
    return packet

def set_raw_motor_speeds(s1: float, s2: float):
    # Docs I read: https://brushlesswhoop.com/dshot-and-bidirectional-dshot/
    global _m1_packet, _m2_packet
    s1i = int(s1 * (2**16 - 49))
    s2i = int(s2 * (2**16 - 49))
    _m1_packet = make_dshot_packet(s1i)
    _m2_packet = make_dshot_packet(s2i)

def set_motor_speeds(s1: float, s2: float):    # Uses proper speeds, not electric values
    ...     # Need to use trial and error

def get_raw_controller_data() -> raw_controller_data:
    return raw_controller_data(
        TRANSMITTER_CH1.duty_u16() / 65535,
        TRANSMITTER_CH2.duty_u16() / 65535,
        TRANSMITTER_CH3.duty_u16() / 65535,
        TRANSMITTER_CH4.duty_u16() / 65535
    )

### Logic ###################################

def acceleration_magnitude(acc: accelerometer) -> float:
    return sqrt(acc.x**2 + acc.y**2)      # I don't think there should be any z acceleration

def update_heading(dt: float, acc: accelerometer_data):     # Should work in the limit, but idk how quickly it'll lose precision
    global heading
    a = acceleration_magnitude(acc)
    R = DIAMETER / 2
    s = sqrt(a*R)
    heading += s*dt / R
    # TODO: test function on collisions!!!

def update_motor_speeds(d: direction):
    baseline = MAX_RPM * pi * DIAMETER - d.mag
    m1s =  d.mag * cos(heading - d.theta) + baseline
    m2s = -d.mag * cos(heading - d.theta) + baseline
    set_motor_speeds(m1s, m2s)

### Mainloop ################################
# Calculation and DShot run on separate cores

_thread.start_new_thread(dshot_mainloop, ())

t = time()
while True:
    dt = t - time()
    update_heading(dt, get_accelerometer())
    t = time()
    d = get_controller_direction()
    update_motor_speeds(d)
