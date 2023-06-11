import _thread
import math

import dshot
from accelerometer import get_heading, update_heading

M1_THROTTLE = 48    # 48 is 0
M2_THROTTLE = 48

_thread.start_new_thread(dshot.mainloop, ())

while True:
    a = update_and_get_heading()
    m1
