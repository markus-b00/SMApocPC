import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui  as qtg
from ..gui.UI_single_channel import Ui_SingleChannel
import numpy as np
import logging
import time
logging.getLogger(__name__)


class SMAChannels(qtc.QObject):
    update_power = qtc.pyqtSignal()

    channel_names = ['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6']


    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.channels = {}

        self.dock = qtw.QDockWidget('SMAPOC channels', self.parent)
        self.dock.setAllowedAreas(qtc.Qt.AllDockWidgetAreas)  # Allow moving anywhere
        # Enable full resizing
        self.dock.setFeatures(qtw.QDockWidget.DockWidgetMovable | qtw.QDockWidget.DockWidgetClosable)

        # Set expanding size policy
        self.dock.setSizePolicy(self.dock.sizePolicy().Expanding, self.dock.sizePolicy().Expanding)

        # Add to main window
        self.parent.addDockWidget(qtc.Qt.LeftDockWidgetArea, self.dock)
        self.dock_content = qtw.QWidget(self.dock)
        self.layout = qtw.QHBoxLayout(self.dock_content)
        self.dock.setWidget(self.dock_content)
        for ch in self.channel_names:
            self.add_channel(ch)


    def update(self):
        self.update_power.emit()

    def add_channel(self, name):
        self.channels[name] = Channel(self, name)
        self.layout.addWidget(self.channels[name])

    def clear(self):
        self.channels = {}



class Channel(qtw.QWidget, Ui_SingleChannel):
    def __init__(self, chs_obj, name):
        super().__init__()
        self.chs_obj = chs_obj
        self.name = name
        self.setupUi(self)
        self.lbl_title.setText(name)

        self.state = True
        self.output = 0

        self.timer = qtc.QTimer()
        self.timer.timeout.connect(self.update_sine)
        self.timer.start(10)
        self.amp = self.doubleSpinBox_amp.value()
        self.freq = self.doubleSpinBox_freq.value()
        self.off = self.doubleSpinBox_offset.value()
        self.phase = self.doubleSpinBox_phase.value()

        self.doubleSpinBox_phase.lineEdit().returnPressed.connect(self.update_value)
        self.doubleSpinBox_freq.lineEdit().returnPressed.connect(self.update_value)
        self.doubleSpinBox_offset.lineEdit().returnPressed.connect(self.update_value)
        self.doubleSpinBox_amp.lineEdit().returnPressed.connect(self.update_value)

        self.btn_activate.clicked.connect(self.toggle_state)


    def update_value(self):
        self.amp = self.doubleSpinBox_amp.value()
        self.freq = self.doubleSpinBox_freq.value()
        self.off = self.doubleSpinBox_offset.value()
        self.phase = self.doubleSpinBox_phase.value()

    def update_sine(self):
        #logging.debug(f'{self.name}:{self.chs_obj.globaltime}')
        out = (self.amp * np.sin(2 * np.pi * self.freq * time.time() + self.phase) + self.off) * self.output
        #logging.debug(f'{self.name}:{out}')
        self.lbl_output_value.setText(f'{out:.1f}')
        return out


    def toggle_state(self):
        if self.state:
            self.state = False
            self.output = 0
            self.btn_activate.setText('deactivated')
            self.btn_activate.setStyleSheet("background-color: 'salmon'")
            #self.chs_obj.timer.stop()
        else:
            self.state = True
            self.output = 1
            self.btn_activate.setText('active')
            self.btn_activate.setStyleSheet("background-color: 'lightgreen'")
            #self.chs_obj.timer.start()



