import os

import PyQt5.QtCore as qtc


import pandas as pd
import datetime as dt
from pathlib import Path
import json
from smapoc.model import session
from smapoc import ids
import logging
from datetime import datetime
import cv2

logging.getLogger(__name__)



class DataHandler(qtc.QObject):
    data_available = qtc.pyqtSignal()
    plot_status = qtc.pyqtSignal(bool)
    plot_interval = qtc.pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.data = pd.DataFrame()
        self.temp_row = {}
        self.timer = qtc.QTimer()
        self.timer.timeout.connect(self.transfer_collected)
        self.interval = 20
        self.timestamp = dt.datetime.utcnow()
        self.config = Config()
        self.session = session.Session()
        self.data_array_size = 20000
        # self.offsets = {}

    def get_col_names(self):
        return list(self.data.columns)

    def data_clear(self):
        self.data = pd.DataFrame()

    def set_interval(self, interval):
        self.interval = interval
        self.timer.setInterval(interval)

    def collect(self, key, value):
        self.temp_row[key] = value


    def start_collecting(self):
        self.timer.start(self.interval)

    def stop_collecting(self):
        self.timer.stop()


    def transfer_collected(self):
        # Get current UTC time
        utc = dt.datetime.utcnow()

        # Calculate the difference in milliseconds
        time = (utc - self.timestamp).total_seconds()
        # get last row of existing df
        if self.data.empty:
            row_df = pd.DataFrame(self.temp_row, index=[0])
        else:
            row_df = self.data.iloc[-1::, :].copy()  # copy last row

        for key, value in self.temp_row.items():
            row_df[key] = value
        row_df['time'] = time
        row_df['datetime'] = dt.datetime.now()
        self.data = pd.concat([self.data, row_df])
        if len(self.data) > self.data_array_size:
            self.data = self.data.iloc[-3000:]  # Keep only the last 3000 rows
        self.data_available.emit()


class Config:
    def __init__(self):
        self.c_data = {}
        self.load()

    def load(self):
        with open('smapoc/global_config.json', 'r') as file:
            self.c_data = json.load(file)


    def write_value(self,key,value):
        self.c_data[key] = value
        try:
            with open('smapoc/global_config.json', 'w') as file:
                json.dump(self.c_data, file)
        except FileNotFoundError as e:
            logging.warning('error writing config')





class Recorder:

    output_folder = Path("TEST-DATA")

    def __init__(self, communicator):
        self.communicator = communicator
        self.rec_flag = False
        self.rec_status = False
        self.video_writer = None
        self.height = None
        self.width = None
        self.size = None
        try:
            self.communicator.devices['webcam'].frame_received.connect(self.get_frame)
        except KeyError:
            logging.warning('No Webcam available')
            self.rec_status = False

    def get_frame(self, myid, frame):
        # one frame to get the dimensions
        if myid == ids.FROM_WEBCAM:
            self.height, self.width, _ = frame.shape
            self.size = (self.width, self.height)
            print(self.size)
            self.communicator.devices['webcam'].frame_received.disconnect(self.get_frame)
            self.rec_status = True

    def stop_rec(self):
        self.rec_flag = False
        self.close_file()

    def start_rec(self):
        self.rec_flag = True
        # Save every frame or conditionally
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")[:-3]  # e.g., 20250605_142330_123
        tempfilename = Path(self.output_folder) / "temp.mp4"
        # Delete if it exists
        if tempfilename.exists():
            tempfilename.unlink()
        # Create the video writer
        print(os.listdir())
        print(tempfilename)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(str(tempfilename), fourcc, 30, self.size)
        if not self.video_writer.isOpened():
            print("VideoWriter konnte nicht geöffnet werden!")
        else:
            print("VideoWriter geöffnet mit Größe:", self.size)
        self.communicator.devices['webcam'].frame_received.connect(self.write_frame)

    def write_frame(self, myid, frame):
        if myid == ids.FROM_WEBCAM:
            if self.rec_flag & self.rec_status:
                self.video_writer.write(frame)

    def close_file(self):
        if self.video_writer:
            self.video_writer.release()





