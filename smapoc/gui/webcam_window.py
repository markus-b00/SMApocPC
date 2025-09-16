import PyQt5.QtWidgets as qtw
import pyqtgraph as pg
import PyQt5.QtCore as qtc
import numpy as np
import cv2
from smapoc import ids


class FloatingCameraWindow(qtw.QDialog):
    def __init__(self, webcam_obj):
        super().__init__()
        self.webcam_obj = webcam_obj
        self.webcam_obj.frame_received.connect(self.update_frame)

        self.setWindowTitle("Floating Camera with PyQtGraph")
        self.setWindowFlags(qtc.Qt.Window)

        # Set up pyqtgraph image view
        self.image_item = pg.ImageItem()
        self.view_box = pg.ViewBox()
        self.view_box.addItem(self.image_item)
        self.view_box.invertY(True)  # Match image coordinate system
        self.view_box.setAspectLocked(True)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setCentralItem(self.view_box)
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.hideAxis('bottom')
        self.plot_widget.hideAxis('left')

        layout = qtw.QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)



    @qtc.pyqtSlot(int, np.ndarray)
    def update_frame(self, myid, frame: np.ndarray):
        """Slot to receive and display a new frame (as a NumPy array)."""
        if myid == ids.FROM_WEBCAM:
            if frame is None:
                return
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.image_item.setImage(np.rot90(frame_rgb, k=1), autoLevels=False)

