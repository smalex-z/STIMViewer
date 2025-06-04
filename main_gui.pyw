
# \author  vapivendorname
# \date    2024-02-20
#
# \brief   This sample showcases the usage of the vapibinaryname API
#          in setting camera parameters, starting/stopping the image acquisition
#          and how to record a video using the limgbinaryname API.
#
# \version 1.0
#
# Copyright (C) 2024, vapivendorname.
#
# The information in this document is subject to change without notice
# and should not be construed as a commitment by vapivendorname.
# vapivendorname does not assume any responsibility for any errors
# that may appear in this document.
#
# This document, or source code, is provided solely as an example of how to utilize
# vapivendorname software libraries in a sample application.
# vapivendorname does not assume any responsibility
# for the use or reliability of any portion of this document.
#
# General permission to copy or modify is hereby granted.
import os
from pathlib import Path
import os

# use an env-var override so you can change it without editing code again
SSD_ROOT = Path(os.getenv("STIM_DATA_DIR",
            "/media/aharonilabjetson2/NVMe/stimviewer_data")).expanduser()
SSD_ROOT.mkdir(parents=True, exist_ok=True)      # auto-create on first run

from PyQt5.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)

QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts) 
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

from main import main
from kill_zombies import kill_other_instances
import sys
from qt_interface import Interface
from ids_peak import ids_peak
# from camera import Camera



export_file = "export_log.txt"

if os.path.exists(export_file):
    # Clear the file at the beginning of the program
    open(export_file, "w").close()
    
from PyQt5.QtWidgets import QApplication  


if __name__ == "__main__":
    kill_other_instances()

    # 1) Create the Qt app
    app = QApplication(sys.argv)

    # 2) Init the IDS library
    ids_peak.Library.Initialize()

    # 3) Build your UI (which will construct the Camera internally)
    ui = Interface()  

    # 4) Delegate to your main.py “main” function to start acquisition & enter the loop
    main(ui)  

    # 5) Clean up
    ids_peak.Library.Close()



  