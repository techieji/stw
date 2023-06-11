from machine import Pin, PWM

# Channel pins
CH1 = PWM(Pin(_____, Pin.IN))
CH2 = PWM(Pin(_____, Pin.IN))
CH3 = PWM(Pin(_____, Pin.IN))
CH4 = PWM(Pin(_____, Pin.IN))

def get_controller() -> tuple:  # Returns ints in range 0-65535
    return (CH1.duty_u16(), CH2.duty_u16(), CH3.duty_u16(), CH4.duty_u16())
