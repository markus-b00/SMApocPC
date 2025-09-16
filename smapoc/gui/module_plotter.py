import sys
import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg
import pyqtgraph as pg
import os
from datetime import datetime
from pathlib import Path
from pyqtgraph.exporters import ImageExporter

from smapoc.gui.UI_actuator_test import Ui_DialogSequence
from smapoc.gui.webcam_window import FloatingCameraWindow

from smapoc.gui.dialogs import LineDialog
from smapoc import ids
import json

import logging
logging.getLogger(__name__)

class ScriptExecutor(qtw.QDialog, Ui_DialogSequence):
    labeling = {ids.CURRENT: {'title': 'Current Driving',
                              'y_label': 'Current [mA]'},
                ids.POWER: {'title': 'Power Driving',
                            'y_label': 'Power [mW]'}}


    def __init__(self, parent, communicator, data_handler, recorder=None):
        super().__init__()
        pg.setConfigOptions(antialias=True)
        self.parent = parent

        self.setWindowFlags(qtc.Qt.Window)
        self.recorder = recorder
        self.communicator = communicator
        self.data_handler = data_handler
        print(os.curdir)
        self.scripts = self.load_text_files('./scripts')
        self.setupUi(self)
        self.setWindowTitle("Script Execution")

        self.webcam_win = None

        self.comboBox_select_sequence.currentTextChanged.connect(self.load_script)
        # State
        self.commands = []
        self.current_index = 0
        self.running = False
        self.rep_total = 0
        self.rep_count = 0
        self.start_index = 0
        self.test_name = None
        self.load_script(self.comboBox_select_sequence.currentText())

        self.camera_window = None
        logging.debug(self.communicator.devices.keys())

        self.btn_save.clicked.connect(self.save_csv)
        self.btn_zero_force.clicked.connect(self.zero_force)
        self.btn_zero_laser.clicked.connect(self.zero_laser)
        self.btn_start_stop.clicked.connect(self.toggle_execution)
        self.btn_reset_offsets.clicked.connect(self.reset_offsets)

        self.plot_timer = qtc.QTimer()
        self.plot_timer.timeout.connect(self.update_plots)
        self.stop_timer = qtc.QTimer()

        # initialize plot
        self.p1_res = self.plt_sequence.addPlot(title='Resistance')
        self.p1_res.setLabel('left', 'Resistance [mOhm]')  # 'left' refers to Y axis
        self.p1_res.setLabel('bottom', 'Time [samples]')   # 'bottom' refers to X axis

        self.p2_pow = self.plt_sequence.addPlot(title=self.labeling[self.communicator.get_smapoc_mode()]['title'])
        self.p2_pow.setLabel('left', self.labeling[self.communicator.get_smapoc_mode()]['y_label'])
        self.p2_pow.setLabel('bottom', 'Time [samples]')  # 'bottom' refers to X axis
        self.plt_sequence.nextRow()

        self.p3_force = self.plt_sequence.addPlot(title='Force')
        self.p3_force.setLabel('left', 'Force')  # 'left' refers to Y axis
        self.p3_force.setLabel('bottom', 'Time [samples]')  # 'bottom' refers to X axis

        self.p4_dis = self.plt_sequence.addPlot(title='Displacement')
        self.p4_dis.setLabel('left', 'Displacement [mm]')  # 'left' refers to Y axis
        self.p4_dis.setLabel('bottom', 'Time [samples]')  # 'bottom' refers to X axis

        self.plots = [self.p1_res, self.p2_pow, self.p3_force, self.p4_dis]
        self.plot_handler = PlotHandler(self.plots, self.communicator)
        for plot in self.plots:
            plot.showGrid(x=True, y=True)
            plot.addLegend()



    def show(self,test_name=None):
        self.setWindowTitle(test_name)
        self.test_name = test_name
        self.comboBox_select_sequence.addItem(self.test_name)
        self.comboBox_select_sequence.setDisabled(True)
        self.plot_timer.start(50)
        self.communicator.start_requesting(mode='direct')
        self.exec_()




    def on_camera_closed(self):
        self.camera_window = None

    def start_plots(self):
        self.plot_timer.start(50)
        self.communicator.start_requesting(mode='direct')
        self.data_handler.data_clear()

    def zero_laser(self):
        reply = qtw.QMessageBox.question(
            self,
            "Zero",
            "Do you really want to reset the laser value? This action will overwrite the preset",
            qtw.QMessageBox.Yes | qtw.QMessageBox.Cancel,
            qtw.QMessageBox.Cancel)
        if reply == qtw.QMessageBox.Yes:
            self.communicator.zero(what='laser')
        else:
            # Just return to main
            pass


    def zero_force(self):
        self.communicator.zero(what='force')

    def update_plots(self):
        if len(self.communicator.devices.keys()) >= 4:
            self.plot_handler.update_res()
            self.plot_handler.update_laser()
            self.plot_handler.update_pow()
            self.plot_handler.update_force()

    def stop_plots(self):
        self.plot_timer.stop()
        self.communicator.stop_requesting()

    def load_text_files(self, folder_path):
        text_data = {}
        for filename in os.listdir(folder_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    key = os.path.splitext(filename)[0]
                    text_data[key] = file.read()
        return text_data


    def load_script(self, name):
        self.plainTextEdit_Script.setPlainText(self.scripts.get(name, ""))

    def parse_commands(self):
        self.commands = []
        lines = self.plainTextEdit_Script.toPlainText().splitlines()
        for idx, raw in enumerate(lines):
            line = raw.strip()
            if not line:
                continue
            entry = {'raw': raw, 'line_no': idx}
            if line.upper() == 'START':
                entry['cmd'] = 'START'
                self.start_index = len(self.commands)
            elif line.upper().startswith('POW'):
                entry['cmd'] = 'POW'
                vals = line[line.find('[')+1:line.find(']')]
                entry['vals'] = [int(x) for x in vals.split(',')]
            elif line.upper().startswith('SLEEP'):
                entry['cmd'] = 'SLEEP'
                entry['ms'] = int(line.split()[1])
            elif line.upper().startswith('REP'):
                entry['cmd'] = 'REP'
                entry['count'] = int(line.split()[1])
                self.rep_total = entry['count']
            else:
                entry['cmd'] = 'UNKNOWN'
            self.commands.append(entry)

    def highlight_line(self, cmd_index):
        # Prepare highlight selections
        selections = []

        # Highlight previous line in light grey
        if cmd_index > 0:
            prev_line_no = self.commands[cmd_index - 1]['line_no']
            block_prev = self.plainTextEdit_Script.document().findBlockByNumber(prev_line_no)
            cursor_prev = qtg.QTextCursor(block_prev)
            cursor_prev.select(qtg.QTextCursor.LineUnderCursor)
            fmt_prev = qtg.QTextCharFormat()
            fmt_prev.setBackground(qtc.Qt.lightGray)
            sel_prev = qtw.QTextEdit.ExtraSelection()
            sel_prev.cursor = cursor_prev
            sel_prev.format = fmt_prev
            selections.append(sel_prev)

        # Highlight current line in yellow (ALWAYS do this)
        line_no = self.commands[cmd_index]['line_no']
        block = self.plainTextEdit_Script.document().findBlockByNumber(line_no)
        cursor = qtg.QTextCursor(block)
        cursor.select(qtg.QTextCursor.LineUnderCursor)
        fmt = qtg.QTextCharFormat()
        fmt.setBackground(qtc.Qt.yellow)
        sel = qtw.QTextEdit.ExtraSelection()
        sel.cursor = cursor
        sel.format = fmt
        selections.append(sel)

        # Set the cursor to the current line
        self.plainTextEdit_Script.setTextCursor(cursor)
        # Apply highlights
        self.plainTextEdit_Script.setExtraSelections(selections)



        #self.plainTextEdit_Script.ensureCursorVisible()

    def execute_pow(self, vals):
        self.communicator.power.update_power_vec_direct(vals)

    def exec_command(self):
        if not self.running or self.current_index >= len(self.commands):
            return self.finish_execution()

        cmd = self.commands[self.current_index]
        self.highlight_line(self.current_index)

        if cmd['cmd'] == 'START':
            qtc.QTimer.singleShot(0, self.advance_and_exec)
        elif cmd['cmd'] == 'POW':
            self.execute_pow(cmd['vals'])
            qtc.QTimer.singleShot(0, self.advance_and_exec)
        elif cmd['cmd'] == 'SLEEP':
            qtc.QTimer.singleShot(cmd['ms'], self.advance_and_exec)
        elif cmd['cmd'] == 'REP':
            if self.rep_count < self.rep_total - 1:
                self.rep_count += 1
                self.current_index = self.start_index + 1
                qtc.QTimer.singleShot(0, self.exec_command)
            else:
                qtc.QTimer.singleShot(0, self.finish_execution)
        else:
            qtc.QTimer.singleShot(0, self.advance_and_exec)

    def advance_and_exec(self):
        self.current_index += 1
        self.exec_command()

    def toggle_execution(self):
        if self.running:
            logging.debug('is running')
            self.running = False
            self.plainTextEdit_Script.setExtraSelections([])
            self.btn_start_stop.setText('START')
            self.stop_plots()
            if self.recorder:
                self.recorder.stop_rec()
                self.recorder.close_file()
        else:
            #self.clear_plots()
            logging.debug('not running')
            self.parse_commands()
            self.running = True
            self.current_index = 0
            self.rep_count = 0
            self.exec_command()
            self.btn_start_stop.setText('STOP')
            self.start_plots()
            if self.recorder:
                self.recorder.start_rec()


    def finish_execution(self):
        logging.debug('finish execution')
        #self.running = False
        self.btn_start_stop.setText('START')
        self.plainTextEdit_Script.setExtraSelections([])
        self.stop_plots()
        self.running = False
        if self.recorder:
            self.recorder.stop_rec()
            self.recorder.close_file()

    def save_csv(self):
        sample_dialog = LineDialog(title="Sample name", text="Enter sample name")
        sample_name = sample_dialog.get_config_name()



        base_dir = os.path.abspath(os.getcwd())
        test_folder = self.test_name
        target_dir = os.path.join(base_dir, "TEST-DATA", test_folder)

        # Step 2: Ensure directory exists
        os.makedirs(target_dir, exist_ok=True)

        # Step 5: Write sample CSV data
        # Create a filename with datetime prefix
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if 'laser' in self.communicator.devices.keys():
            up_stroke = self.data_handler.data['laser'].min()
            down_stroke = self.data_handler.data['laser'].max()
            filename = f"{timestamp}_{sample_name}_upstroke{up_stroke:.3f}_downstroke{down_stroke:.3f}.csv"
        else:
            filename = f"{timestamp}_{sample_name}.csv"

        filename_config = filename[0:-4]+".json"
        # Step 4: Open save file dialog in the target directory
        default_filepath = os.path.join(target_dir, filename)
        file_path, _ = qtw.QFileDialog.getSaveFileName(
            self,
            "Save CSV File",
            default_filepath,
            "CSV Files (*.csv)"
        )

        if not file_path:
            return
        self.data_handler.data.to_csv(file_path)
        # Create an image exporter
        exporter = ImageExporter(self.plt_sequence.scene())
        exporter.parameters()['width'] = 1600  # Set image width (optional)
        exporter.export(f'{file_path[0:-4]}.png')  # Save as PNG

        with open(os.path.join(target_dir, filename_config), "w", encoding="utf-8") as f:
            json.dump(self.parent.config_selector.selected_config, f, indent=4)
        # rename videofile
        if self.recorder and Path('TEST-DATA/temp.mp4').exists():
            temp_video_file = Path('TEST-DATA/temp.mp4')
            new_video_file = Path(target_dir) / Path(filename[0:-4] + ".mp4")
            temp_video_file.rename(new_video_file)

    def zero_values(self):
        self.communicator.zero()

    def reset_offsets(self):
        self.communicator.reset_offsets()

    def closeEvent(self, event):
        self.communicator.zero_output()
        event.accept()  # Proceed with closing


class PlotHandler:
    colors = [(255, 0, 0),  # Red
              (0, 255, 0),  # Green
              (0, 0, 255),  # Blue
              (255, 0, 255),  # Magenta
              (0, 255, 255),  # Cyan
              (255, 165, 0)]  # Orange
    def __init__(self, list_plots, communicator):
        self.list_plots = list_plots
        self.communicator = communicator
        self.data_handler = communicator.data_handler
        self.res = list_plots[0]
        self.pow = list_plots[1]
        self.force = list_plots[2]
        self.laser = list_plots[3]
        res = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
        self.res_artists = {}
        for i, r in enumerate(res):
            self.res_artists[r] = self.res.plot(pen=self.colors[i],
                                                name=r)

        if self.communicator.smapoc_mode == ids.POWER:
            pow = ['pow1', 'pow2', 'pow3', 'pow4', 'pow5', 'pow6']
        else:
            pow = ['curr1', 'curr2', 'curr3', 'curr4', 'curr5', 'curr6']

        self.pow_artists = {}
        for i, p in enumerate(pow):
            self.pow_artists[p] = self.pow.plot(pen=self.colors[i],
                                                name=p)
        self.laser_artist = self.laser.plot(pen=self.colors[0],
                                            name='Laser')
        self.force_artist = self.force.plot(pen=self.colors[0],
                                            name='Force')




    def update_res(self):
        for name, artist in self.res_artists.items():
            if name in self.data_handler.data.keys():
                artist.setData(self.data_handler.data['time'], self.data_handler.data[name])

    def update_pow(self):
        for name, artist in self.pow_artists.items():
            if name in self.data_handler.data.keys():
                artist.setData(self.data_handler.data['time'], self.data_handler.data[name])

    def update_laser(self):
        self.laser_artist.setData(self.data_handler.data['time'], self.data_handler.data['laser'])

    def update_force(self):
        self.force_artist.setData(self.data_handler.data['time'], self.data_handler.data['force'])


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    win = ScriptExecutor()
    win.resize(600, 400)
    win.show()
    sys.exit(app.exec_())
