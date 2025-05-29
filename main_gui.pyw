
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
# os.environ['QT_QPA_PLATFORM'] = 'egl'

from PyQt5.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts) 
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
# import os
from vispy import use                             # 
use()
# vispy.use(gl='gl2')
# os.environ['QT_QPA_PLATFORM'] = 'eglfs'

# vispy.use('egl')
# from vispy import app as vispy_app           # 
#vispy_app.use_app('pyqt5')
#os.environ["QT_API"] = "PyQt5"
from main import main
from kill_zombies import kill_other_instances
import sys

export_file = "export_log.txt"

if os.path.exists(export_file):
    # Clear the file at the beginning of the program
    open(export_file, "w").close()
    
# try:
from PyQt5.QtWidgets import QApplication    
# except ImportError:
#     from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    kill_other_instances()
    print("[DEBUG] main_gui.py: __main__ hit", flush=True)
    from qt_interface import Interface
    #main(Interface())
    app = QApplication(sys.argv)       
    window = Interface()                 
    window.show()
    sys.exit(app.exec_())
  