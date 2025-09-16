import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
import PyQt5.QtCore as qtc
from drivers.micro_epsilon.ild1900 import ILD_1900
from drivers.me_messsysteme.gsv3_usb import GSV3USB
from smapoc.gui import webcam_gui
import logging
import smapoc.ids as ids
import struct
import numpy as np
import sys
import cv2


logging.getLogger(__name__)


class SMAPOCWorker(QThread):
    name = 'SMAPOC'
    data_received = pyqtSignal(int, list)  # id + Signal to send received binary data
    error_signal = pyqtSignal(str)  # Signal for error messages
    send_data_signal = pyqtSignal(int, bytes)  # id + Signal to receive binary data from GUI
    send_status = pyqtSignal(list)

    def __init__(self, port, baudrate=250000, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.serial = None
        self.id = 999
        self.timer = qtc.QTimer()
        self.send_data_signal.connect(self.write_data)

    def run(self):
        logging.debug('SMAPOC run is called')
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.5)
            self.error_signal.emit(f"Connected to {self.port}")
            self.send_data_signal.connect(self.write_data)  # Connect signal to slot

            while self.running:
                if self.serial.in_waiting == 16:
                    data = self.serial.read(self.serial.in_waiting)# Read raw bytes
                    data_parsed = list(struct.unpack('<8h', data))
                    self.data_received.emit(self.id, data_parsed)  # Send raw bytes to GUI
                    logging.debug(f'received 16bytes: {data_parsed}')

                elif (self.serial.in_waiting > 0) and (self.serial.in_waiting < 16):
                    data = self.serial.read(self.serial.in_waiting)
                    logging.debug(f'received:{data}')

        except serial.SerialException as e:
            self.error_signal.emit(f"Serial Error: {str(e)}")
            logging.debug(f'Error Serialport {e}')
        finally:
            if self.serial and self.serial.is_open:
                self.serial.close()
                self.error_signal.emit("Disconnected.")

    def write_data(self, my_id, data: bytes):
        """Writes raw binary data to the serial port."""
        self.id = my_id
        if self.serial and self.serial.is_open:
            self.serial.write(data)  # Send raw bytes
            logging.debug(f'write to smapoc: {data}')

    def self_test(self, myid=ids.SELFTEST_SMAPOC):
        logging.debug('handshake smapoc')
        self.timer.singleShot(1500, lambda: self.write_data(myid, 'uz\n'.encode('utf-8')))

    def read(self, myid):
        # it's better to use the write command, because the power as to be controlled anyway...
        self.write_data(myid, b'uz' + bytes([0, 0, 0, 0, 0, 0]))


    def stop(self):
        self.running = False
        self.wait()  # Ensure proper thread exit


class ForceWorker(QThread):
    name = 'FORCE'

    data_received = pyqtSignal(int, list)  # id + Signal to send received binary data
    error_signal = pyqtSignal(str)  # Signal for error messages
    send_data_signal = pyqtSignal(int, bytes)  # Signal to receive binary data from GUI

    def __init__(self, port, config, profile):
        super().__init__()
        self.port = port
        self.config = config
        self.profile = profile
        self.running = True
        self.my_force = None
        self.my_id = 999
        self.timer = qtc.QTimer()

    def run(self):
        self.my_force = GSV3USB(self.port)
        self.my_force.set_200hz()
        self.my_force.set_calib(self.profile)
        self.timer.singleShot(1000, self.my_force.start_transmission)
        logging.debug('Force sensor start transmission')


    def start_trans(self):
        self.my_force.start_transmission()

    def end_trans(self):
        self.my_force.end_transmission()

    def read(self, my_id=ids.FROM_FORCE):
        self.my_id = my_id
        #logging.debug(f'Read value {my_id}')
        if self.my_force is not None:
            #logging.debug('status OK')
            value = self.my_force.read_value()
            #logging.debug(f'read value {value}')
            self.data_received.emit(self.my_id, [value])
        else:
            self.error_signal.emit('No Force Sensor available')

    def calib(self):
        self.my_force.set_calib(self.profile)


    def stop(self):
        self.running = False
        self.wait()  # Ensure proper thread exit

    def self_test(self, myid=ids.SELFTEST_FORCE):
        self.timer.singleShot(3000, lambda: self.read(myid))



class LaserWorker(QThread):
    name = 'LASER'
    data_received = pyqtSignal(int, list)  # Signal to send received binary data
    error_signal = pyqtSignal(str)  # Signal for error messages

    def __init__(self, port, config, sn):
        super().__init__()
        self.port = port
        self.config = config
        self.sn = sn
        self.running = True
        self.myild = None
        self.timer = qtc.QTimer()


    def run(self):
        self.myild = ILD_1900(self.port, self.config.c_data['laser'], self.sn)
        # while self.running:
        #     if self.mode == ids.MODE_CONTI:
        #         data = self.myild.get_last_values(2)
        #         self.data_received.emit(ids.LASER_DATA, data)  # Send raw bytes to GUI
        #         logging.debug(data)

    def read(self, my_id=ids.FROM_LASER):
        self.my_id = my_id
        data = self.myild.get_last_values(2)
        if data:
            self.data_received.emit(self.my_id, data)  # Send raw bytes to GUI
        else:
            logging.warning('No Laser connected or configuration is wrong')


    def stop(self):
        self.running = False
        self.wait()  # Ensure proper thread exit

    def self_test(self, myid=ids.SELFTEST_LASER):
        self.timer.singleShot(3000, lambda: self.read(myid))

class Video(QThread):
    name = 'WEBCAM'
    frame_received = qtc.pyqtSignal(int, np.ndarray)  # Signal to send received binary data

    def __init__(self, cam_number):
        super().__init__()
        self.cam_number = cam_number

        self.running = True
        self.cap = None
        self.timer = None

    def run(self):
        logging.debug(f'cam no. {self.cam_number}')
        list_cams = self.find_cam()
        self.cap = cv2.VideoCapture(list_cams[-1])  # Open the first available camera
        logging.debug(f'selected cam no. {list_cams[-1]}')

        while self.cap.isOpened():
            ret, frame = self.cap.read()
            logging.debug('cam is open')
            if ret:
                logging.debug('frame received')
                self.frame_received.emit(ids.FROM_WEBCAM, frame)
        self.cap.release()
    def update_frame(self):
        logging.debug('update frame')
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
            frame = cv2.flip(frame, -1)  # Flip horizontally
            self.frame_received.emit(ids.FROM_WEBCAM, frame)
            logging.debug('Frame received emit')

    def stop(self):
        self.cap.release()
        self.running = False
        self.wait()  # Ensure proper thread exit

    def find_cam(self):
        available_cams = []
        for i in range(3):  # Try the first 10 indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():  # Check if the camera is available
                available_cams.append(i)
                cap.release()
        return available_cams


    def self_test(self, myid=ids.SELFTEST_WEBCAM):
        if self.cap.isOpened():
            logging.debug('Webcam alive')
        else:
            logging.debug('Webcam not responding')



