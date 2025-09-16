import logging
import os
import sys
import json
import PyQt5.QtCore as qtc
from PyQt5.QtWidgets import (
    QApplication, QDialog, QListWidget, QPushButton, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox
)
from smapoc.gui.UI_config_selector import Ui_Dialog
from smapoc.gui import device_wizard
from smapoc.gui.dialogs import PeripheralStatusDialog
from smapoc import ids


class ConfigDialog(QDialog, Ui_Dialog):
    def __init__(self, data_handler, config_list=None, config_file=None):
        super().__init__()
        self.data_handler = data_handler
        self.setupUi(self)
        self.setWindowTitle("Select Configuration")
        self.resize(800, 400)
        self.config_list_data = config_list if config_list else []
        # Load from file if provided
        if config_file:
            self.config_file = config_file
            self.load_config_from_file(self.config_file)
        # Connecting gui elements
        self.btn_load.clicked.connect(self.load_config)
        self.btn_export.clicked.connect(self.export_config)
        self.btn_delete.clicked.connect(self.delete_config)
        self.buttonBox.accepted.connect(self.accept_config)
        self.buttonBox.rejected.connect(self.reject)
        self.listWidget_configs.currentRowChanged.connect(self.display_config)
        self.btn_new.clicked.connect(self.open_wizard)
        self.selected_config = None

        count = self.listWidget_configs.count()
        if count > 0:
            last_item = self.listWidget_configs.item(count - 1)
            self.listWidget_configs.setCurrentItem(last_item)

            self.listWidget_configs.scrollToItem(last_item)


    def open_wizard(self):
        self.wizard = device_wizard.DeviceWizard(self)
        if self.wizard.exec_() == QDialog.Accepted:
            config = self.wizard.new_config
            self.add_new_config(config)


    def display_config(self, index):
        if index < 0:
            return

        config = self.config_list_data[index]["devices"]

        # Collect all unique field names across all devices
        all_fields = set()
        for device_info in config.values():
            all_fields.update(device_info.keys())

        # Sort fields for consistent column order
        all_fields = sorted(all_fields)
        headers = ["Device"] + all_fields

        self.tableWidget_details.clear()
        self.tableWidget_details.setRowCount(0)
        self.tableWidget_details.setColumnCount(len(headers))
        self.tableWidget_details.setHorizontalHeaderLabels(headers)

        for row_index, (device_name, device_info) in enumerate(config.items()):
            self.tableWidget_details.insertRow(row_index)
            self.tableWidget_details.setItem(row_index, 0, QTableWidgetItem(device_name))
            for col_index, field in enumerate(all_fields, start=1):
                value = device_info.get(field, "-")
                if isinstance(value, list):
                    value = str(value)
                self.tableWidget_details.setItem(row_index, col_index, QTableWidgetItem(str(value)))

    def accept_config(self):
        index = self.listWidget_configs.currentRow()
        if index >= 0:
            self.selected_config = self.config_list_data[index]
        self.accept()

    def load_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Config File", "", "JSON Files (*.json)")
        if path:
            self.load_config_from_file(path)

    def load_config_from_file(self, path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for cfg in data:
                        self.config_list_data.append(cfg)
                        self.listWidget_configs.addItem(cfg["name"])
                elif isinstance(data, dict):
                    self.config_list_data.append(data)
                    self.listWidget_configs.addItem(data["name"])
                else:
                    QMessageBox.warning(self, "Error", "Invalid configuration file format.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config:\n{str(e)}")

    def export_config(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Config File", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'w') as f:
                    json.dump(self.config_list_data, f, indent=4)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save config:\n{str(e)}")

    def save_config(self):
        # save current to standard output file
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config_list_data, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config:\n{str(e)}")

    def delete_config(self):
        index = self.listWidget_configs.currentRow()
        if index < 0:
            QMessageBox.warning(self, "No selection", "Please select a config to delete.")
            return

        name = self.config_list_data[index]["name"]
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            del self.config_list_data[index]
            self.listWidget_configs.takeItem(index)
            self.tableWidget_details.clearContents()
            self.tableWidget_details.setRowCount(0)
            # Optional: save after delete
            self.save_config()

    def add_new_config(self, config_dict):
        if not isinstance(config_dict, dict) or "name" not in config_dict or "devices" not in config_dict:
            QMessageBox.warning(self, "Invalid Config", "The configuration must be a dict with 'name' and 'devices'.")
            return

        # Check for duplicate name
        existing_names = [cfg["name"] for cfg in self.config_list_data]
        if config_dict["name"] in existing_names:
            QMessageBox.warning(self, "Duplicate Name",
                                f"A configuration named '{config_dict['name']}' already exists.")
            return

        # Add to list and UI
        self.config_list_data.append(config_dict)
        self.listWidget_configs.addItem(config_dict["name"])

        # Save and refresh UI
        self.save_config()
        self.listWidget_configs.setCurrentRow(self.listWidget_configs.count() - 1)


class ConfigLoader(qtc.QObject):
    loader_finished = qtc.pyqtSignal()

    def __init__(self, parent, communicator):
        super().__init__()
        self.parent = parent
        self.communicator = communicator
        self.status_dialog = PeripheralStatusDialog()
        self.selected_config = None
        self.counter = 0
        self.state_handler = None




    def load(self, selected_config):
        # Start with the laser sensor
        self.status_dialog.show()
        self.selected_config = selected_config
        self.state_handler = StateHandler(self.communicator, self.selected_config, self.status_dialog)
        self.state_handler.jobs_done.connect(self.jobs_done)
        self.state_handler.prepare_job()

    def jobs_done(self):
        self.loader_finished.emit()
        self.status_dialog.accept()








class StateHandler(qtc.QObject):
    jobs_done = qtc.pyqtSignal()
    def __init__(self, communicator, selected_config, status_dialog):
        super().__init__()
        self.communicator = communicator
        self.selected_config = selected_config
        self.status_dialog = status_dialog
        self.list_peripherals = list(self.selected_config['devices'].keys())
        self.status_jobs = {}
        self.pointer = 0
        self.connected_pers = None

    def prepare_job(self):
        logging.debug(f'pointer: {self.pointer}, len {len(self.list_peripherals)}')
        if self.pointer < len(self.list_peripherals):
            candidate = self.list_peripherals[self.pointer]
            self.pointer += 1
            self.do_action(candidate)
        else:
            self.jobs_done.emit()

    def do_action(self, name):

        match name:
            case 'SMAPOC':
                port = self.selected_config['devices']['SMAPOC']['port']
                self.communicator.add_smapoc(port)
                self.communicator.devices['smapoc'].data_received.connect(self.callback)
                self.communicator.devices['smapoc'].self_test(myid=ids.SELFTEST_SMAPOC)

            case 'LASER':
                port = self.selected_config['devices']['LASER']['port']
                sn = self.selected_config['devices']['LASER']['sn']
                self.communicator.add_laser(port, sn)
                self.communicator.devices['laser'].data_received.connect(self.callback)
                self.communicator.devices['laser'].self_test(myid=ids.SELFTEST_LASER)

            case 'FORCE':
                port = self.selected_config['devices']['FORCE']['port']
                force_profile = self.selected_config['devices']['FORCE']['params']
                logging.debug(force_profile)
                self.communicator.add_force(port, force_profile)
                self.communicator.devices['force'].data_received.connect(self.callback)
                self.communicator.devices['force'].self_test(myid=ids.SELFTEST_FORCE)
            case 'WEBCAM':
                logging.debug('add webcam')
                number = self.selected_config['devices']['WEBCAM']['number']
                self.communicator.add_webcam(number)
                self.prepare_job()

    def callback(self, myid, value):
        self.callback_action(myid, value)


    def callback_action(self, myid, value):
        match myid:
            case ids.SELFTEST_SMAPOC:
                if len(value) == 8:
                    state = True
                else:
                    state = False
                self.status_jobs['smapoc'] = state
                self.prepare_job()



            case ids.SELFTEST_LASER:
                if len(value) == 2:
                    state = True

                else:
                    state = False
                self.status_jobs['laser'] = state
                self.prepare_job()



            case ids.SELFTEST_FORCE:
                if len(value) == 1:
                    state = True
                else:
                    state = False
                self.status_jobs['force'] = state
                self.prepare_job()




if __name__ == "__main__":
    app = QApplication(sys.argv)
    config_file_path = "../config_file.json"  # Path to initial JSON file
    dialog = ConfigDialog(config_file=config_file_path)

    result = dialog.exec_()
    if result == QDialog.Accepted:
        print("Selected config:", json.dumps(dialog.selected_config, indent=4))
    else:
        print("Cancelled")

