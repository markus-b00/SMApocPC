import serial
from serial.serialutil import SerialException
import logging
logging.getLogger(__name__)


class SMAPOC:
    """ This version uses the SMApoc generation 2 with 6 channels and the firmware version XXX from 2025/04/11
    by Philip Frenzel. The board has 2 modes: An openloop current driven mode and a closedloop power driven mode.
    It uses the programming port of the arduino due to communicate over serial port"""

    def __init__(self, port, baudrate=250000):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connect()

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.5)
            logging.info(f'SMApoc serialport {self.port} opened')
        except SerialException as e:
            logging.warning(e)

    def disconnect(self):
        if self.serial.is_open:
            self.serial.close()
            logging.info('SMApoc serialport closed')

    def read(self) -> bytes:
        in_waiting_bytes = self.serial.in_waiting
        if in_waiting_bytes == 16:
            data_in = self.serial.read(in_waiting_bytes)
            return data_in
        else:
            logging.warning(f'wrong number of in bytes received: {in_waiting_bytes}')
            return None



    def write_data(self, data: bytes) -> None:
        """Writes raw binary data to the serial port."""
        if self.serial and self.serial.is_open:
            self.serial.write(data)  # Send raw bytes
            logging.debug(f'data:{data}')

