from machine import Pin, I2C
from micropython import viper, native
from rp2 import PIO, StateMachine, asm_pio
from math import cos
from decimal import Decimal
import struct
import utime

### Hardware & Constants ################################################################
# Motor pins:
#   M1: 0
#   M2: 1
# Receiver pins:
#   ch1: 2
#   ch2: 3
#   ch3: 4
#   ch4: 5
# Accelerometer pins:
#   sda: 8
#   scl: 9

M1 = Pin(0)
M2 = Pin(1)

# May need to set freq and duty cycle
RC_CH1 = PWM(Pin(2))
RC_CH2 = PWM(Pin(3))
RC_CH3 = PWM(Pin(4))
RC_CH4 = PWM(Pin(5))

i2c = I2C(0, sda=Pin(8), scl=Pin(9))
H3LIS331DL_ADDR = 0b0011000    # See page 12 sec 6.1.1 for details on LSB
CTRL_REG1_ADDR = 0x20
OUT_X_L_ADDR = 0x28
MAX_G = 100     # This is modifiable using CTRL_REG4, but is left at default of 100 gs
CONVERSION_FACTOR = Decimal(12) / (10**-9) * Decimal(32.174) * 2 * MAX_G / 4096      # g -> in/us^2

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
    def _throttle(self, throttle):
        throttleWithTelemetry = throttle << 1
        crc = (throttleWithTelemetry ^ (throttleWithTelemetry >> 4) ^ (throttleWithTelemetry >> 8)) & 0x0F
        dShotPacket = (throttleWithTelemetry << 4) | crc
        rightPaddedPacket = dShotPacket << 16
        self._sm.put(rightPaddedPacket)
        
    def throttle(self, throttle): self._throttle(throttle + 48)
    def arm(self): self._throttle(0)    # Has to run continuously for 200 ms (I think?)

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

def setup_accel():
    i2c.writeto_mem(H3LIS331DL_ADDR, CTRL_REG1_ADDR, 0b001_11_111 .to_bytes(1, 'little'))

@viper
def get_accel(n=1):    # Average over n iterations
    x, y, z = 0, 0, 0
    for _ in range(n):
        _x, _y, _z = struct.unpack('<hhh', b''.join(i2c.readfrom_mem(H3LIS331DL_ADDR, OUT_X_L_ADDR + i, 1) for i in range(6)))
        x += _x
        y += _y
        z += _z
    z /= n
    z -= 1    # Remove gravitational force
    x *= CONVERSION_FACTOR / n
    y *= CONVERSION_FACTOR / n
    z *= CONVERSION_FACTOR
    mag = (x**2 + y**2 + z**2).sqrt()
    return mag

def update_controller_direction():
    global direction, magnitude
    ch3 = RC_CH3.duty_u16()
    ch4 = RC_CH4.duty_u16()
    direction = math.atan(ch3/ch4)    # TODO: check order
    magnitude = (ch3**2 + ch4**2).sqrt() * 900 / 65535
    # Really high magnitudes cause high loads (prediction)

@viper
def update_heading(a: Decimal, dt: int):    # MAY lose precision over time
    global heading
    s = (a*R).sqrt()
    heading += s*dt / R    # Consider implementing wrap-around logic

def position_tracker():
    utime.sleep(1)       # Arming sequence (assuming motor control is running)
    while True:
        t = utime.ticks_us()
        update_controller_direction()
        update_heading(get_accel(), utime.ticks_diff(utime.ticks_us(), t))

### "Oh yeah, it's all coming together" #################################################

setup_accel()
_thread.start_new_thread(motor_control, ())
position_tracker()
