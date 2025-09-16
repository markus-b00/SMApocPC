import PyQt5.QtWidgets as qtw
import PyQt5.QtCore as qtc
import pyqtgraph as pg
import cv2
import numpy as np
import subprocess

class CameraWindow:
    def __init__(self, parent, device_obj):
        self.parent = parent
        self.device = device_obj
        self.device.frame_received.connect(self.update)

        self.dock = qtw.QDockWidget("Webcam", self.parent)
        self.dock.setAllowedAreas(qtc.Qt.AllDockWidgetAreas)  # Allow moving anywhere
        # Enable full resizing
        self.dock.setFeatures(
            qtw.QDockWidget.DockWidgetMovable | qtw.QDockWidget.DockWidgetClosable | qtw.QDockWidget.DockWidgetFloatable)

        # Set expanding size policy
        self.dock.setSizePolicy(self.dock.sizePolicy().Expanding, self.dock.sizePolicy().Expanding)

        # Add to main window

        self.dock_content = qtw.QWidget(self.dock)
        layout = qtw.QVBoxLayout(self.dock_content)
        self.dock.setWidget(self.dock_content)
        self.win = pg.GraphicsLayoutWidget(show=True)
        layout.addWidget(self.win)
        self.view_box = self.win.addViewBox(lockAspect=True)
        self.view_box.setAspectLocked(True)  # Lock aspect ratio
        self.img_item = pg.ImageItem()
        self.view_box.addItem(self.img_item)
        self.parent.addDockWidget(qtc.Qt.RightDockWidgetArea, self.dock)
        self.btn_settings = qtw.QPushButton('Cam Settings')
        self.btn_settings.clicked.connect(self.open_cam_settings)
        layout.addWidget(self.btn_settings)

    def update(self, myid, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
        frame = cv2.flip(frame, -1)  # Flip horizontally
        self.img_item.setImage(np.rot90(frame), autoLevels=False)

    def open_cam_settings(self):
        subprocess.Popen(['C:/Program Files (x86)/Common Files/LogiShrd/LWSPlugins/LWS/Applets/CameraHelper/CameraHelperShortcut.exe'])



def find_webcams():
    # available_cams = []
    # for i in range(1):  # Try the first 10 indices
    #     cap = cv2.VideoCapture(i)
    #     if cap.isOpened():  # Check if the camera is available
    #         available_cams.append(i)
    #         cap.release()
    return [1,2]
