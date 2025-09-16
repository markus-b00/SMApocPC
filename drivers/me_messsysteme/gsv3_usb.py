import serial
import struct
import numpy as np
import platform
import json
from pathlib import Path
import logging
logging.getLogger(__name__)


class ForceMeasurementConverterN:
    def __init__(self):
        self.F_n = 0.5  # Nominal Force
        self.S_n = 0.6  # Output  @ nominal Force
        self.u_e = 2  # Amplifier Gain

    def load_sensor_profile(self, profile):
        self.F_n = profile['fn']  # Nominal Force
        self.S_n = profile['sn']  # Output  @ nominal Force
        self.u_e = profile['u_e']  # Amplifier Gain
        print(f'Fn:{self.F_n} ,Sn:{self.S_n} ,ue:{self.u_e}')






    def convertValue(self, value):
        A = struct.unpack('>H', value)[0]
        # return (A - 0x8000) * (self.F_n / self.S_n) * (self.u_e / 0x8000)
        return self.F_n / self.S_n * ((A - 0x8000) / 0x8000) * self.u_e  # Scale 16bit number from -1 to 1


class GSV3USB:
    def __init__(self, com_port, baudrate=38400):
        self.sensor = serial.Serial(com_port,
                                    baudrate)
        self.converter = ForceMeasurementConverterN()



    def get_all(self, profile=0):
        self.sensor.write(struct.pack('bb', 9, profile))

    def save_all(self, profile=2):
        self.sensor.write(struct.pack('bb', 10, profile))

    def start_transmission(self):
        self.sensor.write(b'\x24')

    def stop_transmission(self):
        self.sensor.write(b'\x23')

    def set_zero(self):
        self.sensor.write(b'\x0C')

    def set_offset(self):
        self.sensor.write(b'\x0E')

    def set_bipolar(self):
        self.sensor.write(b'\x14')

    def set_unipolar(self):
        self.sensor.write(b'\x15')

    def get_serial_nr(self):
        self.stop_transmission()
        self.sensor.reset_input_buffer()
        self.sensor.write(b'\x1F')
        ret = self.sensor.read(8)
        self.start_transmission()
        return ret

    def set_mode(self, text=False, max=False, log=False, window=False):
        x = 0
        if(text):
            x = x | 0b00010
        if(max):
            x = x | 0b00100
        if(log):
            x = x | 0b01000
        if(window):
            x = x | 0b10000
        self.sensor.write(struct.pack('bb', 0x26, x))

    def set_calib(self, profile):
        self.converter.load_sensor_profile(profile)

    def get_calib(self):
        return self.converter.F_n, self.converter.S_n, self.converter.u_e

    def set_50hz(self):
        self.sensor.write(b'\x8A\x07\xFC\xF3')

    def set_100hz(self):
        self.sensor.write(b'\x8A\x06\xFC\xF3')

    def set_200hz(self):
        self.sensor.write(b'\x8A\x05\xFC\xF3')

    def set_500hz(self):
        self.sensor.write(b'\x8A\x04\xFC\xF3')

    def set_800hz(self):
        self.sensor.write(b'\x8A\x03\xFC\xF3')




    def get_mode(self):
        self.stop_transmission()
        self.sensor.write(b'\x27')
        ret = self.sensor.read(1)
        self.start_transmission()
        return ret

    def get_firmware_version(self):
        self.stop_transmission()
        self.sensor.reset_input_buffer()
        self.sensor.write(b'\x27')
        ret = self.sensor.read(2)
        self.start_transmission()
        return ret

    def get_special_mode(self):
        self.stop_transmission()
        self.sensor.reset_input_buffer()
        self.sensor.write(b'\x89')
        ret = self.sensor.read(2)
        self.start_transmission()
        return ret

    def set_special_mode(self):
        pass

    def read_value(self):
        self.sensor.reset_input_buffer()
        self.sensor.read_until(b'\xA5')
        read_val = self.sensor.read(2)
        if len(read_val) == 2:
            return self.converter.convertValue(read_val)
        else:
            return -1

    def clear_maximum(self):
        self.sensor.write(b'\x3C')

    def clear_buffer(self):
        self.sensor.write(b'\x25')


def main():
    dev = GSV3USB('COM3')
    try:
        while True:
            print(dev.read_value())
    except KeyboardInterrupt:
        print("Exiting")
        return


if __name__ == "__main__":
    main()
