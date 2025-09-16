import logging

import pandas as pd
import numpy as np
import smapoc.ids as ids
import datetime as dt
import PyQt5.QtCore as qtc


class Datacollector(qtc.QObject):
    update = qtc.pyqtSignal()

    def __init__(self, parent, smapoc_worker, laser_worker, force_worker, sma_channels):
        super().__init__()
        self.parent = parent
        self.smapoc_worker = smapoc_worker

        self.laser_worker = laser_worker
        #self.laser_worker.data_received.connect(self.callback)

        self.force_worker = force_worker
        #self.force_worker.data_received.connect(self.callback)

        self.smapoc_worker = smapoc_worker
        self.smapoc_worker.data_received.connect(self.callback)

        self.sma_channels = sma_channels

        self.data = pd.DataFrame({'force': [0],
                                  'laser': [0],
                                  'time': [dt.datetime.now()],
                                  'id': [0]})

        self.mytimer = qtc.QTimer()
        self.mytimer.setInterval(100)
        self.mytimer.timeout.connect(self.request_data)
        self.temp_values = {}
        self.state = 0


        #self.row_df_laser = pd.DataFrame({'laser': [3.5], 'time': [dt.datetime.now()], 'id': [0]})

    def set_cycle_time(self, cycle_time):
        self.mytimer.setInterval(cycle_time)



    def set_timer_interval(self, interval):
        self.mytimer.setInterval(interval)



    def request_data(self):
        logging.debug('single read request')
        self.sma_channels.update()
        self.force_worker.read(ids.FROM_FORCE)
        if len(self.data) > 5000:
            last_row = self.data.iloc[-1::, :].copy()
            self.data = last_row
        self.laser_worker.read_single(ids.FROM_LASER)



    def start_collecting(self):
        self.mytimer.start()


    @qtc.pyqtSlot(int, list)
    def callback(self, my_id, value):

        if my_id == ids.FROM_LASER:
            logging.debug('callback laser')
            #row_df = self.data.iloc[-1::, :].copy()  # copy last row
            #row_df['time'] = [dt.datetime.now()]
            self.temp_values['laser'] = [value[-1]]
            #row_df['id'] = [my_id]
            #self.data = pd.concat([self.data, row_df])
            self.state = self.state | 1 << 0

        if my_id == ids.FROM_FORCE:
            logging.debug('callback force')
            #row_df = self.data.iloc[-1::, :].copy()  # copy last row
            #row_df['time'] = [dt.datetime.now()]
            self.temp_values['force'] = [value[0]]
            #row_df['id'] = [my_id]
            #self.data = pd.concat([self.data, row_df])
            self.state = self.state | 1 << 1

        if my_id == ids.FROM_SMAPOC:
            logging.debug('callback smapoc')
            #self.row_df = self.data.iloc[-1::, :].copy()  # copy last row
            #row_df['time'] = [dt.datetime.now()]
            res_dict = {}
            #self.temp_values['id'] = [my_id]

            self.temp_values['r1'] = value[2]
            self.temp_values['r2'] = value[3]
            self.temp_values['r3'] = value[4]
            self.temp_values['r4'] = value[5]
            self.temp_values['r5'] = value[6]
            self.temp_values['r6'] = value[7]

            sma_power = self.parent.power

            self.temp_values['pow1'] = sma_power.power_vec[0]
            self.temp_values['pow2'] = sma_power.power_vec[1]
            self.temp_values['pow3'] = sma_power.power_vec[2]
            self.temp_values['pow4'] = sma_power.power_vec[3]
            self.temp_values['pow5'] = sma_power.power_vec[4]
            self.temp_values['pow6'] = sma_power.power_vec[5]
            #self.data = pd.concat([self.data, row_df])

            self.state = self.state | 1 << 2

        if self.state == 7:
            self.state = 0
            row_df = pd.DataFrame(self.temp_values, index=[0])
            self.data = pd.concat([self.data, row_df])




    def clear(self):
        self.data = pd.DataFrame()