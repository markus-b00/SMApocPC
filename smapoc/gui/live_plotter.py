
import pandas as pd
import numpy as np
import PyQt5.QtCore as qtc
import PyQt5.QtWidgets as qtw
import PyQt5.QtGui as qtg
from pyqtgraph import DateAxisItem
import logging
import pyqtgraph as pg
logging.getLogger(__name__)

class LivePlot(qtc.QObject):
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

    def __init__(self, parent, data_handler=None, **kwargs):
        super().__init__()
        pg.setConfigOptions(antialias=True)
        self.parent = parent
        self.plot_timer = qtc.QTimer()
        self.plot_timer.timeout.connect(self.update_plot)

        if data_handler is None:
            self.data_handler = self.sample_df
            self.names_x = ['time']
            self.names_y = ['pow1', 'pow2', 'pow3']
            self.title = kwargs['title']

        else:
            self.data_handler = data_handler
            self.data_handler.plot_status.connect(self.plot_status_changed)
            self.data_handler.plot_interval.connect(self.set_interval)

        try:
            self.names_x = kwargs['list_x']
            self.names_y = kwargs['list_y']
            self.title = kwargs['title']
        except KeyError as e:
            logging.warning(e)

        self.dock = qtw.QDockWidget(self.title, self.parent)
        self.dock.setAllowedAreas(qtc.Qt.AllDockWidgetAreas)  # Allow moving anywhere
        # Enable full resizing
        self.dock.setFeatures(qtw.QDockWidget.DockWidgetMovable | qtw.QDockWidget.DockWidgetClosable | qtw.QDockWidget.DockWidgetFloatable)

        # Set expanding size policy
        self.dock.setSizePolicy(self.dock.sizePolicy().Expanding, self.dock.sizePolicy().Expanding)

        # Add to main window
        self.parent.addDockWidget(qtc.Qt.RightDockWidgetArea, self.dock)

        self.dock_content = qtw.QWidget(self.dock)
        self.layout = qtw.QVBoxLayout(self.dock_content)
        self.dock.setWidget(self.dock_content)
        self.win = pg.GraphicsLayoutWidget(show=True, title=self.title)
        self.layout.addWidget(self.win)
        self.p1 = self.win.addPlot(title=self.title)
        self.p1.addLegend()
        self.p1_artists = {}
        # Placeholders
        self.fit_line = None
        self.formula_text = None

        #self.group_graph_items = qtw.QGroupBox(title='graph_items')
        #self.layout.addWidget(self.group_graph_items)

        self.dict_radio_buttons = {}
        self.h_layout = qtw.QHBoxLayout()
        self.layout.addLayout(self.h_layout)
        self.layout.setStretch(0, 10)
        self.layout.setStretch(1, 0)

        # if webcam is selected
        if 'WEBCAM' in self.names_x or 'WEBCAM' in self.names_y:
            self.img_item = pg.ImageItem()
            self.view = pg.ImageView()
            self.view.addItem(self.img_item)
            self.view = self.win.addViewBox()
            self.view.setAspectLocked(True)  # Lock aspect ratio
        else:

            for i, col in enumerate(self.names_y):
                self.dict_radio_buttons[col] = FilterRadioButton(self, col)
                self.dict_radio_buttons[col].setText(col)
                self.dict_radio_buttons[col].setAutoExclusive(False)
                self.dict_radio_buttons[col].setChecked(True)
                self.dict_radio_buttons[col].filter_changed.connect(self.filter_data)
                self.h_layout.addWidget(self.dict_radio_buttons[col])
                self.p1_artists[col] = self.p1.plot(self.data_handler.data[self.names_x[0]],
                                                    self.data_handler.data[col],
                                                    name=col,
                                                    pen=self.colors[i],
                                                    symbol='o')
                self.p1.getViewBox().sigRangeChanged.connect(self.updateSymbols)

            # set radio button for approx
            self.radio_button_approx = qtw.QRadioButton("Fit data")
            self.radio_button_approx.setAutoExclusive(False)
            self.radio_button_approx.setChecked(False)
            self.h_layout.addWidget(self.radio_button_approx)
            self.radio_button_approx.toggled.connect(self.toggle_fit)


            self.h_layout.addItem(qtw.QSpacerItem(0, 0, qtw.QSizePolicy.Expanding, qtw.QSizePolicy.Minimum))

    def set_interval(self, interval):
        self.plot_timer.setInterval(interval)

    def toggle_fit(self, checked):
        if checked:
            # Calculate and plot linear fit
            coeffs = np.polyfit(self.data_handler.data[self.names_x[0]],
                                self.data_handler.data[self.names_y[0]], 1)
            slope, intercept = coeffs
            fit_y = slope * self.data_handler.data[self.names_x[0]] + intercept
            self.fit_line = self.p1.plot(self.data_handler.data[self.names_x[0]], fit_y, pen=pg.mkPen('y', width=2))
            formula_str = f"y = {slope:.3f}x + {intercept:.3f}"

            self.formula_text = pg.TextItem(text=formula_str, color='y', anchor=(0, 1))
            # Set custom font size: Change the font size as desired here
            font = qtg.QFont("Sans Serif", 14)  # 14-point font
            self.formula_text.setFont(font)
            # Update label with formatted formula
            view_box = self.p1.getViewBox()
            x_range, y_range = view_box.viewRange()
            self.formula_text.setPos(x_range[0] + 0.5, y_range[1] - 1)
            self.p1.addItem(self.formula_text)
        else:
            # Remove fit line and clear label
            # Remove fit line and annotation
            if self.fit_line is not None:
                self.p1.removeItem(self.fit_line)
                self.fit_line = None
            if self.formula_text is not None:
                self.p1.removeItem(self.formula_text)
                self.formula_text = None



    def plot_status_changed(self, status):
        if status:
            self.plot_timer.start(80)
            logging.debug('start plotting')
        else:
            self.plot_timer.stop()
            logging.debug('stop plotting')



    def filter_data(self, name, value):
        if value:
            if name in self.names_y:
                pass
            else:
                self.names_y.append(name)
        else:
            self.names_y.remove(name)
        self.redraw_plot()

    def update_plot(self):
        for i, col in enumerate(self.names_y):
            self.p1_artists[col].setData(self.data_handler.data[self.names_x[0]],
                                         self.data_handler.data[col])

    def redraw_plot(self):
        self.clear_plot()
        for i, col in enumerate(self.names_y):
            self.p1_artists[col] = self.p1.plot(self.data_handler.data[self.names_x[0]],
                                                self.data_handler.data[col],
                                                name=col,
                                                pen=self.colors[i],
                                                symbol='o')

    def clear_plot(self):
        self.p1.clear()
        if self.fit_line is not None:
            self.p1.removeItem(self.fit_line)
            self.fit_line = None
        if self.formula_text is not None:
            self.p1.removeItem(self.formula_text)
            self.formula_text = None

    def updateSymbols(self):
        view_range = self.p1.viewRange()
        x_range = (view_range[0][1] - view_range[0][0])   # Adjust sensitivity
        if x_range < 5:
            for i, name in enumerate(self.p1_artists):
                self.p1_artists[name].setSymbol('o')
                self.p1_artists[name].setSymbolSize(4)
                self.p1_artists[name].setSymbolBrush(self.colors[i])
        else:
            for i, name in enumerate(self.p1_artists):
                self.p1_artists[name].setSymbol(None)  # Hide symbols




class FilterRadioButton(qtw.QRadioButton):
    filter_changed = qtc.pyqtSignal(str,bool)

    def __init__(self, parent, col_name):
        super().__init__()
        self.parent = parent

        self.col_name = col_name
        self.clicked.connect(self.update_df)


    def update_df(self):
        if self.isChecked():
            self.filter_changed.emit(self.col_name, True)
        else:
            self.filter_changed.emit(self.col_name, False)



