import smapoc.ids as ids
import PyQt5.QtCore as qtc
import struct

class Power(qtc.QObject):
    def __init__(self, parent, communicator, sma_channels):
        super().__init__()
        self.parent = parent
        self.communicator = communicator
        self.communicator.smapoc_mode_changed.connect(self.update_sampoc_mode)
        self.power_vec = [0, 0, 0, 0, 0, 0]
        self.sma_channels = sma_channels
        self.smapoc_mode = self.communicator.get_smapoc_mode()

    def update_sampoc_mode(self):
        self.smapoc_mode = self.communicator.get_smapoc_mode()


    def get_power_sine_msg(self):
        self.update_power_vec_sine()
        msg = self.make_msg()
        return msg

    def get_power_direct_msg(self):
        msg = self.make_msg()
        return msg

    def update_power_vec_direct(self, pow_vec):
        self.power_vec = pow_vec


    def update_power_vec_sine(self):
        for name, channel in self.sma_channels.channels.items():
            self.power_vec[ids.CHANNEL_MAPPING[name]] = int(abs(channel.update_sine()))
        return self.power_vec

    def make_msg(self):
        start = b'uz'
        status = bytes([self.smapoc_mode, 0])  #22
        power = struct.pack('6H', *self.power_vec)
        #suffix = bytes([14, 15, 16, 17, 18, 19, 20, 21])  #00
        return start + status + power   # +suffix


