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
# main.py

# import threading
# from ids_peak import ids_peak
# from WhiteBackgroundGen import makeWhite
# from calibration import create_custom_registration_image
# from logbook import Logbook
# from camera import Camera

# def start(camera_device, ui):
#     if not camera_device.start_realtime_acquisition():
#         Logbook.log_ERRO("Failed to start acquisition!")
#         return

#     ui.start_window()
#     thread = threading.Thread(
#         target=camera_device.acquisition_thread,
#         daemon=True
#     )
#     thread.start()
#     ui.acquisition_thread = thread
#     ui.start_interface()

# def main(ui):
#     # 1) Initialize IDS-Peak
#     ids_peak.Library.Initialize()
#     Logbook.log_INFO("IDS-Peak library initialized.")

#     # 2) Generate projector assets
#     makeWhite(1936, 1096)
#     create_custom_registration_image()

#     # 3) Build device + UI
#     device_manager = ids_peak.DeviceManager.Instance()
#     camera_device = Camera(device_manager, interface=ui)

#     try:
#         start(camera_device, ui)
#     except KeyboardInterrupt:
#         Logbook.log_NOTI("User interrupt: Exiting…")
#     except Exception as e:
#         Logbook.log_ERRO(f"Exception in main: {e}")
#     finally:
#         camera_device.killed = True
#         if ui.acquisition_thread is not None:
#             ui.acquisition_thread.join()
#         camera_device.close()
#         ids_peak.Library.Close()

# if __name__ == "__main__":
#     from qt_interface import Interface
#     logbook = Logbook()        # pop up the logbook window
#     ui = Interface()           # your Qt-based GUI
#     main(ui)

import threading

from ids_peak import ids_peak
from WhiteBackgroundGen import makeWhite
from calibration import create_custom_registration_image
from logbook import Logbook
import camera

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from cli_interface import CLIInterface
    from qt_interface import QtInterface
    Interface = Union[CLIInterface, QtInterface]


# def start(camera_device: camera.Camera, ui: 'Interface'):
#     if not camera_device.start_realtime_acquisition():
#         Logbook.log("Failed to start acquisition!")
#         return

#     ui.start_window()
#     thread = threading.Thread(target=camera_device.acquisition_thread, args=())
#     thread.start()
#     ui.acquisition_thread = thread
#     ui.start_interface()

#     # Assets
#     makeWhite(1936, 1096) #resolution
#     create_custom_registration_image()
def start(camera_device: camera.Camera, ui: 'Interface'):
    print("[DEBUG] start() entry", flush=True)
    ok = camera_device.start_realtime_acquisition()
    print(f"[DEBUG] start_realtime_acquisition → {ok}", flush=True)

    if not ok:
        print("‼ [DEBUG] acquisition failed, continuing anyway for UI test", flush=True)
        # return   ← comment this out while debugging

    print("[DEBUG] about to ui.start_window()", flush=True)
    ui.start_window()
    print("[DEBUG] ui.start_window() done", flush=True)

    thread = threading.Thread(target=camera_device.acquisition_thread, daemon=True)
    thread.start()
    ui.acquisition_thread = thread

    print("[DEBUG] about to ui.start_interface()", flush=True)
    ui.start_interface()
    print("[DEBUG] ui.start_interface() returned", flush=True)



def main(ui: 'Interface'):
    print("[DEBUG] main() entry", flush=True)
    # Initialize library and create a device manager
    ids_peak.Library.Initialize()
    print("[DEBUG] IDS-Peak library initialized", flush=True)
    device_manager = ids_peak.DeviceManager.Instance()
    camera_device = None
    try:
        print("[DEBUG] about to create Camera", flush=True)
        camera_device = camera.Camera(device_manager, ui)
        print("[DEBUG] Camera created", flush=True)

        print("[DEBUG] calling start()", flush=True)
        start(camera_device, ui)
        print("[DEBUG] start() returned", flush=True)
    
    except KeyboardInterrupt:
        Logbook.log_NOTI("User interrupt: Exiting...")
    except Exception as e:
        Logbook.log_ERRO(f"Exception (main): {str(e)}")
    finally:
        # Close camera and library after program ends
        if camera_device is not None:
            camera_device.close()
        ids_peak.Library.Close()


if __name__ == '__main__':
    logbook = Logbook()
    from qt_interface import Interface
    main(Interface())
