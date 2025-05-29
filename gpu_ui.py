
import os
import os

from PyQt5.QtWidgets import (
    QGridLayout, QPushButton, QWidget, QTextEdit,
    QVBoxLayout, QFileDialog
)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import pyqtSignal
import threading
import os

import pyqtgraph as pg
from live_trace_extractor import LiveTraceExtractor
from make_mmap import make_memmap
from otsu_thresh import compute_mean_projection, denoise_and_threshold_gpu
from roi_thresh import threshold_patch
from roi_editor import refine_rois   
from trace_extr import extract_traces
from trace_view import view_traces
import numpy as np
from otsu_thresh import load_movie, compute_mean_projection, denoise_and_threshold_gpu
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Q_ARG
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtCore import Qt, QMetaObject
from PyQt5 import QtCore
from camera import Camera

class GPU(QWidget):
    newLogpyqtSignal = pyqtSignal(str)
    closed       = pyqtSignal()
    instance     = None
    log_buffer   = []
    export_count = 0
    refineRequested = pyqtSignal(object, object)
    requestStartLiveTraces = pyqtSignal()
    requestStartRecording   = pyqtSignal()

    def __init__(self, camera: Camera, logger=None, log_widget=None):
        super().__init__()
        if camera is None:
            raise ValueError("GPU needs a Camera instance")
        self.camera = camera
        GPU.instance = self
        #self.camera = camera 
        self.setWindowTitle("GPU Pipeline")
        self.resize(700, 500)
        self.requestStartLiveTraces.connect(self.start_live_traces, QtCore.Qt.QueuedConnection)
        self.requestStartRecording.connect(self.camera.start_recording, QtCore.Qt.QueuedConnection)
        # layout & log widget
        self.layout = QVBoxLayout(self)
        self.log_widget = log_widget or QTextEdit()
        self.log_widget.setReadOnly(True)
        self.layout.addWidget(self.log_widget)
        self.newLogpyqtSignal.connect(self.write_log_pyqtSlot)
        self.paused = False
        # pipeline state
        self.video_path   = None
        self.proj_display = None
        self.memmap_path  = "movie_mmap.npy"
        self.rois_path    = "rois.npz"
        self.curated_path = "rois_current.npz"
        self.trace_path   = "traces_live.npy"
        self.trace_plot = pg.PlotWidget(title="Live ROI Traces")
        self.layout.addWidget(self.trace_plot)
        self.refineRequested.connect(self._launch_napari_viewer)

        # Add a “Start Live Traces” button
        btn = QPushButton("▶ Restart Live Traces")
        btn.clicked.connect(self.start_live_traces)
        self.layout.addWidget(btn)

    

        # storage for our extractor
        self.live_extractor = None
        # add pause/export controls
        self.log_init()

        # add our pipeline‐button row
        self.init_pipeline_buttons()

        # flush any early logs
        for msg in GPU.log_buffer:
            self.newLogpyqtSignal.emit(msg)
        GPU.log_buffer.clear()

    def init_pipeline_buttons(self):
        """Create buttons for each GPU‐pipeline step."""
        grid = QGridLayout()
        row = 0

        # 1) Select source video
        btn = QPushButton("🖼 Select Video…")
        btn.clicked.connect(self.select_video)
        grid.addWidget(btn, row, 0)

        # 2) Convert → memmap
        btn = QPushButton("➤ Make Memmap")
        btn.clicked.connect(self.run_make_memmap)
        grid.addWidget(btn, row, 1)

        # 3) Detect ROIs
        btn = QPushButton("➤ Discover ROIs")
        btn.clicked.connect(self.run_discover_rois)
        grid.addWidget(btn, row, 2)

        # 4) Refine curated ROIs
        btn = QPushButton("➤ Refine ROIs")
        btn.clicked.connect(self.run_refine_rois)
        grid.addWidget(btn, row, 3)

        # 5) Extract traces
        # btn = QPushButton("➤ Extract Traces")
        # btn.clicked.connect(self.run_extract_traces)
        # grid.addWidget(btn, row, 4)

        # 6) View traces
        btn = QPushButton("▶ Export/View Traces")
        btn.clicked.connect(self.run_view_traces)
        grid.addWidget(btn, row, 5)

        self.layout.addLayout(grid)

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select video file", "", "Video files (*.avi *.mp4 *.h5 *.npy *.npz)"
        )
        if path:
            self.video_path = path
            GPU.log_INFO(f"Selected video: {path}")

    # Generic pattern: spawn a thread, log start, run, log finish
    def run_make_memmap(self):
        threading.Thread(target=self._thread_make_memmap, daemon=True).start()

    def _thread_make_memmap(self):
        GPU.log_NOTI("Making memmap…")
        try:
            make_memmap(self.video_path, self.memmap_path)
            GPU.log_INFO(f"Memmap saved to {self.memmap_path}")
        except Exception as e:
            GPU.log_ERRO(f"Memmap failed: {e}")

    def run_discover_rois(self):
        threading.Thread(target=self._thread_discover_rois, daemon=True).start()

    # def _thread_discover_rois(self):
    #     GPU.log_NOTI("Discovering ROIs…")
    #     try:
    #         # reuse your main.py logic but via a function
    #         movie = np.load(self.memmap_path, mmap_mode='r')
    #         self.discovered = compute_mean_projection(movie, calib_frames=5400, chunk_size=200)

    #         label = masks, sizes = denoise_and_threshold_gpu(
    #             self.discovered, gauss_ksize=(3,3), gauss_sigma=1.5,
    #             min_area=60, max_area=300
    #         )
    #         # save as rois.npz
    #         np.savez_compressed(self.rois_path, masks=masks, sizes=sizes)
    #         GPU.log_INFO(f"ROIs written to {self.rois_path}")
    #         # from projection import ProjectDisplay
    #         # import cv2
    #         # from skimage.color import label2rgb
    #         # rgb_image = label2rgb(label, bg_label=0).astype(np.uint8)
    #         # rgb_image = (rgb_image * 255).astype(np.uint8)
    #         # ProjectDisplay.show_image_fullscreen_on_second_monitor(
    #         #         rgb_image, homography_matrix=None
    #         # )
    #     except Exception as e:
    #         GPU.log_ERRO(f"ROI discovery failed: {e}")

    def _thread_discover_rois(self):
        GPU.log_NOTI("Discovering ROIs…")
        try:
            # Load memmap video
            movie = np.load(self.memmap_path, mmap_mode='r')
            self.discovered = compute_mean_projection(movie, calib_frames=5400, chunk_size=200)

            # Threshold and denoise to get masks
            masks, sizes = denoise_and_threshold_gpu(
                self.discovered, gauss_ksize=(3,3), gauss_sigma=1.5,
                min_area=60, max_area=300
            )
            labeled_image = np.zeros_like(masks[0], dtype=np.int32)
            for i, mask in enumerate(masks, start=1):
                labeled_image[mask] = i
            # Save original discovered ROIs
            #np.savez_compressed(self.rois_path, masks=masks, sizes=sizes)
            #GPU.log_INFO(f"ROIs written to {self.rois_path}")

            # ==== 👇 Project thresholded masks on STIMViewer ====
            from skimage.color import label2rgb
            from projection import ProjectDisplay
            from PyQt5.QtGui import QGuiApplication
            import cv2
            rgb_image = (label2rgb(labeled_image, bg_label=0) * 255).astype(np.uint8)
            screen = QGuiApplication.screens()[1]  # or [0] if only one
            size = screen.size()
            h, w = size.height(), size.width()
            rgb_image = cv2.resize(rgb_image, (w, h), interpolation=cv2.INTER_NEAREST)
            screens = QGuiApplication.screens()
            screen = screens[1] if len(screens) > 1 else screens[0]
            self.proj_display = ProjectDisplay(screen)
            self.proj_display.show_image_fullscreen_on_second_monitor(rgb_image, homography_matrix=None)
            np.savez_compressed(self.rois_path, masks=masks, sizes=sizes, labels=labeled_image)
            GPU.log_INFO(f"ROIs written to {self.rois_path}")
            # ==== 👇 Start Live Traces automatically ====
            self.requestStartLiveTraces.emit()
            # self.start_live_traces()
            # QtCore.QMetaObject.invokeMethod(self, "start_live_traces", QtCore.Qt.QueuedConnection)

            # ==== 👇 Start recording automatically ====
            # if not getattr(self.camera, "is_recording", False):
            #     self.camera.start_recording()
            #     GPU.log_INFO("Recording started after ROI discovery.")
            self.requestStartRecording.emit()
                # QtCore.QMetaObject.invokeMethod(self.camera, "start_recording", QtCore.Qt.QueuedConnection)
            GPU.log_INFO("Recording requested after ROI discovery.")

        except Exception as e:
            GPU.log_ERRO(f"ROI discovery failed: {e}")


    def run_refine_rois(self):
        threading.Thread(target=self._thread_refine_rois, daemon=True).start()
    # def start_live_traces(self):
    #     if self.live_extractor is None:
    #         if not os.path.exists(self.curated_path):
    #             GPU.log_ERRO("No curated ROIs; run Refine ROIs first.")
    #             return
    #         self.live_extractor = LiveTraceExtractor(
    #             camera=self.camera,
    #             label_path=self.curated_path,
    #             plot_widget=self.trace_plot,
    #             max_points=300
    #         )
    #         GPU.log_INFO("Live trace extraction started.")
    #     else:
    #         GPU.log_NOTI("Live trace extractor already running.")
    def start_live_traces(self):
        if self.live_extractor is None:
            # Try curated labels first; fall back to discovered ROIs
            roi_path =  self.rois_path

            if not os.path.exists(roi_path):
                GPU.log_ERRO("No ROI file found. Run Discover or Refine ROIs first.")
                return

            try:
                self.live_extractor = LiveTraceExtractor(
                    camera=self.camera,
                    label_path=roi_path,
                    plot_widget=self.trace_plot,
                    max_points=300
                )
                GPU.log_INFO(f"Live trace extraction started using {os.path.basename(roi_path)}.")
            except Exception as e:
                GPU.log_ERRO(f"Failed to start live traces: {e}")
        else:
            GPU.log_NOTI("Live trace extractor already running.")

    def _thread_refine_rois(self):
        GPU.log_NOTI("Refining ROIs in GUI…")
        try:
            # load the mean, masks, run your roi_editor logic in headless mode
            from otsu_thresh import load_movie, compute_mean_projection
            mean = compute_mean_projection(load_movie(self.video_path), calib_frames=5400)
            masks = np.load(self.rois_path)["masks"]
            #refined_labels = refine_rois(mean, masks)
            # QtCore.QMetaObject.invokeMethod(
            #     self,
            #     "_launch_napari_viewer",
            #     QtCore.Qt.QueuedConnection,
            #     QtCore.Q_ARG(object, mean),
            #     QtCore.Q_ARG(object, masks),
            # )
            self.refineRequested.emit(mean, masks)
            GPU.log_INFO("Live traces requested after ROI refinement.")
            if not self.camera.is_recording:
                self.requestStartRecording.emit()
                GPU.log_INFO("Recording requested after ROI refinement.")
            
            # np.savez_compressed(self.curated_path, labels=refined_labels)
            # GPU.log_INFO(f"Refined labels saved to {self.curated_path}")
        except Exception as e:
            GPU.log_ERRO(f"ROI refinement failed: {e}")
    
    @pyqtSlot(object, object)
    def _launch_napari_viewer(self, mean, masks):
        """
        This runs on the main (GUI) thread, so Qt is fully available.
        We call your refine_rois() helper here.
        """
        from roi_editor import refine_rois

        # This call will now succeed with a proper Qt event loop
        label_map = refine_rois(mean, masks)

        from projection       import ProjectDisplay
        from PyQt5.QtGui      import QGuiApplication
        from skimage.color    import label2rgb
        rgb_image = (label2rgb(label_map, bg_label=0) * 255).astype(np.uint8)
        screens = QGuiApplication.screens()
        screen  = screens[1] if len(screens) > 1 else screens[0]
        proj    = ProjectDisplay(screen)
        proj.show_image_fullscreen_on_second_monitor(rgb_image, homography_matrix=None)


        # Optionally save out the new labels right here
        # np.savez_compressed(self.curated_path, labels=label_map)
        # GPU.log_INFO(f"Refined labels saved to {self.curated_path}")

    def run_extract_traces(self):
        threading.Thread(target=self._thread_extract_traces, daemon=True).start()

    def _thread_extract_traces(self):
        GPU.log_NOTI("Extracting traces…")
        try:
            extract_traces(
                self.memmap_path, self.rois_path, self.trace_path
            )
            GPU.log_INFO(f"Traces saved to {self.trace_path}")
        except Exception as e:
            GPU.log_ERRO(f"Trace extraction failed: {e}")

    def run_view_traces(self):
        # # no need thread—instant
        # # try:
        # #     view_traces(self.trace_path)
        # # except Exception as e:
        # #     GPU.log_ERRO(f"Trace view failed: {e}")
        # try:
        #     save_path, _ = QFileDialog.getSaveFileName(
        #         self, "Export traces to CSV", "", "CSV Files (*.csv)")
        #     if save_path:
        #         data = np.load(self.trace_path)   # assume shape (T, N_rois)
        #         # build a header of ROI names
        #         num_rois = data.shape[1] if data.ndim > 1 else 1
        #         header = ",".join(f"ROI{i+1}" for i in range(num_rois))
        #         np.savetxt(save_path, data, delimiter=",",
        #                    header=header, comments="")
        #         GPU.log_INFO(f"Traces exported to {save_path}")
        # except Exception as e:
        #     GPU.log_ERRO(f"Failed to export traces: {e}")

        try:
            # show only the last 50 frames of live traces
            view_traces(self.trace_path, rois_path=self.curated_path if os.path.exists(self.curated_path) else self.rois_path, last_n=5)
        except Exception as e:
            GPU.log_ERRO(f"Trace view failed: {e}")


    def closeEvent(self, event):
        # Override close event: hide instead of closing.
        event.ignore()
        self.hide()
        self.closed.emit()

    def log_init(self):
        self.pause_resume_button = QPushButton("Pause Logging")
        self.pause_resume_button.setCheckable(True)
        self.pause_resume_button.clicked.connect(self.pause_resume_logging)


        self.export = QPushButton("Export Logbook")
        self.export.clicked.connect(self.export_logbook_to_file)

        grid = QGridLayout()
        grid.addWidget(self.pause_resume_button, 2, 0, 2, 1)
        grid.addWidget(self.export, 2, 2, 2, 1)

        self.layout.addStretch()
        self.layout.addLayout(grid)

    def pause_resume_logging(self):
        if self.pause_resume_button.isChecked():
            self.paused = True
            self.pause_resume_button.setText("Resume Logging")
        else:
            self.paused = False
            self.pause_resume_button.setText("Pause Logging")


    def write_log_pyqtSlot(self, log):
        """
        Write the log to the log widget.
        Uses HTML formatting so that colored messages are rendered properly.
        """
        if not self.paused:
            self.log_widget.insertHtml(log)
            self.log_widget.moveCursor(QTextCursor.End)

    def write_log(self, log):
        self.newLogpyqtSignal.emit(log)


    @classmethod
    def _log_generic(cls, level, message):
        """
        Generic logging method using HTML formatting for colored log levels.
        Levels: EMER, ALRT, CRIT, ERRO, WARN, NOTI, INFO, DBUG.
        """
        level_config = {
            "EMER": ("EMERGENCY:", "red"),
            "ALRT": ("ALERT:", "orange"),
            "CRIT": ("CRITICAL:", "darkred"),
            "ERRO": ("ERROR:", "red"),
            "WARN": ("WARNING:", "goldenrod"),
            "NOTI": ("NOTIFICATION:", "blue"),
            "INFO": ("INFORMATIONAL:", "black"),
            "DBUG": ("DEBUG:", "gray"),
        }
        prefix, color = level_config.get(level, ("", "black"))
        # Build an HTML-formatted log message.
        html = f"<span style='color: {color};'><b>{prefix}</b></span> {message}<br>"
        if cls.instance:
            cls.instance.write_log(html)
    

    # Convenience methods for each log level:
    @classmethod
    def log_EMER(cls, message):
        cls._log_generic("EMER", message)

    @classmethod
    def log_ALRT(cls, message):
        cls._log_generic("ALRT", message)

    @classmethod
    def log_CRIT(cls, message):
        cls._log_generic("CRIT", message)

    @classmethod
    def log_ERRO(cls, message):
        cls._log_generic("ERRO", message)

    @classmethod
    def log_WARN(cls, message):
        cls._log_generic("WARN", message)

    @classmethod
    def log_NOTI(cls, message):
        cls._log_generic("NOTI", message)

    @classmethod
    def log_INFO(cls, message):
        cls._log_generic("INFO", message)

    @classmethod
    def log_DBUG(cls, message):
        cls._log_generic("DBUG", message)

    def export_logbook_to_file(self):
        """
        Export the log to a file.
        Each export is appended to the file with an export header and separator.
        """
        GPU.export_count += 1
        # Get all logs from the widget as plain text.
        log_text = self.log_widget.toPlainText()
        lines = log_text.splitlines()
        file_path = "export_log.txt"
        try:
            with open(file_path, "a") as f:
                f.write(f"Export: {GPU.export_count}\n")
                f.write("\n".join(lines))
                f.write("\n" + ("-" * 40) + "\n")
            self.write_log(f"<br><i>Log exported successfully to {file_path}</i><br>")
        except Exception as e:
            self.write_log(f"<br><i>Error exporting log: {str(e)}</i><br>")
        print("Logbook exported to file")

