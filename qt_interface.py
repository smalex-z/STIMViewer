# \file    qt_interface.py
# \author  IDS Imaging Development Systems GmbH
# \date    2024-02-20
#
# \brief   This sample showcases the usage of the ids_peak API
#          in setting camera parameters, starting/stopping the image acquisition
#          and how to record a video using the ids_peak_ipl API.
#
# \version 1.0
#
# Copyright (C) 2024, IDS Imaging Development Systems GmbH.
#
# The information in this document is subject to change without notice
# and should not be construed as a commitment by IDS Imaging Development Systems GmbH.
# IDS Imaging Development Systems GmbH does not assume any responsibility for any errors
# that may appear in this document.
#
# This document, or source code, is provided solely as an example of how to utilize
# IDS Imaging Development Systems GmbH software libraries in a sample application.
# IDS Imaging Development Systems GmbH does not assume any responsibility
# for the use or reliability of any portion of this document.
#
# General permission to copy or modify is hereby granted.

import sys
import time

from typing import Optional

from camera import Camera
from time import time
from display import Display
from ids_peak import ids_peak

try:
    from PyQt5 import QtCore, QtWidgets, QtGui
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtCore import pyqtSlot as Slot
    from PyQt5.QtWidgets import QLabel
except ImportError:
    from PyQt5 import QtCore, QtWidgets, QtGui
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtCore import pyqtSlot as Slot
    from PyQt5.QtWidgets import QLabel


ids_peak.Library.Initialize()
print("IDS peak library initialized.")

class Interface(QtWidgets.QMainWindow):
    """
    Interface provides a GUI to interact with the camera,
    but it is not necessary to understand how to use the API of ids_peak or
    ids_peak_ipl.
    """

    messagebox_signal = QtCore.pyqtSignal((str, str))
    start_button_signal = QtCore.pyqtSignal()

    def __init__(self, cam_module: Optional[Camera] = None):
        """
        :param cam_module: Camera object to access parameters
        """
        qt_instance = QtWidgets.QApplication(sys.argv)
        super().__init__()
        self.last_frame_time = time()  # Track time of the last frame



        self._camera = cam_module

        self.widget = QtWidgets.QWidget(self)
        self._layout = QtWidgets.QVBoxLayout()
        self.widget.setLayout(self._layout)
        self.setCentralWidget(self.widget)
        self.display = None
        self._qt_instance = qt_instance
        self._qt_instance.aboutToQuit.connect(self._close)
        self.acquisition_thread = None

        # Buttons
        self._button_start = None
        self._button_exit = None
        self._button_software_trigger = None
        self._button_start_acquisition = None
        self._button_stop_acquisition = None
        self._checkbox_save = None
        self._button_exit = None
        self._dropdown_pixel_format = None

        #FPS Label
        self.fps_label = QLabel("FPS: 0.00", self)
        self.fps_label.setStyleSheet("font-size: 14px; color: green;")
        self.fps_label.setAlignment(Qt.AlignRight)


        self.messagebox_signal[str, str].connect(self.message)

        self._frame_count = 0
        self._fps_label = None
        self._error_cont = 0
        self._gain_label = None

        self._label_infos = None
        self._label_version = None
        self._label_aboutqt = None

        self._fps_slider = None
        self._gain_slider = None

        self.recording_time = 10
        self.setMinimumSize(700, 650)

    # Common interface start
    def is_gui(self):
        return True
    
    def set_camera(self, cam_module):
        self._camera = cam_module
    
    def _create_button_bar(self):
        #Software Trigger
        self._checkbox_save = QtWidgets.QCheckBox("save image to computer")
        self._checkbox_save.setChecked(False)

        self._dropdown_pixel_format = QtWidgets.QComboBox()
        formats = self._camera.node_map.FindNode("PixelFormat").Entries()
        for idx in formats:
            if (idx.AccessStatus() != ids_peak.NodeAccessStatus_NotAvailable
                    and idx.AccessStatus() != ids_peak.NodeAccessStatus_NotImplemented
                    and self._camera.conversion_supported(idx.Value())):
                self._dropdown_pixel_format.addItem(idx.SymbolicValue())
        self._dropdown_pixel_format.currentIndexChanged.connect(
            self.change_pixel_format)

        self._button_software_trigger = QtWidgets.QPushButton(
            "Software Trigger")
        self._button_software_trigger.clicked.connect(self._trigger_sw_trigger)

        self._button_start_acquisition = QtWidgets.QPushButton(
            "Start Acquisition")
        self._button_start_acquisition.clicked.connect(self._start_acquisition)
        self._button_stop_acquisition = QtWidgets.QPushButton(
            "Stop Acquisition")
        self._button_stop_acquisition.clicked.connect(self._stop_acquisition)
        self._button_stop_acquisition.setEnabled(False)
        self._button_software_trigger.setEnabled(False)

        #Gain:
        gain_widget = QtWidgets.QWidget(self.centralWidget())

        self._gain_label = QtWidgets.QLabel(gain_widget)
        self._gain_label.setMaximumWidth(30)
        self._gain_label.setText("<b>Gain: </b>")

        self._gain_slider = QtWidgets.QSlider()
        self._gain_slider.setMaximum(1000)
        self._gain_slider.setMinimum(100)
        self._gain_slider.setSingleStep(1)
        self._gain_slider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self._gain_slider.valueChanged.connect(self._update_gain)

        self._spinbox_gain = QtWidgets.QDoubleSpinBox()


        #Adding Widgets
        button_bar = QtWidgets.QWidget(self.centralWidget())
        button_bar_layout = QtWidgets.QGridLayout()
        button_bar_layout.addWidget(self._button_start_acquisition, 0, 0, 1, 2)
        button_bar_layout.addWidget(self._button_stop_acquisition, 0, 2, 1, 2)
        button_bar_layout.addWidget(self._button_software_trigger, 1, 0, 1, 2)
        button_bar_layout.addWidget(self._dropdown_pixel_format, 1, 2, 1, 1)
        button_bar_layout.addWidget(self._checkbox_save, 1, 3, 1, 1)

        button_bar_layout.addWidget(self._gain_label, 6, 0)
        button_bar_layout.addWidget(self._gain_slider, 6, 2, 1, 2)
        button_bar_layout.addWidget(self._spinbox_gain, 6, 1, 1, 1)
        button_bar_layout.addWidget(self.fps_label, 7, 0, 1, 4)  # Add FPS label to the layout



        button_bar.setLayout(button_bar_layout)
        self._layout.addWidget(button_bar)
        
        self._spinbox_gain.valueChanged.connect(self.change_slider_gain)


    def _create_statusbar(self):
        status_bar = QtWidgets.QWidget(self.centralWidget())
        status_bar_layout = QtWidgets.QHBoxLayout()
        status_bar_layout.setContentsMargins(0, 0, 0, 0)
        status_bar_layout.addStretch()

        self._label_version = QtWidgets.QLabel(status_bar)
        self._label_version.setText("Version:")
        self._label_version.setAlignment(Qt.AlignRight)
        status_bar_layout.addWidget(self._label_version)

        self._label_aboutqt = QtWidgets.QLabel(status_bar)
        self._label_aboutqt.setObjectName("aboutQt")
        self._label_aboutqt.setText("<a href='#aboutQt'>About Qt</a>")
        self._label_aboutqt.setAlignment(Qt.AlignRight)
        self._label_aboutqt.linkActivated.connect(
            self.on_aboutqt_link_activated)
        status_bar_layout.addWidget(self._label_aboutqt)
        status_bar.setLayout(status_bar_layout)

        self._layout.addWidget(status_bar)

    def _close(self):
        self._camera.killed = True
        self.acquisition_thread.join()


    def start_window(self):
        self.display = Display()
        self._layout.addWidget(self.display)
        self._create_button_bar()
        self._create_statusbar()
    
    def start_interface(self):
        self._gain_slider.setMaximum(int(self._camera.max_gain * 100))
        self._spinbox_gain.setMaximum(self._camera.max_gain)
        self._spinbox_gain.setMinimum(1.0)
        
        QtCore.QCoreApplication.setApplicationName(
            "Real Time + Hardware Trigger")
        self.show()
        self._qt_instance.exec()
        

    def _trigger_sw_trigger(self):
        #Gain Implementation
        gain_input = float(self._gain_slider.value())
        gain_input = gain_input / 100
        self._camera.target_gain = gain_input

        self._camera.make_image = True
        if self._checkbox_save.isChecked():
            self._camera.keep_image = True
        else:
            self._camera.keep_image = False

    def _start_acquisition(self):
        self._camera.start_acquisition()
        self._button_start_acquisition.setEnabled(False)
        self._dropdown_pixel_format.setEnabled(False)
        self._button_software_trigger.setEnabled(True)
        self._button_stop_acquisition.setEnabled(True)

    def _stop_acquisition(self):
        self._camera.stop_acquisition()
        self._button_start_acquisition.setEnabled(True)
        self._dropdown_pixel_format.setEnabled(True)
        self._button_software_trigger.setEnabled(False)
        self._button_stop_acquisition.setEnabled(False)

    def change_pixel_format(self):
        pixel_format = self._dropdown_pixel_format.currentText()
        self._camera.change_pixel_format(pixel_format)

    def on_image_received(self, image):
        """
        Processes the received image for the video stream.

        :param image: takes an image for the video preview seen onscreen
        """
        # Calculate FPS
        current_time = time()
        frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

        fps = round(1 / frame_time) if frame_time > 0 else 0  # Round FPS to nearest integer

        # Update the FPS label
        self.fps_label.setText(f"GUI FPS: {fps}")  # Display FPS as an integer

        # Process and display the image
        image_numpy = image.get_numpy_1D().copy()
        qt_image = QtGui.QImage(
            image_numpy,
            image.Width(),
            image.Height(),
            QtGui.QImage.Format_RGB32
        )
        self.display.on_image_received(qt_image)
        self.display.update()


    def warning(self, message: str):
        self.messagebox_signal.emit("Warning", message)

    def information(self, message: str):
        self.messagebox_signal.emit("Information", message)

    #Slot SW Trigger
    @Slot(str)
    def on_aboutqt_link_activated(self, link: str):
        if link == "#aboutQt":
            QtWidgets.QMessageBox.aboutQt(self, "About Qt")

    @Slot(str, str)
    def message(self, typ: str, message: str):
        if typ == "Warning":
            QtWidgets.QMessageBox.warning(
                self, "Warning", message, QtWidgets.QMessageBox.Ok)
        else:
            QtWidgets.QMessageBox.information(
                self, "Information", message, QtWidgets.QMessageBox.Ok)

    #Slot Gain
    @Slot(float)
    def change_slider_gain(self, val):
        self._gain_slider.setValue(int(val * 100))

    @Slot(int)
    def _update_gain(self, val):
        self._spinbox_gain.setValue(val / 100)
        self._camera.target_gain = val / 100
        self._camera.set_remote_device_value("Gain", val / 100)