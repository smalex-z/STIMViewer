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
import numpy as np

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

        self.set_camera(cam_module)

        self.gui_init()
        self._qt_instance = qt_instance
        self._qt_instance.aboutToQuit.connect(self._close)

        self.setMinimumSize(700, 650)

    def gui_init(self):
        self.widget = QtWidgets.QWidget(self)
        self._layout = QtWidgets.QVBoxLayout()
        self.widget.setLayout(self._layout)
        self.setCentralWidget(self.widget)
        self.display = None
        self.acquisition_thread = None

        # Buttons
        self._button_start = None
        self._button_exit = None
        self._button_software_trigger = None
        self._button_start_hardware_acquisition = None
        self._button_stop_hardware_acquisition = None
        self._button_exit = None
        self._dropdown_pixel_format = None

        self.messagebox_signal[str, str].connect(self.message)

        self._GUIfps_label = None
        self._frame_count = 0
        self._error_cont = 0
        self._gain_label = None


        self._gain_slider = None

    # Common interface start
    def is_gui(self):
        return True
    
    def set_camera(self, cam_module):
        self._camera = cam_module
    
    #GUI Creation
    def _create_button_bar(self):
        """Create the button bar with all necessary controls and widgets."""
        # Initialize button bar widget and layout
        button_bar = QtWidgets.QWidget(self.centralWidget())
        button_bar_layout = QtWidgets.QGridLayout()

        # Pixel Format Dropdown
        self._dropdown_pixel_format = QtWidgets.QComboBox()
        formats = self._camera.node_map.FindNode("PixelFormat").Entries()
        for idx in formats:
            if (idx.AccessStatus() not in [ids_peak.NodeAccessStatus_NotAvailable, ids_peak.NodeAccessStatus_NotImplemented]
                    and self._camera.conversion_supported(idx.Value())):
                self._dropdown_pixel_format.addItem(idx.SymbolicValue())
        self._dropdown_pixel_format.currentIndexChanged.connect(self.change_pixel_format)

        # Snapshot Button
        self._button_software_trigger = QtWidgets.QPushButton("Snapshot")
        self._button_software_trigger.clicked.connect(self._trigger_sw_trigger)

        # Acquisition Buttons
        self._button_start_hardware_acquisition = QtWidgets.QPushButton("Start Hardware Acquisition")
        self._button_start_hardware_acquisition.clicked.connect(self._start_hardware_acquisition)

        self._button_stop_hardware_acquisition = QtWidgets.QPushButton("Stop Hardware Acquisition")
        self._button_stop_hardware_acquisition.clicked.connect(self._stop_hardware_acquisition)
        self._button_stop_hardware_acquisition.setEnabled(False)

        # Recording Buttons
        self._button_start_recording = QtWidgets.QPushButton("Start Recording")
        self._button_start_recording.clicked.connect(self._start_recording)

        self._button_stop_recording = QtWidgets.QPushButton("Stop Recording")
        self._button_stop_recording.clicked.connect(self._stop_recording)
        self._button_stop_recording.setEnabled(False)

        # Gain Controls
        self._gain_label = QtWidgets.QLabel("<b>Gain:</b>")
        self._gain_label.setMaximumWidth(70)

        self._gain_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical)
        self._gain_slider.setRange(100, 1000)
        self._gain_slider.setSingleStep(1)
        self._gain_slider.valueChanged.connect(self._update_gain)

        self._spinbox_gain = QtWidgets.QDoubleSpinBox()
        self._spinbox_gain.valueChanged.connect(self.change_slider_gain)

        # Digital Gain Controls
        self._dgain_label = QtWidgets.QLabel("<b>D-Gain:</b>")
        self._dgain_label.setMaximumWidth(70)

        self._dgain_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical)
        self._dgain_slider.setRange(100, 1000)
        self._dgain_slider.setSingleStep(1)
        self._dgain_slider.valueChanged.connect(self._update_dgain)

        self._spinbox_dgain = QtWidgets.QDoubleSpinBox()
        self._spinbox_dgain.valueChanged.connect(self.change_slider_dgain)

        # Button Zoom In
        self._zoom_label = QtWidgets.QLabel("<b>Zoom:</b>")
        self._zoom_label.setMaximumWidth(70)

        self._zoom_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical)
        self._zoom_slider.setRange(100, 1000)
        self._zoom_slider.setSingleStep(1)
        self._zoom_slider.valueChanged.connect(self._update_zoom)

        self._spinbox_zoom = QtWidgets.QDoubleSpinBox()
        self._spinbox_zoom.valueChanged.connect(self.change_slider_zoom)

        # Add Widgets to Layout
        button_bar_layout.addWidget(self._button_start_hardware_acquisition, 0, 0, 1, 2)
        button_bar_layout.addWidget(self._button_stop_hardware_acquisition, 0, 2, 1, 2)
        button_bar_layout.addWidget(self._button_start_recording, 1, 0, 1, 2)
        button_bar_layout.addWidget(self._button_stop_recording, 1, 2, 1, 2)
        button_bar_layout.addWidget(self._button_software_trigger, 2, 0, 1, 2)
        button_bar_layout.addWidget(self._dropdown_pixel_format, 2, 2, 1, 2)

        # Move gain controls to the right column
        button_bar_layout.addWidget(self._gain_label, 0, 4)
        button_bar_layout.addWidget(self._spinbox_gain, 6, 4)
        button_bar_layout.addWidget(self._gain_slider, 1, 4, 5, 1, Qt.AlignHCenter)

        button_bar_layout.addWidget(self._dgain_label, 0, 5)
        button_bar_layout.addWidget(self._spinbox_dgain, 6, 5)
        button_bar_layout.addWidget(self._dgain_slider, 1, 5, 5, 1, Qt.AlignHCenter)

        button_bar_layout.addWidget(self._zoom_label, 0, 6)
        button_bar_layout.addWidget(self._spinbox_zoom, 6, 6)
        button_bar_layout.addWidget(self._zoom_slider, 1, 6, 5, 1, Qt.AlignHCenter)

        # ToolTips:
        # Buttons
        self._button_start_hardware_acquisition.setToolTip("Start acquiring images using hardware triggering rather than real time(RT) acquisition. Hardware Trigger FPS must stay <45 hz")
        self._button_stop_hardware_acquisition.setToolTip("Stop hardware-triggered image acquisition, return to real time (RT) acquisition")
        self._button_start_recording.setToolTip("Start recording video of the live feed.")
        self._button_stop_recording.setToolTip("Stop recording video and save the file.")
        self._button_software_trigger.setToolTip("Save the next processed frame.")

        # Slider Lables
        self._gain_label.setToolTip("Adjust the analog gain level (brightness).")
        self._dgain_label.setToolTip("Adjust the digital gain level.")
        self._zoom_label.setToolTip("Zoom in and out of the displayed image.")

        # Set Layout and Add to Main Layout
        button_bar.setLayout(button_bar_layout)
        self._layout.addWidget(button_bar)

    def _create_statusbar(self):
        status_bar = QtWidgets.QWidget(self.centralWidget())
        status_bar_layout = QtWidgets.QHBoxLayout()
        status_bar_layout.setContentsMargins(0, 0, 0, 0)
        status_bar_layout.addStretch()

        #FPS Label
        self.GUIfps_label = QLabel("GUI FPS: 0.00", self)
        self.GUIfps_label.setStyleSheet("font-size: 14px; color: green;")
        self.GUIfps_label.setAlignment(Qt.AlignRight)
        self.GUIfps_label.setToolTip("Calculated FPS over a rolling average of 2 seconds. If set to hardware trigger mode, camera only supports <45 fps.")

        status_bar_layout.addWidget(self.GUIfps_label)
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
        self._spinbox_dgain.setMinimum(1.0)
        self._spinbox_zoom.setMinimum(1.0)
        
        QtCore.QCoreApplication.setApplicationName(
            "STIMViewer")
        self.show()
        self._qt_instance.exec()
        

    def _trigger_sw_trigger(self):
        self._camera.save_image = True

    def _start_hardware_acquisition(self):
        self._camera.stop_realtime_acquisition()
        self._camera.start_hardware_acquisition()
        self._button_start_hardware_acquisition.setEnabled(False)
        self._dropdown_pixel_format.setEnabled(False)
        self._button_stop_hardware_acquisition.setEnabled(True)

    def _stop_hardware_acquisition(self):
        self._camera.stop_hardware_acquisition()
        self._camera.start_realtime_acquisition()
        self._button_start_hardware_acquisition.setEnabled(True)
        self._dropdown_pixel_format.setEnabled(True)
        self._button_stop_hardware_acquisition.setEnabled(False)

    def _start_recording(self):
        self._camera.start_recording()
        self._button_start_recording.setEnabled(False)
        self._button_stop_recording.setEnabled(True)
        self._button_start_hardware_acquisition.setEnabled(False)
        self._button_stop_hardware_acquisition.setEnabled(False)


    def _stop_recording(self):
        self._camera.stop_recording()
        self._button_stop_recording.setEnabled(False)
        if self._camera.acquisition_mode == 1: #HW Trigger
            self._button_stop_hardware_acquisition.setEnabled(True)
        else:
            self._button_start_hardware_acquisition.setEnabled(True)


    def change_pixel_format(self):
        pixel_format = self._dropdown_pixel_format.currentText()
        self._camera.change_pixel_format(pixel_format)

    def on_image_received(self, image):
        """
        Processes the received image for the video stream.

        :param image: takes an image for the video preview seen onscreen
        """
        # Calculate FPS
        GUIfps = self._camera.get_actual_fps()

        # Update the FPS label
        QtCore.QMetaObject.invokeMethod(self.GUIfps_label, "setText",
                                    QtCore.Qt.QueuedConnection,
                                    QtCore.Q_ARG(str, f"GUI FPS: {GUIfps}"))

        # Process and display the image
        image_numpy = image.get_numpy_1D().copy()
        qt_image = QtGui.QImage(
            image_numpy,
            image.Width(),
            image.Height(),
            QtGui.QImage.Format_RGB32
        )
             
        try:
            self.display.on_image_received(qt_image)
        except Exception as e:
            print(f"Error updating Display, {e}")
        


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
        self._camera.node_map.FindNode("GainSelector").SetCurrentEntry("AnalogAll")
        self._camera.set_remote_device_value("Gain", val / 100)

    #Slot Gain
    @Slot(float)
    def change_slider_dgain(self, val):
        self._dgain_slider.setValue(int(val * 100))

    @Slot(int)
    def _update_dgain(self, val):
        self._spinbox_dgain.setValue(val / 100)
        self._camera.target_dgain = val / 100
        self._camera.node_map.FindNode("GainSelector").SetCurrentEntry("DigitalAll")
        self._camera.set_remote_device_value("Gain", val / 100)
    
    @Slot(float)
    def change_slider_zoom(self, val):
        self._zoom_slider.setValue(int(val * 100))

    @Slot(int)
    def _update_zoom(self, val):
        self._spinbox_zoom.setValue(val / 100)
        self.display.set_zoom(val / 100)

