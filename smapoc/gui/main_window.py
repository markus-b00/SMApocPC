import pandas as pd
from PyQt5 import QtCore as qtc
from PyQt5 import QtWidgets as qtw
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from ..gui.UI_main_window1 import Ui_MainWindow
from ..gui.device_wizard import DeviceWizard, StatusTable
from ..gui.sma_channels import SMAChannels
from ..gui.dialogs import DialogPlotSelector
from smapoc import ids as ids

from ..model import calc, data, data_collecter, sma_power, data_handler, communicator
from ..gui import webcam_gui, config_selector

from ..gui.live_plotter import LivePlot
from ..gui.stiffness_plotter import StiffnessPlot
from ..gui.module_plotter import ScriptExecutor
import time
import struct
import logging
import datetime as dt
import os
from pathlib import Path


FORMAT = '%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s'
#FORMAT = '%(asctime)s %(message)s'
filnam = dt.datetime.now().strftime('%y%m%d_%H_%M_%S') + '_logfile.log'
#filename = 'logfile.log'
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger(__name__)


class SMApocMain(qtw.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.list_comports = None
        self.power_vec = [0, 0, 0, 0]


        self.startup_timer = qtc.QTimer()

        self.data_handler = data_handler.DataHandler()
        self.communicator = communicator.Communicator(self.data_handler)
        #self.wizard = DeviceWizard(self)
        #self.wizard.on_accept.connect(self.wizard_finished)

        # Current file's directory: project/gui/
        # Path to the current file
        current_file = Path(__file__)

        # Get the location of the config file
        json_path = self.data_handler.config.c_data['path_config']
        self.config_selector = config_selector.ConfigDialog(self.data_handler, config_file=Path(json_path))

        self.startup_timer.singleShot(1000, self.open_config_selector)
        self.sma_channels = None
        self.sma_power = None
        self.stiffness_plotter = None
        self.sequence_plotter = None
        self.webcam_win = None
        self.recorder = None
        self.loader = config_selector.ConfigLoader(self, self.communicator)
        self.loader.loader_finished.connect(self.wizard_finished)

        self.btn_add_plot.clicked.connect(self.add_plot)
        self.btn_play.clicked.connect(self.start_play)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_stop.clicked.connect(self.stop_play)

        self.spinBox_timer_plot.valueChanged.connect(self.change_cycle_time)
        self.spinBox_timer_request.valueChanged.connect(self.change_cycle_time)
        self.spinBox_timer_datahandler.valueChanged.connect(self.change_cycle_time)

        self.comboBox_smapoc_mode.currentIndexChanged.connect(self.change_smapoc_mode)

        self.myplots = {}
        self.actionConfig.triggered.connect(self.open_config_selector)
        #self.actionBSAT2_1.triggered.connect(lambda: self.open_stiffness_plotter('BSA-T-2.1'))
        #self.actionBSAT2_2.triggered.connect(lambda: self.open_stiffness_plotter('BSA-T-2.2'))
        #self.actionASA_T_2.triggered.connect(lambda: self.open_stiffness_plotter('ASA-T-2'))
        #self.actionASA_T_3.triggered.connect(lambda: self.open_sequence_plotter('ASA-T-3'))
        #self.actionAMA_T_2.triggered.connect(lambda: self.open_sequence_plotter('AMA-T-2'))


    def change_smapoc_mode(self):
        text = self.comboBox_smapoc_mode.currentText()
        if text == 'POWER':
            self.communicator.set_smapoc_mode(ids.POWER)
        elif text == 'CURRENT':
            self.communicator.set_smapoc_mode(ids.CURRENT)


    def open_sequence_plotter(self, name):
        self.sequence_plotter = ScriptExecutor(self, self.communicator, self.data_handler, self.recorder)
        self.sequence_plotter.show(name)

    def open_stiffness_plotter(self, name):
        self.stiffness_plotter = StiffnessPlot(self, self.data_handler, self.communicator)
        self.stiffness_plotter.show(name)


    def open_config_selector(self):
        if self.config_selector.exec_() == qtw.QDialog.Accepted:
            self.loader.load(self.config_selector.selected_config)



    def start_play(self):
        self.change_cycle_time()
        self.communicator.start_requesting()
        self.data_handler.plot_status.emit(True)
    def pause(self):
        self.communicator.stop_requesting()
        self.data_handler.plot_status.emit(False)
        self.btn_stop.setEnabled(True)

    def stop_play(self):
        self.communicator.stop_requesting()
        self.data_handler.plot_status.emit(False)
        self.data_handler.data.to_csv("my_snapshot.csv", decimal=',', sep=';')
        self.data_handler.data_clear()


    def wizard_finished(self):
        logging.debug(self.communicator.devices.keys())
        for key in self.communicator.devices.keys():
            if key == 'smapoc':
                self.sma_channels = SMAChannels(self)
                self.sma_power = sma_power.Power(self, self.communicator, self.sma_channels)
                self.communicator.add_power_obj(self.sma_power)
                self.communicator.devices[key].self_test(ids.FROM_SMAPOC)
            #if key == 'force':
            #    self.communicator.devices[key].self_test(ids.FROM_FORCE)
            #if key == 'laser':
            #    self.communicator.devices[key].self_test(ids.FROM_LASER)
            if key == 'webcam':
                self.webcam_win = webcam_gui.CameraWindow(self, self.communicator.devices['webcam'])
                self.communicator.devices['webcam'].frame_received.connect(self.webcam_win.update)
                self.recorder = data_handler.Recorder(self.communicator)
        logging.debug(self.data_handler.data)
        self.communicator.data_handler.transfer_collected()

    def add_plot(self):
        self.communicator.data_handler.transfer_collected()
        plot_sel = DialogPlotSelector(self, self.data_handler)
        if plot_sel.exec_() == qtw.QDialog.Accepted:
            dialog_data = plot_sel.get_data()
            self.myplots[len(self.myplots)] = LivePlot(self,
                                                       self.data_handler,
                                                       **dialog_data)

        #self.status_table = StatusTable(self, self.gridLayout_3)
        #self.dev_observer.state_changed.connect(self.status_table.update_status_table)


        #self.radioButton_Sine.clicked.connect(self.activate_sine)

        #self.btnWizard.clicked.connect(self.wizard.show)
        #self.webcam = webcam.VideoWindow(self.plt_video)



        #self.setup()

    def change_cycle_time(self):
        value_data = self.spinBox_timer_datahandler.value()
        value_request = self.spinBox_timer_request.value()
        value_plot = self.spinBox_timer_plot.value()

        self.data_handler.set_interval(value_data)
        self.data_handler.plot_interval.emit(value_plot)
        self.communicator.set_interval(value_request)



    # def setup_data_manager(self):
    #     logging.debug('Setup data')
    #
    #     self.sma_channels = SMAChannels(self, self.horizontalLayout_single_channels)
    #     self.sma_channels.clear()
    #     self.sma_channels.add_channel('CH1')
    #     self.sma_channels.add_channel('CH2')
    #     self.sma_channels.add_channel('CH3')
    #     self.sma_channels.add_channel('CH4')
    #     self.sma_channels.add_channel('BRAKE')
    #     self.power = sma_power.Power(self, self.wizard.connector_smapoc.thread, self.sma_channels)
    #     self.sma_channels.update_power.connect(self.power.write_power)
    #
    #     self.data_manager = data_collecter.Datacollector(self,
    #                                                      self.wizard.connector_smapoc.thread,
    #                                                      self.wizard.connector_laser.thread,
    #                                                      self.wizard.connector_force.thread,
    #                                                      self.sma_channels)
    #     self.live_plot = LivePlot(self, self.plt_live, self.data_manager)
    #
    #     self.btn_start_plot.clicked.connect(self.data_manager.start_collecting)
    #     self.btn_start_plot.clicked.connect(self.live_plot.start_plotting)
    #     self.btn_stop_plot.clicked.connect(self.data_manager.mytimer.stop)
    #     self.btn_stop_plot.clicked.connect(self.live_plot.stop_plotting)
    #     self.btn_clear_plot.clicked.connect(self.save_df)



    def save_df(self):
        self.data_manager.data.to_csv('my_csv.csv')

    def update_plot(self):
        self.live_plot.update_plot()

    def activate_sine(self):
        if self.radioButton_Sine.isChecked():
            self.groupBox_sine.setEnabled(True)
        else:
            self.groupBox_sine.setDisabled(True)

    def closeEvent(self, event):
        try:
            self.wizard.connector_smapoc.thread.stop()
            self.wizard.connector_smapoc.thread.quit()

            self.wizard.connector_laser.thread.stop()
            self.wizard.connector_laser.thread.quit()

            self.wizard.connector_force.thread.stop()
            self.wizard.connector_force.thread.quit()
        except AttributeError as e:
            logging.info('Trying to close thread that not exists')



        self.close()
        event.accept()

    def setup(self):
        self.startup_timer.singleShot(500, self.wizard.show)
        # self.list_comports = list_comports()
        # self.comboComport.clear()
        # for port, desc in reversed(self.list_comports.items()):
        #     self.comboComport.addItem(f"{port}", port)


    # def toggle_connection(self):
        # """Start or stop serial communication."""
        # if not self.connected:
        #     selected_port = self.list_comports[self.comboComport.currentText()]
        #     print(selected_port)
        #     if not selected_port:
        #         self.text_area.append("No serial port selected.")
        #         return
        #     self.serial_thread = SerialThread(selected_port, 115200)
        #     self.serial_thread.data_received.connect(self.display_data)
        #     self.serial_thread.start()
        #
        #     self.btnConnect.setText("Disconnect")
        #     self.connected = True
        # else:
        #     if self.serial_thread:
        #         self.serial_thread.stop()
        #     self.btnConnect.setText("Connect")
        #     self.connected = False



    # @pyqtSlot(bytes)
    # def display_data(self, data: bytes):
    #     """Display received binary data in the text area as text and hex."""
    #     mylist = []
    #     if len(data) >= 8:
    #         mylist = list(calc.make_16_bit_list(data))
    #         self.textEdit_logging.append(f"{mylist}")
    #         line_data = {'res1': mylist[2],
    #                      'res2': mylist[3],
    #                      'pow1': self.power_vec[1],
    #                      'pow2': self.power_vec[2],
    #                      'pow3': self.power_vec[3]}
    #         self.data.add_line(line_data)
    #         self.live_plot.update_res_plot()


    def send_command(self):
        text_in = self.lineEdit_command.text()
        my_int_list = [int(item) for item in text_in.split(',')]
        self.power_vec = my_int_list
        b0 = struct.pack('<4H', *my_int_list)
        prefix = bytes('uz', 'utf-8')
        com_line = prefix + b0
        print(len(com_line))
        if len(com_line) == 10:
            self.serial_thread.send_data_signal.emit(com_line)


