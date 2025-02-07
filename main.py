# \file    main.py
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

import threading

from ids_peak import ids_peak

import camera

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from cli_interface import CLIInterface
    from qt_interface import QtInterface
    Interface = Union[CLIInterface, QtInterface]


def start(camera_device: camera.Camera, ui: 'Interface'):
    if not camera_device.start_realtime_acquisition():
        print("Failed to start acquisition!")
        return

    ui.start_window()
    thread = threading.Thread(target=camera_device.acquisition_thread, args=())
    thread.start()
    ui.acquisition_thread = thread
    ui.start_interface()


def main(ui: 'Interface'):
    # Initialize library and create a device manager
    ids_peak.Library.Initialize()
    device_manager = ids_peak.DeviceManager.Instance()
    camera_device = None
    try:
        camera_device = camera.Camera(device_manager, ui)
        start(camera_device, ui)
    
    except KeyboardInterrupt:
        print("User interrupt: Exiting...")
    except Exception as e:
        print(f"Exception (main): {str(e)}")
    finally:
        # Close camera and library after program ends
        if camera_device is not None:
            camera_device.close()
        ids_peak.Library.Close()


if __name__ == '__main__':
    from qt_interface import Interface
    main(Interface())
