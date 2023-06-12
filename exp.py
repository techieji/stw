from machine import Pin, I2C
from micropython import viper, native
from rp2 import PIO, StateMachine, asm_pio
from math import cos
import struct
import utime

### Hardware & Constants ################################################################

M1 = Pin(____)
M2 = Pin(____)

# May need to set freq and duty cycle
RC_CH1 = PWM(Pin(____))
RC_CH2 = PWM(Pin(____))
RC_CH3 = PWM(Pin(____))
RC_CH4 = PWM(Pin(____))
RC_CH5 = PWM(Pin(____))
RC_CH6 = PWM(Pin(____))

i2c = I2C(0, sda=Pin(____), scl=Pin(____))
H3LIS331DL_ADDR = 0b0011000    # See page 12 sec 6.1.1 for details on LSB
MAX_G = 100     # I think? I believe this is modifiable
CONVERSION_FACTOR = 12 / (10**-6) * 32.174 * 2 * MAX_G / 4096      # g -> in/ms^2

DIAMETER = 8        # inches
R = DIAMETER // 2

### Global variables ####################################################################
# Angles are in radians (look, it's convenient, alright?)

heading = 0

direction = 0
magnitude = 0    # From 0-1000 where 2000 is top motor speed

### DShot ###############################################################################
# Copied from https://github.com/jrddupont/DShotPIO/blob/main/src/DShotPIO.py

@asm_pio(sideset_init=PIO.OUT_LOW, out_shiftdir=PIO.SHIFT_LEFT, autopull=True, pull_thresh=16)
def dshot():
    wrap_target()
    label("start")
    out(x, 1)            .side(0)    [1] # 2 cycle, Read the next bit into x register. Start at zero so the output is always low when waiting for new data
    jmp(not_x, "zero")   .side(1)    [2] # 3 cycles, Jump on x register
    jmp("start")         .side(1)    [2] # 3 cycles, "ONE" condition
    label("zero")
    jmp("start")         .side(0)    [2] # 3 cycles, "ZERO" condition
    wrap()

class DSHOT_SPEEDS:
    DSHOT150  = 1_200_000 #   150,000 bit/s * 8 cycle/bit
    DSHOT300  = 2_400_000 #   300,000 bit/s * 8 cycle/bit
    DSHOT600  = 4_800_000 #   600,000 bit/s * 8 cycle/bit
    DSHOT1200 = 9_600_000 # 1,200,000 bit/s * 8 cycle/bit

class DShotPIO:
    def __init__(self, stateMachineID, outputPin, dshotSpeed=DSHOT_SPEEDS.DSHOT150):
        self._sm = StateMachine(stateMachineID, dshot, freq=dshotSpeed, sideset_base=Pin(outputPin))
        self._sm.active(1)

    @viper
    def throttle(self, throttle):    
        # No use for 0-47
        throttle += 48
        throttleWithTelemetry = throttle << 1
        crc = (throttleWithTelemetry ^ (throttleWithTelemetry >> 4) ^ (throttleWithTelemetry >> 8)) & 0x0F
        dShotPacket = (throttleWithTelemetry << 4) | crc
        rightPaddedPacket = dShotPacket << 16
        self._sm.put(rightPaddedPacket)

### Motor control #######################################################################

@native
def motor_control():
    m1 = DShotPIO(0, M1)
    m2 = DShotPIO(1, M2)
    # Arming sequence is implicit (in position tracker)
    while True:
        baseline = 2000 - magnitude
        s1 = baseline + int(magnitude * math.cos(heading - direction))
        s2 = baseline - int(magnitude * math.cos(heading - direction))
        m1.throttle(s1)    # May have to interleave, but fingers crossed
        m2.throttle(s2)

### Position tracker ####################################################################

@viper
def get_accel():
    # See: https://github.com/mattytrentini/MicroPython-LIS3DH/blob/master/lis3dh.py#L165
    x, y, z = struct.unpack('<hhh', i2c.readfrom_mem(0b10101000, 6))
    x = x * CONVERSION_FACTOR
    y = y * CONVERSION_FACTOR
    z = z * CONVERSION_FACTOR
    mag = sqrt(x**2 + y**2 + z**2)
    return mag

def update_controller_direction():
    global direction, magnitude
    ch3 = RC_CH3.duty_u16()
    ch4 = RC_CH4.duty_u16()
    direction = math.atan(ch3/ch4)    # TODO: check order
    magnitude = sqrt(ch3**2 + ch4**2) * 900 / 65535
    # Really high magnitudes cause high loads (prediction)

@viper
def update_heading(a: float, dt: float):    # MAY lose precision over time
    global heading
    s = sqrt(a*R)
    heading += s*dt / R    # Consider implementing wrap-around logic

def position_tracker():
    utime.sleep(1)       # Arming sequence (assuming motor control is running)
    while True:
        t = utime.ticks_ms()
        update_controller_direction()
        update_heading(get_accel(), utime.ticks_diff(utime.ticks_ms(), t))

### "Oh yeah, it's all coming together" #################################################

_thread.start_new_thread(motor_control, ())
position_tracker()
