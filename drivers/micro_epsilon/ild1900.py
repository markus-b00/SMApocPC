#
# This is a very simple sample following MEDAQLib.pdf section 4 Using MEDAQLib
#
# This is an adopted Sample from the original MEDAQLib documentation
# Changed for USB Converter and Lasersensor ILD1900
#

from drivers.micro_epsilon.MEDAQLib import MEDAQLib, ME_SENSOR, ERR_CODE
import json
from pathlib import Path


class ILD_1900:
    def __init__(self, comport, config_laser, serial_number):
        self.comport = comport
        self.sensor = MEDAQLib.CreateSensorInstance(ME_SENSOR.SENSOR_ILD1900)
        self.logging = False
        self.config_laser = config_laser
        self.serial_number = serial_number
        self.set_config()
        self.sensor.OpenSensor()



    def set_config(self):

        # setting all integer parameters from the json file onto the sensor
        for item, value in self.config_laser['int_params'].items():
            self.sensor.SetParameterInt(item, value)
        # setting all string parameters from the json file onto the sensor
        for item, value in self.config_laser['str_params'].items():
            self.sensor.SetParameterString(item, str(value))
        # write serial number from gui input
        self.sensor.SetParameterString('IP_SerialNumber', self.serial_number)

        #setting up comport
        self.sensor.SetParameterString("IP_Port", self.comport)
        #set up logging
        if self.logging:
            self.sensor.SetParameterInt("IP_EnableLogging", 1)
        else:
            self.sensor.SetParameterInt("IP_EnableLogging", 0)


    def get_last_values(self,n=1):
        if self.sensor.GetLastError() == ERR_CODE.ERR_NOERROR:
            # Check whether there's enough data to read in
            currently_available = self.sensor.DataAvail()
            # Check if DataAvail causes an Error
            # If data is available?
            if currently_available > 0:
                # Transfer/Move data from MEDAQLib's internal buffer to own buffer
                # transfered_data = self.sensor.TransferData(currently_available)
                transfered_data = self.sensor.Poll(n)
                scaled_data = transfered_data[1]
                return scaled_data
            else:
                return -1  # if no data available
        else:
            print(self.sensor.GetError())


    def get_info(self):
        return self.sensor.GetParameterString("IP_SerialNumber")

    def get_str_param(self, name):
        return self.sensor.GetParameterString(name, 16)



    def shut_down(self):
        # Release sensor instance when sensor is closed
        self.self.sensor.CloseSensor()
        self.sensor.ReleaseSensorInstance()
