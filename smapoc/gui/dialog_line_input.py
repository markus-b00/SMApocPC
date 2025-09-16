from star.gui.UI_config_name import Ui_Dialog_config_name

import PyQt5.QtCore as qtc
import PyQt5.QtGui as qtg
import PyQt5.QtWidgets as qtw


class LineDialog(qtw.QDialog,Ui_Dialog_config_name):
    def __init__(self):
        super().__init__()
