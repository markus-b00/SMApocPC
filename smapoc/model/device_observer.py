
import PyQt5.QtCore as qtc
import logging
import star.ids as ids
logging.getLogger(__name__)



class DeviceObserver(qtc.QObject):
    # Checking which peripherals are registered and responsive
    state_changed = qtc.pyqtSignal(dict)
    def __init__(self, parent):
        super().__init__()
        self.state = {}
        self.timer = qtc.QTimer()
        #self.timer.timeout.connect(self.update_state)

    def get_state(self, dev_id):
        # returns a tuple (registrated,active)
        if dev_id in self.state.keys():
            return (1, self.get_state(dev_id))


    def register_device(self,dev_id, state=1):
        self.state[dev_id] = state
        logging.debug(self.state)
        self.state_changed.emit(self.state)

    def unregister_device(self, dev_id):
        if dev_id in self.state.keys():
            self.state.pop(dev_id, None)
        self.state_changed.emit(self.state)

    def set_inactive(self, dev_id):
        self.state[dev_id] = 0
        logging.debug(self.state)
        self.state_changed.emit(self.state)


    def set_active(self, dev_id):
        if dev_id in self.state.keys():
            self.state[dev_id] = 1







