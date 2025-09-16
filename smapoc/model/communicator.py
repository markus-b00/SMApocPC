import PyQt5.QtCore as qtc

import logging
import smapoc.model.com_peripherals as peripherals
import smapoc.ids as ids

logging.getLogger(__name__)

class Communicator(qtc.QObject):
    smapoc_mode_changed = qtc.pyqtSignal()

    def __init__(self, data_handler):
        super().__init__()
        self.data_handler = data_handler
        self.state = {}
        self.devices = {}

        self.request_timer = qtc.QTimer()
        self.request_timer.timeout.connect(self.choose_request)
        self.zero_timer = qtc.QTimer()

        self.power = None
        self.interval = 15
        self.offsets = {ids.FROM_FORCE: 0, ids.FROM_LASER: self.data_handler.config.c_data['laser_offset']}
        self.mode = 'sine'
        self.smapoc_mode = ids.CURRENT

    def choose_request(self):
        if self.mode == 'sine':
            if self.power:
                self.devices['smapoc'].write_data(ids.FROM_SMAPOC, self.power.get_power_sine_msg())
            for key, value in self.devices.items():
                #logging.debug(f'request {key}')
                if key not in ['smapoc', 'webcam']:
                    value.read()
        elif self.mode == 'direct':
            if self.power:
                self.devices['smapoc'].write_data(ids.FROM_SMAPOC, self.power.get_power_direct_msg())
            for key, value in self.devices.items():
                # logging.debug(f'request {key}')
                if key not in ['smapoc', 'webcam']:
                    value.read()
    def set_smapoc_mode(self,mode):
        self.smapoc_mode = mode
        self.smapoc_mode_changed.emit()

    def get_smapoc_mode(self):
        return self.smapoc_mode

    def zero_output(self):
        if self.power:
            self.power.update_power_vec_direct([0, 0, 0, 0, 0, 0])
            self.devices['smapoc'].write_data(ids.FROM_SMAPOC, self.power.get_power_direct_msg())


    def set_interval(self, interval):
        self.request_timer.setInterval(interval)
        self.interval = interval

    def start_requesting(self, mode='sine'):
        if mode == 'sine':
            self.mode = mode
            self.request_timer.start(self.interval)
            self.data_handler.start_collecting()
        if mode == 'direct':
            self.mode = mode
            self.request_timer.start(self.interval)
            self.data_handler.start_collecting()



    def stop_requesting(self):
        self.request_timer.stop()
        self.data_handler.stop_collecting()

    def add_smapoc(self, port, baudrate=250000):
        self.devices['smapoc'] = peripherals.SMAPOCWorker(port, baudrate)
        self.devices['smapoc'].start()
        self.devices['smapoc'].data_received.connect(self.callback)

    def add_force(self, port, force_profile):
        self.devices['force'] = peripherals.ForceWorker(port,
                                                        self.data_handler.config,
                                                        force_profile)
        self.devices['force'].start()
        self.devices['force'].data_received.connect(self.callback)

    def add_laser(self, port, sn):
        self.devices['laser'] = peripherals.LaserWorker(port,
                                                        self.data_handler.config,
                                                        sn)
        self.devices['laser'].start()
        self.devices['laser'].data_received.connect(self.callback)

    def add_webcam(self, name):
        self.devices['webcam'] = peripherals.Video(name)
        self.devices['webcam'].start()


    def remove_device(self, key):
        self.devices[key].stop()
        self.devices.pop(key)

    def add_power_obj(self, power_obj):
        self.power = power_obj


    def zero(self, what='force'):
        if what == 'force':
            if ids.FROM_FORCE in self.offsets.keys():
                self.offsets[ids.FROM_FORCE] = 0
            self.zero_timer.singleShot(300, self.zero_force)
        if what == 'laser':
            if ids.FROM_LASER in self.offsets.keys():
                self.offsets[ids.FROM_LASER] = 0
            self.zero_timer.singleShot(300, self.zero_laser)


    def zero_force(self):
        self.offsets[ids.FROM_FORCE] = self.data_handler.data['force'].iloc[-1]


    def zero_laser(self):
        self.offsets[ids.FROM_LASER] = self.data_handler.data['laser'].iloc[-1]
        self.data_handler.config.write_value('laser_offset', self.offsets[ids.FROM_LASER])




    def do_zeroing(self):
        # legacy code not used anymore
        if len(self.data_handler.data) >= 1:
            last_laser_val = self.data_handler.data['laser'].iloc[-1]
            last_force_val = self.data_handler.data['force'].iloc[-1]
            self.offsets[ids.FROM_LASER] = last_laser_val
            self.offsets[ids.FROM_FORCE] = last_force_val
            self.data_handler.config.write_value('laser_offset', self.offsets[ids.FROM_LASER])
        print(self.offsets)






    def callback(self, myid, data_list):
        logging.debug('Enter Callback Communicator')
        if myid in [ids.FROM_LASER, ids.SELFTEST_LASER]:
            logging.debug('callback laser')
            # row_df = self.data.iloc[-1::, :].copy()  # copy last row
            # row_df['time'] = [dt.datetime.now()]
            self.data_handler.collect('laser', data_list[-1] - self.offsets[ids.FROM_LASER])
            #logging.info(f'new_data{data_list[-1]},offset:{self.offsets[ids.FROM_LASER]}')
            # row_df['id'] = [my_id]
            # self.data = pd.concat([self.data, row_df])

        if myid in [ids.SELFTEST_FORCE, ids.FROM_FORCE]:
            logging.debug('callback force')
            # row_df = self.data.iloc[-1::, :].copy()  # copy last row
            # row_df['time'] = [dt.datetime.now()]
            if 'force' in self.data_handler.data.keys():
                old_val = self.data_handler.data['force'].iloc[-1]
                new_val = data_list[0] - self.offsets[ids.FROM_FORCE]
                if abs(old_val-new_val) < 0.4:
                    self.data_handler.collect('force', new_val)
                else:
                    self.data_handler.collect('force', old_val)
            else:
                self.data_handler.collect('force', data_list[0] - self.offsets[ids.FROM_FORCE])

            #logging.info(f'new_data{data_list[-1]},offset:{self.offsets[ids.FROM_FORCE]}')
            # row_df['id'] = [my_id]
            # self.data = pd.concat([self.data, row_df])


        if myid in [ids.SELFTEST_SMAPOC, ids.FROM_SMAPOC]:
            logging.debug('start transfer smapoc data')
            # self.row_df = self.data.iloc[-1::, :].copy()  # copy last row
            # row_df['time'] = [dt.datetime.now()]
            res_dict = {}
            # self.temp_data_lists['id'] = [my_id]

            self.data_handler.collect('r1', data_list[2])
            self.data_handler.collect('r2', data_list[3])
            self.data_handler.collect('r3', data_list[4])
            self.data_handler.collect('r4', data_list[5])
            self.data_handler.collect('r5', data_list[6])
            self.data_handler.collect('r6', data_list[7])

            try:
                power = self.power.power_vec
                if self.smapoc_mode == ids.POWER:
                    self.data_handler.collect('pow1', power[0])
                    self.data_handler.collect('pow2', power[1])
                    self.data_handler.collect('pow3', power[2])
                    self.data_handler.collect('pow4', power[3])
                    self.data_handler.collect('pow5', power[4])
                    self.data_handler.collect('pow6', power[5])
                else:
                    self.data_handler.collect('curr1', power[0])
                    self.data_handler.collect('curr2', power[1])
                    self.data_handler.collect('curr3', power[2])
                    self.data_handler.collect('curr4', power[3])
                    self.data_handler.collect('curr5', power[4])
                    self.data_handler.collect('curr6', power[5])
            except AttributeError as e:
                logging.warning(e)
            logging.debug('finish transfer smapoc data')








