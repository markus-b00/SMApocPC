import logging
import struct
from star.gui.UI_device_wizard import Ui_Dialog
from star.model.comport_handling import ComPortSearcher
from star.model.com_peripherals import SMAPOCWorker
from star.model.com_peripherals import LaserWorker, SMAPOCWorker, ForceWorker
from star import ids
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
import PyQt5.QtCore as qtc




class DeviceWizard(qtw.QDialog, Ui_Dialog):
    on_accept = qtc.pyqtSignal()

    force_calib_data = {'17306857_5N': {'fn': 5, 'sn': 0.4980, 'u_e': 2},
                        '17404730_5N': {'fn': 5, 'sn': 0.5032, 'u_e': 2},
                        '19104236_0_5N': {'fn': 0.491, 'sn': 0.628, 'u_e': 2}}

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.dev_observer = self.parent.dev_observer

        self.setupUi(self)

        self.btn_skip.clicked.connect(self.clicked_next)
        self.btn_cancel.clicked.connect(self.close)
        self.btn_back.clicked.connect(self.clicked_previous)
        self.stackedWidget.setCurrentIndex(0)
        self.port_searcher = ComPortSearcher()
        self.connector_smapoc = Connector(self,
                                          self.comboBox_smapoc_select_com,
                                          self.btn_smapoc_connect,
                                          self.lbl_smapoc_status,
                                          ids.SMAPOC_WORKER)
        self.connector_laser = Connector(self,
                                         self.comboBox_laser_select_com,
                                         self.btn_laser_connect,
                                         self.lbl_laser_status,
                                         ids.LASER_WORKER)
        self.connector_force = Connector(self,
                                         self.comboBox_force_select_com,
                                         self.btn_force_connect,
                                         self.lbl_force_status,
                                         ids.FORCE_WORKER)

        self.check_timer = qtc.QTimer()
        self.check_timer.setInterval(2000)
        self.check_timer.timeout.connect(self.do_check)

    @qtc.pyqtSlot(int)
    def received_inactive(self, myid):
        self.dev_observer.set_inactive(myid)

    def start_checker(self):
        self.check_timer.start()

    def stop_checker(self):
        self.check_timer.stop()

    def do_check(self):
        for key in self.dev_observer.state:
            if key == ids.START_SMAPOC:
                self.connector_smapoc.thread.handshake()
            if key == ids.START_LASER:
                self.connector_laser.thread.handshake()
            if key == ids.START_FORCE:
                self.connector_force.thread.handshake()







    def clicked_next(self):
        page = self.stackedWidget.currentIndex()
        n_pages = self.stackedWidget.count()
        print(f'{page}/{n_pages}')
        self.btn_skip.setText('Skip')
        if page < (n_pages-1):
            self.stackedWidget.setCurrentIndex(page+1)
            if self.stackedWidget.currentIndex() == n_pages-1:
                self.btn_skip.setText('Finish')
        else:
            self.on_accept.emit()
            logging.debug('on accept signal emitted')
            self.close()

    def clicked_previous(self):
        page = self.stackedWidget.currentIndex()

        if page > 0:
            self.stackedWidget.setCurrentIndex(page-1)


    def onloading(self):
        # Find connected SMAPOC
        smapoc = self.port_searcher.get_smapoc()
        populate_comports(self.comboBox_smapoc_select_com, self.btn_smapoc_connect, smapoc)

        # Find connected Force sensors
        force = self.port_searcher.get_force()
        populate_comports(self.comboBox_force_select_com, self.btn_force_connect, force)
        poplulate_combo(self.comboBox_force_config,  self.force_calib_data)

        # Find connected Force sensors
        laser = self.port_searcher.get_laser()
        populate_comports(self.comboBox_laser_select_com, self.btn_laser_connect, laser)


    def show(self):
        self.onloading()
        self.exec_()


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
            combo_widget.addItem(' | '.join([key, str(value)]))


class Connector(qtc.QObject):
    def __init__(self, parent, combo, connect_btn, status_label, current_id):
        super().__init__()
        self.parent = parent
        self.dev_observer = self.parent.dev_observer
        self.thread = None
        self.combo = combo
        self.btn_connect = connect_btn
        self.status_label = status_label
        self.current_id = current_id
        self.btn_connect.clicked.connect(self.connect_threads)
        self.timer = qtc.QTimer()
        self.timeout_timer = qtc.QTimer()
        self.text = ""
        self.btn_next = self.parent.btn_skip

        self.timer_smapoc = qtc.QTimer()
        self.timer_laser = qtc.QTimer()



    def connect_threads(self):
        port = self.combo.currentText().split(' | ')[0]
        if self.current_id == ids.SMAPOC_WORKER:
            self.thread = SMAPOCWorker(port, parent=self.parent)
        if self.current_id == ids.LASER_WORKER:
            self.thread = LaserWorker(port, parent=self.parent)
        if self.current_id == ids.FORCE_WORKER:
            self.thread = ForceWorker(port, parent=self.parent)
        self.thread.start()
        self.thread.data_received.connect(self.callback)
        self.append_text("Try to connect....\n")
        self.thread.handshake()

    def callback(self, my_id, value):
        if my_id == ids.START_SMAPOC:
            n = len(value)
            self.append_text(f'Received {n}/8 values\n')
            self.append_text(f'Values: {value}\n')
            self.status_label.setText(str(value))
            if n == 8:
                self.append_text('Connection successfull\n')
                self.status_label.setStyleSheet("background-color: lightgreen")
                self.btn_next.setText('Next')
                self.dev_observer.register_device(ids.START_SMAPOC)
            else:
                self.append_text('------------------Error--------------\n')
                self.status_label.setStyleSheet("background-color: salmon")

        if my_id == ids.START_LASER:
            n = len(value)
            self.append_text(f'Received {n}/2 values\n')
            self.append_text(f'{value}\n')
            if n == 2:
                self.append_text('Connection successfull\n')
                self.status_label.setStyleSheet("background-color: lightgreen")
                self.dev_observer.register_device(ids.START_LASER)
            else:
                self.append_text('------------------Error--------------\n')
                self.status_label.setStyleSheet("background-color: salmon")


        if my_id == ids.START_FORCE:
            n = len(value)
            self.btn_next.setText('Finish')
            self.append_text(f'Received {n}/1 values\n')
            self.append_text(f'{value}\n')
            current_text = self.parent.comboBox_force_config.currentText()
            values = self.parent.force_calib_data[current_text.split(' | ')[0]]
            self.thread.calib(values['fn'], values['sn'], values['u_e'])
            if n > 0:
                self.append_text('Connection successfull\n')
                self.status_label.setStyleSheet("background-color: lightgreen")
                self.dev_observer.register_device(ids.START_FORCE)
            else:
                self.append_text('-----------COM Error--------------\n')
                self.status_label.setStyleSheet("background-color: salmon")

    def append_text(self, new_text):
        self.text = self.text + new_text
        self.status_label.setText(self.text)

    def on_timeout(self):
        self.append_text('--------------No Response Error--------------\n')
        self.status_label.setStyleSheet("background-color: salmon")
        self.dev_observer.set_inactive(self.current_id)








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
