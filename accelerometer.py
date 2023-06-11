import machine

SCL_PIN = None    # Pin objects
SDA_PIN = None

i2c = I2C(scl=SCL_PIN, sda=SDA_PIN)

i2c.scan()

# Do stuff hopefully

def get_heading():
    pass

def update_heading():
    pass
