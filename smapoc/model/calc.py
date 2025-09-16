import struct
import numpy as np


# Unpack as little-endian unsigned 16-bit integers
def make_16_bit_list(bytelist):
    return struct.unpack('<4H', bytelist[0:8])


def calc_sine(t, freq, amp, offset, phase):
    temp_result = amp * np.sin(2*np.pi*freq*t+phase) + offset
    if temp_result < 0:
        temp_result = 0
    return int(temp_result)

