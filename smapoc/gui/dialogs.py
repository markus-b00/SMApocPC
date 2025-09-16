from smapoc.gui.UI_plot_selector import Ui_Dialog_Plot_Selector
from smapoc.gui.UI_config_name import Ui_Dialog_config_name
import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc

class DialogPlotSelector(qtw.QDialog, Ui_Dialog_Plot_Selector):


    def __init__(self, parent, data_handler):
        super().__init__()
        self.parent = parent
        self.data_handler = data_handler
        self.data = self.data_handler.data

        self.setupUi(self)
        self.listWidget_available_x.addItems(self.data.columns)
        if 'WEBCAM' in self.parent.communicator.devices.keys():
            self.listWidget_available_x.addItem('WEBCAM')
        self.listWidget_available_y.addItems(self.data.columns)

        self.btn_select_x.clicked.connect(self.move_to_sel_x)
        self.btn_deselect_x.clicked.connect(self.move_to_avail_x)
        self.btn_select_y.clicked.connect(self.move_to_sel_y)
        self.btn_deselect_y.clicked.connect(self.move_to_avail_y)



    @staticmethod
    def move_selected_items(source, destination):
        selected_items = source.selectedItems()
        for item in selected_items:
            destination.addItem(item.text())
            source.takeItem(source.row(item))  # Remove from source

    def move_to_sel_x(self):
        self.move_selected_items(self.listWidget_available_x, self.listWidget_selected_x)

    def move_to_avail_x(self):
        self.move_selected_items(self.listWidget_selected_x, self.listWidget_available_x)

    def move_to_sel_y(self):
        self.move_selected_items(self.listWidget_available_y, self.listWidget_selected_y)

    def move_to_avail_y(self):
        self.move_selected_items(self.listWidget_selected_y, self.listWidget_available_y)

    def get_data(self):
        list_x = [self.listWidget_selected_x.item(i).text() for i in range(self.listWidget_selected_x.count())]
        list_y = [self.listWidget_selected_y.item(i).text() for i in range(self.listWidget_selected_y.count())]
        return {'list_x': list_x, 'list_y': list_y, 'title': self.lineEdit_plot_title.text()}




class LineDialog(qtw.QDialog, Ui_Dialog_config_name):
    def __init__(self, title=None, text=None):
        super().__init__()
        self.setupUi(self)
        if title:
            self.setWindowTitle(title)
        if text:
            self.label.setText(text)
        self.exec_()


    def get_config_name(self):
        return self.lineEdit_config_name.text()


class PeripheralStatusDialog(qtw.QDialog):
    def __init__(self, peripheral_statuses=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Peripheral Status")
        self.setMinimumWidth(300)

        self.main_layout = qtw.QVBoxLayout()

        # Add initial peripherals if provided
        if peripheral_statuses:
            for peripheral, is_active in peripheral_statuses:
                self.add_peripheral_status(peripheral, is_active)

        # OK button
        self.button_box = None




    def add_peripheral_status(self, peripheral, is_active):
        row_layout = qtw.QHBoxLayout()

        label = qtw.QLabel(peripheral)
        label.setAlignment(qtc.Qt.AlignLeft | qtc.Qt.AlignVCenter)

        status_label = qtw.QLabel("✅" if is_active else "❌")
        status_label.setAlignment(qtc.Qt.AlignRight | qtc.Qt.AlignVCenter)
        status_label.setStyleSheet("font-size: 16px;")

        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(status_label)

        # Insert above the button box
        self.main_layout.insertLayout(self.main_layout.count() - 1, row_layout)
        self.setLayout(self.main_layout)

    def add_ok_button(self):
        self.button_box = qtw.QDialogButtonBox(qtw.QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        self.main_layout.addWidget(self.button_box)
        self.setLayout(self.main_layout)
