# # test.py
# from PyQt5.QtWidgets import QApplication, QWidget
# import sys
import os



# app = QApplication(sys.argv)
# widget = QWidget()
# widget.resize(640, 480)
# widget.show()
# sys.exit(app.exec())
# quick_test.py
# from PyQt5.QtWidgets import QApplication, QWidget
# import sys
# app = QApplication(sys.argv)
# w = QWidget(); w.show()
# sys.exit(app.exec())

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

