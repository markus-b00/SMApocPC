import os
import pandas as pd
import numpy as np
from datetime import datetime
import json

import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg

from pyqtgraph.exporters import ImageExporter
from pyqtgraph import DateAxisItem

import logging
import pyqtgraph as pg
from smapoc.gui.UI_stiffness import Ui_DialogStiffness
from smapoc.gui.dialogs import LineDialog
from smapoc import ids


logging.getLogger(__name__)


class StiffnessPlot(qtw.QDialog, Ui_DialogStiffness):
    colors = [(255, 0, 0),  # Red
              (0, 255, 0),  # Green
              (0, 0, 255),  # Blue
              (255, 0, 255),  # Magenta
              (0, 255, 255),  # Cyan
              (255, 165, 0)]  # Orange
    sample_time = np.linspace(0, 10, 1000)
    sample_df = pd.DataFrame({'time': sample_time,
                              'pow1': np.sin(sample_time),
                              'pow2': np.cos(sample_time),
                              'pow3': np.atan(5*sample_time)})

    def __init__(self, parent, data_handler, communicator, ):
        super().__init__()
        self.setupUi(self)
        pg.setConfigOptions(antialias=True)
        self.parent = parent
        self.data_handler = data_handler
        self.interval = 100
        self.plot_timer = qtc.QTimer()
        self.plot_timer.timeout.connect(self.update_plot)




        self.data_handler = data_handler
        self.communicator = communicator
        self.data_handler.transfer_collected()
        # current data column labels
        self.x_name = None
        self.y_name = None
        self.state = False
        self.line = None
        self.line_state = False
        self.test_name = None



        self.btn_start_stop.clicked.connect(self.toggle_plotting)
        self.btn_zero_force.clicked.connect(self.zero_force)
        self.btn_zero_laser.clicked.connect(self.zero_laser)

        self.btn_approx.clicked.connect(self.toggle_line)
        self.btn_save.clicked.connect(self.save_csv)

        self.p1 = self.plt_stiffness.addPlot(title='Stiffness')
        # Set X and Y axis labels
        self.p1.setLabel('left', 'Force')  # 'left' refers to Y axis
        self.p1.setLabel('bottom', 'Displacement')  # 'bottom' refers to X axis
        self.p1.showGrid(x=True, y=True)
        self.comboBox_source_x.currentIndexChanged.connect(self.update_data_source)
        self.comboBox_source_y.currentIndexChanged.connect(self.update_data_source)







    def toggle_line(self):
        if self.line_state:
            self.line_state = False
            self.p1.removeItem(self.line)
        else:
            self.line_state = True
            self.line = DraggableLine(self.p1, self.lbl_formula)
            self.line.return_slope.connect(self.update_label)

    def update_label(self, coeff):
        formula = f'y={coeff[0]:.3f}x + {coeff[1]:.3f}'
        self.lbl_formula.setText(formula)
        self.p1.setTitle(f'Stiffness {formula}')

    def toggle_plotting(self):
        if self.state:
            self.state = False
            self.btn_start_stop.setText('Start')
            self.communicator.stop_requesting()
            self.plot_timer.stop()
            #vb = self.p1.getViewBox()
            #vb.setMouseEnabled(x=True, y=True)

        else:
            self.state = True

            self.btn_start_stop.setText('Stop')
            self.data_handler.data_clear()
            self.communicator.start_requesting()
            self.plot_timer.start(self.interval)
            # Assuming 'plot' is a PlotItem
            #vb = self.p1.getViewBox()
            # Update axis limits
            #vb.setLimits(xMin=-0.1, xMax=0.15, yMin=-0.1, yMax=0.5)

    def reset_offsets(self):
        self.communicator.reset_offsets()


    def zero_force(self):
            self.communicator.zero(what='force')

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

    def update_data_source(self):
        self.x_name = self.comboBox_source_x.currentText()
        self.y_name = self.comboBox_source_y.currentText()


    def update_plot(self):
        self.p1.clear()
        if all(col in self.data_handler.data.columns for col in [self.x_name, self.y_name]):
            self.p1.plot(self.data_handler.data[self.x_name],
                         self.data_handler.data[self.y_name],
                         pen=self.colors[0])
            self.p1.plot(self.data_handler.data[self.x_name][-2:-1],
                         self.data_handler.data[self.y_name][-2:-1],
                         pen=self.colors[1],
                         symbol='o')

    def save_csv(self):
        sample_dialog = LineDialog(title="Sample name", text="Enter sample name")
        sample_name = sample_dialog.get_config_name()


        m, b = self.line.get_slope()
        base_dir = os.path.abspath(os.getcwd())
        test_folder = self.test_name
        target_dir = os.path.join(base_dir, "TEST-DATA", test_folder)

        # Step 2: Ensure directory exists
        os.makedirs(target_dir, exist_ok=True)

        # Step 5: Write sample CSV data
        # Create a filename with datetime prefix
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{sample_name}_stiffness{m:.3f}.csv"
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
        exporter = ImageExporter(self.p1)
        exporter.parameters()['width'] = 800  # Set image width (optional)
        exporter.export(f'{file_path[0:-4]}.png')  # Save as PNG
        print(self.parent.config_selector.selected_config)
        with open(os.path.join(target_dir, filename_config), "w", encoding="utf-8") as f:
            json.dump(self.parent.config_selector.selected_config, f, indent=4)


    def show(self, test_name='BSAT2.1'):
        self.setWindowTitle(test_name)
        self.test_name = test_name
        self.comboBox_source_x.clear()
        self.comboBox_source_x.addItems(self.data_handler.get_col_names())
        self.comboBox_source_y.clear()
        self.comboBox_source_y.addItems(self.data_handler.get_col_names())
        print(self.data_handler.get_col_names())
        # preset laser and force signal
        index = self.comboBox_source_x.findText("laser")
        if index != -1:
            self.comboBox_source_x.setCurrentIndex(index)

        index = self.comboBox_source_x.findText("force")
        if index != -1:
            self.comboBox_source_y.setCurrentIndex(index)

        self.exec_()

    def closeEvent(self, event):
        self.communicator.zero_output()
        event.accept()  # Proceed with closing




class DraggableLine(qtw.QWidget):
    return_slope = qtc.pyqtSignal(list)
    def __init__(self, plot_widget, label_formula):
        super().__init__()
        self.plot_widget = plot_widget
        self.label_formula = label_formula
        self.m = 0
        self.b = 0

        # Initial positions
        self.positions = [(0, 0), (0.75, 0.3)]

        # Line item
        self.line = pg.PlotDataItem(pen=pg.mkPen('g', width=2))
        self.plot_widget.addItem(self.line)

        # Draggable points
        self.points = []
        for i, (x, y) in enumerate(self.positions):
            color = 'r' if i == 0 else 'b'
            pt = DraggablePoint(i, (x, y), color, self.point_moved)
            self.points.append(pt)
            self.plot_widget.addItem(pt)

        # Text item to display the equation using QLabel
        self.label_formula = qtw.QLabel(self)
        self.label_formula.setStyleSheet("font-size: 16px; font-weight: bold; color: black;")
        self.label_formula.setText("Test")  # Placeholder
        self.update_line()

    def point_moved(self, index, pos):
        self.positions[index] = pos
        self.update_line()

    def update_line(self):
        x, y = zip(*self.positions)
        self.line.setData(x, y)

        # Calculate the equation of the line (y = mx + b)
        self.m, self.b = self.calculate_slope_intercept(self.positions)

        # Equation format: y = mx + b
        equation = f"y = {self.m:.2f}x + {self.b:.2f}"
        self.label_formula.setText(equation)  # Update the displayed equation

    def calculate_slope_intercept(self, points):
        # Calculate slope (m) and intercept (b) from two points
        (x1, y1), (x2, y2) = points
        if x2 - x1 == 0:  # To avoid division by zero if x1 == x2
            m = float('inf')  # Vertical line
            b = x1  # x = b (vertical line at x = b)
        else:
            m = (y2 - y1) / (x2 - x1)
            b = y1 - m * x1
        self.return_slope.emit([m, b])
        return m, b

    def get_slope(self):
        return self.m, self.b



class DraggablePoint(pg.ScatterPlotItem):
    def __init__(self, index, pos, color, on_move_callback):
        super().__init__(
            x=[pos[0]],
            y=[pos[1]],
            brush=pg.mkBrush(color),
            size=10,
            symbol='o'
        )
        self.index = index
        self.on_move_callback = on_move_callback
        self.setZValue(10)
        self.moving = False

    def mousePressEvent(self, ev):
        if ev.button() == qtc.Qt.LeftButton:
            self.moving = True
            ev.accept()
        else:
            ev.ignore()

    def mouseMoveEvent(self, ev):
        if self.moving:
            pos = self.mapToParent(ev.pos())
            self.setData(x=[pos.x()], y=[pos.y()])
            self.on_move_callback(self.index, (pos.x(), pos.y()))
            ev.accept()

    def mouseReleaseEvent(self, ev):
        self.moving = False
        ev.accept()