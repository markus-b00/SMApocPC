import logging

import serial
import serial.tools.list_ports


class ComPortSearcher:
    def __init__(self, data_handler):
        self.data_handler = data_handler
        self.ports = self.get_list_comports()

    def get_laser(self):
        output = {}
        for port in self.get_list_comports():
            if port.serial_number:
                if port.serial_number[0:-1] in self.data_handler.config.c_data['laser']['IP_SerialNumbers'].values():
                    output[port.name] = (port.description, 'ILD_1900')
        return output

    def get_force(self):
        serial_numbers = self.data_handler.config.c_data['force_amplifier_sn']
        output = {}
        for port in self.get_list_comports():
            if port.serial_number in serial_numbers.keys():
                output[port.name] = (port.serial_number, serial_numbers[port.serial_number])
        return output

    def get_smapoc(self):
        output = {}
        for port in self.get_list_comports():
            if any(elem in port.description for elem in ['USB Serial Device','Serielles USB-Gerät', 'Arduino']):   # Win11 and Win10 difference
                output[port.name] = (port.description, 'SMAPOC 6CH')
        return output

    @staticmethod
    def get_list_comports() -> list:
        return serial.tools.list_ports.comports()

