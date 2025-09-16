import logging
import struct
from smapoc.gui.UI_device_wizard import Ui_Dialog
import smapoc.gui.webcam_gui as webcam
from smapoc.model.comport_handling import ComPortSearcher
from smapoc.gui.dialogs import LineDialog

from drivers.micro_epsilon.ild1900 import ILD_1900
from drivers.me_messsysteme.gsv3_usb import GSV3USB
from drivers.smapoc.smapoc_driver import SMAPOC

from smapoc import ids
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
import PyQt5.QtCore as qtc


class DeviceWizard(qtw.QDialog, Ui_Dialog):
    on_accept = qtc.pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~qtc.Qt.WindowContextHelpButtonHint) #get rid of the question mark
        self.stackedWidget.setCurrentIndex(0)

        self.port_searcher = ComPortSearcher(self.parent.data_handler)
        # assign buttons
        self.btn_skip_next.clicked.connect(self.clicked_next)
        self.btn_cancel.clicked.connect(self.close)
        self.btn_back.clicked.connect(self.clicked_prev)
        self.btn_smapoc_select.clicked.connect(self.select_smapoc)
        self.btn_laser_select.clicked.connect(self.select_laser)
        self.btn_force_select.clicked.connect(self.select_force)
        self.btn_cam_connect.clicked.connect(self.connect_webcam)


        self.text = ""
        self.timer = qtc.QTimer()
        self.cnt_smapoc = 0
        self.webcam_dict = None
        self.new_config = {}

        self.status = None
        self.onloading()


    def onloading(self):
        # Find SMAPOC
        smapoc = self.port_searcher.get_smapoc()
        populate_comports(self.comboBox_smapoc_select_com, self.btn_smapoc_select, smapoc)

        # Find ME Force sensors
        force = self.port_searcher.get_force()
        populate_comports(self.comboBox_force_select_com, self.btn_force_select, force)
        force_profiles = self.parent.data_handler.config.c_data['force']
        poplulate_combo(self.comboBox_force_config, force_profiles)

        # Find MicroEpsilon Laser sensors
        laser_ports = self.port_searcher.get_laser()
        laser_sns = self.parent.data_handler.config.c_data['laser']['IP_SerialNumbers']
        poplulate_combo(self.comboBox_laser_config, laser_sns)
        populate_comports(self.comboBox_laser_select_com, self.btn_laser_select, laser_ports)

        # Find Webcam
        webcam_list = webcam.find_webcams()
        self.webcam_dict = {}
        for i, cam in enumerate(webcam_list):
            self.webcam_dict[i] = cam
        poplulate_combo(self.comboBox_webcam, self.webcam_dict)


    def select_smapoc(self):
        port = self.comboBox_smapoc_select_com.currentText().split('|')[0].strip()
        self.add_item_to_config('SMAPOC', 'port', port)
        self.status = Status(self.lbl_smapoc_status)
        self.status.append_text(str(self.new_config))
        self.status.green()
        self.btn_skip_next.setText('Next')
        self.btn_skip_next.setEnabled(True)




    def add_item_to_config(self, device_name, item_name, value):
        if 'devices' not in self.new_config:
            self.new_config['devices'] = {}
        if device_name not in self.new_config['devices']:
            self.new_config['devices'][device_name] = {}
        self.new_config['devices'][device_name][item_name] = value
        print(self.new_config)

    def show_progress(self):
        n = 25
        self.cnt_smapoc += 1
        self.status.append_text(f'Waiting for SMApoc to self calibrate {self.cnt_smapoc}/{n}sec....\n')

        if self.cnt_smapoc == n-2:
            self.mysmapoc.serial.reset_input_buffer()
            self.mysmapoc.write_data(b'uz')
            self.status.append_text('Writing UZ\n')

        if self.cnt_smapoc >= n:
            self.timer.disconnect()
            self.status.append_text('Reading\n')
            data = self.mysmapoc.serial.read_until(size=16)
            if len(data) == 16:
                data_parsed = list(struct.unpack('<8h', data))
            else:
                data_parsed = data
            self.status.append_text(f'Received:{data_parsed}\n')
            logging.debug(data_parsed)
            if len(data_parsed) == 8:
                self.status.green()
                self.btn_skip_next.setEnabled(True)
                self.btn_skip_next.setText('Next')
                self.new_config['SMAPOC'] = {'comport': self.mysmapoc.port,
                                             'baudrate': self.mysmapoc.baudrate}
            else:
                self.status.red()
                self.status.setText(f'Error: Received wrong number of bytes: {data_parsed}')





    def select_laser(self):
        port = self.comboBox_laser_select_com.currentText().split('|')[0].strip()
        sn = self.comboBox_laser_config.currentText().split('|')[1].strip()
        self.add_item_to_config('LASER','port', port)
        self.add_item_to_config('LASER','sn', sn)

        self.status = Status(self.lbl_laser_status)
        self.status.append_text(str(self.new_config))
        self.status.green()
        self.btn_skip_next.setText('Next')
        self.btn_skip_next.setEnabled(True)

    def select_force(self):
        port = self.comboBox_force_select_com.currentText().split('|')[0].strip()
        profile = self.comboBox_force_config.currentText().split('|')[0].strip()
        print(f'Profile: {profile}')
        force_profile = self.parent.data_handler.config.c_data['force'][profile]
        self.add_item_to_config('FORCE', 'port', port)
        self.add_item_to_config('FORCE', 'sn', profile)
        self.add_item_to_config('FORCE', 'params', force_profile)
        self.status = Status(self.lbl_force_status)
        self.status.append_text(str(self.new_config))
        self.status.green()
        self.btn_skip_next.setText('Next')
        self.btn_skip_next.setEnabled(True)

    def connect_webcam(self):
        number = self.comboBox_webcam.currentText().split('|')[1].strip()
        self.add_item_to_config('WEBCAM','number',number)
        self.status = Status(self.lbl_force_status_2)
        self.status.append_text(str(self.new_config))
        self.status.green()
        self.btn_skip_next.setEnabled(True)

    def disconnect(self):
        for key, device in self.communicator.devices.items():
            try:
                device.data_received.disconnect(self.callback)
            except Exception as e:
                print(f"Error disconnecting device {key}: {e}")

    def clicked_next(self):
        page = self.stackedWidget.currentIndex()
        n_pages = self.stackedWidget.count()
        print(f'{page}/{n_pages}')
        self.btn_skip_next.setText('Skip')
        if page < (n_pages-1):
            self.stackedWidget.setCurrentIndex(page+1)
            if self.stackedWidget.currentIndex() == n_pages-1:
                self.btn_skip_next.setText('Save Config')
        else:
            self.on_accept.emit()
            logging.debug('on accept signal emitted')
            self.mydialog = LineDialog()
            if self.mydialog.exec_() == qtw.QDialog.Accepted:
                config_name = self.mydialog.get_config_name()
                if config_name == "":
                    config_name = "Config1"
                self.new_config['name'] = config_name
            self.accept()

    def clicked_prev(self):
        page = self.stackedWidget.currentIndex()
        if page > 0:
            self.stackedWidget.setCurrentIndex(page-1)


def populate_comports(combo_widget, connect_btn, dict_com):
    combo_widget.clear()
    for key, value in dict_com.items():
        combo_widget.addItem(' | '.join([key, value[-1]]))
    if len(dict_com) > 0:
        connect_btn.setEnabled(True)
    else:
        connect_btn.setEnabled(False)

def poplulate_combo(combo_widget, dict_com):
    combo_widget.clear()
    for key, value in dict_com.items():
        combo_widget.addItem(' | '.join([str(key), str(value)]))


class Status(qtw.QLabel):
    def __init__(self, label):
        super().__init__()
        self.label = label
        self.text = ""

    def append_text(self, new_text):
        self.text = self.text + new_text
        self.label.setText(self.text)

    def red(self):
        self.label.setStyleSheet("background-color: salmon")

    def green(self):
        self.label.setStyleSheet("background-color: lightgreen")


class StatusTable:
    def __init__(self, parent, layout_widget):
        self.parent = parent
        self.dev_wizard = self.parent.wizard
        self.state = self.parent.dev_observer.state
        self.layout = layout_widget

    def update_status_table(self):
        n_row = 2
        for key, value in self.state.items():
            self.print_row(key, value, n_row)
            n_row += 1

    def print_row(self, mykey, myvalue, row_number):
        name = ""
        port = ""
        state = ""

        verbos_state = {1: 'ACTIVE', 0: 'INACTIVE'}
        if mykey == ids.START_SMAPOC:
            name = 'SMAPOC'
            port = self.dev_wizard.connector_smapoc.thread.port
            state = verbos_state[myvalue]
        if mykey == ids.START_LASER:
            name = 'Laser'
            port = self.dev_wizard.connector_laser.thread.port
            state = verbos_state[myvalue]
        if mykey == ids.START_FORCE:
            name = 'Force'
            port = self.dev_wizard.connector_force.thread.port
            state = verbos_state[myvalue]
        label_name = ColorLabel(name, 'black')
        label_comport = ColorLabel(port, 'black')
        label_status = ColorLabel(state, 'black')
        for i in [0, 1, 2]:
            self.remove_cell(row_number, i)

        self.layout.addWidget(label_name, row_number, 0)
        self.layout.addWidget(label_comport, row_number, 1)
        self.layout.addWidget(label_status, row_number, 2)

    def remove_cell(self, row, col):
        widget = self.layout.itemAtPosition(row, col)
        if widget:
            widget = widget.widget()  # Get actual widget
            self.layout.removeWidget(widget)  # Remove from layout
            widget.deleteLater()  # Delete widget


class ColorLabel(qtw.QLabel):
    def __init__(self, text, color="red", parent=None):
        super().__init__(text, parent)
        self.set_color(color)

    def set_color(self, color):
        """Set label font color."""
        palette = self.palette()
        palette.setColor(qtg.QPalette.WindowText, qtg.QColor(color))
        if 'ACTIVE' in self.text():
            palette.setColor(qtg.QPalette.WindowText, qtg.QColor('green'))
        if 'INACTIVE' in self.text():
            palette.setColor(qtg.QPalette.WindowText, qtg.QColor('red'))

        self.setPalette(palette)

