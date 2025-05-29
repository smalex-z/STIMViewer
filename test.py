# # test.py
# from PyQt5.QtWidgets import QApplication, QWidget
# import sys
import os


# test_qt_opengl.py
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
import sys

class GLTest(QOpenGLWidget):
    def initializeGL(self):
        print("OpenGL context successfully created.")

app = QApplication(sys.argv)
win = GLTest()
win.show()
sys.exit(app.exec_())

