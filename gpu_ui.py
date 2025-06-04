from pathlib import Path
import os

# use an env-var override so you can change it without editing code again
SSD_ROOT = Path(os.getenv("STIM_DATA_DIR",
            "/media/aharonilabjetson2/NVMe/stimviewer_data")).expanduser()
SSD_ROOT.mkdir(parents=True, exist_ok=True)      # auto-create on first run

import os

from PyQt5.QtWidgets import (
    QGridLayout, QPushButton, QWidget, QTextEdit,
    QVBoxLayout, QFileDialog
)
from PyQt5.QtGui import QTextCursor
from PyQt5.QtCore import pyqtSignal
import threading
import time
import pyqtgraph as pg
from live_trace_extractor import LiveTraceExtractor
from live_trace_extractor import LiveTraceExtractorNapari

from make_mmap import make_memmap
from otsu_thresh import compute_mean_projection, denoise_and_threshold_gpu
import numpy as np
from otsu_thresh import  compute_mean_projection, denoise_and_threshold_gpu
from PyQt5.QtCore import pyqtSignal, pyqtSlot
import PyQt5.QtCore as QtCore
from PyQt5 import QtCore
from camera import Camera
import cv2

class GPU(QWidget):
    newLogpyqtSignal = pyqtSignal(str)
    closed       = pyqtSignal()
    instance     = None
    log_buffer   = []
    export_count = 0
    refineRequested = pyqtSignal(object, object)
    requestStartLiveTraces = pyqtSignal()
    requestStartRecording   = pyqtSignal()
    requestStartLiveTracesNapari = pyqtSignal()

    def __init__(self, camera: Camera, logger=None, log_widget=None):
        super().__init__()
        if camera is None:
            raise ValueError("GPU needs a Camera instance")
        self.camera = camera
        GPU.instance = self
        #self.camera = camera 
        self.setWindowTitle("CRISPI")
        self.resize(700, 500)
        self.requestStartLiveTraces.connect(self.start_live_traces, QtCore.Qt.QueuedConnection)
        self.requestStartLiveTraces.connect(self.start_live_traces_napari, QtCore.Qt.QueuedConnection)
        self.requestStartRecording.connect(self.camera.start_recording, QtCore.Qt.QueuedConnection)
        # self.camera.recordingStarted.connect(self.on_recording_started)
        # self.camera.recordingStopped.connect(self.on_recording_stopped)
        if hasattr(GPU.instance, "roiExported"):
            GPU.instance.roiExported.connect(self.on_roi_exported)
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
        # self.curated_path = "rois_current.npz"
        self.trace_path   = "traces_live.npy"
        # self.trace_plot = pg.PlotWidget(title="Live ROI Traces")
        # self.layout.addWidget(self.trace_plot)
        self.refineRequested.connect(self._launch_napari_viewer)

        # # Add a “Start Live Traces” button
        # btn = QPushButton("▶ Restart Live Traces")
        # btn.clicked.connect(self.start_live_traces)
        # self.layout.addWidget(btn)

    

        # storage for our extractor
        self.live_extractor = None
        self.live_extractor_napari = None
        # add pause/export controls
        self.log_init()

        # add our pipeline‐button row
        self.init_pipeline_buttons()

        # flush any early logs
        for msg in GPU.log_buffer:
            self.newLogpyqtSignal.emit(msg)
        GPU.log_buffer.clear()

    @pyqtSlot(object)
    def on_roi_exported(self, label_data):
        try:
            GPU.log_INFO("Received new ROIs from Napari export. Re-initializing live traces.")
            if self.live_extractor_napari:
                self.live_extractor_napari.stop()
                self.live_extractor_napari = None
            self.start_live_traces_napari()
        except Exception as e:
            GPU.log_ERRO(f"Failed to reinit live traces after export: {e}")


    # def stop_live_traces(self):
    #     """Safely stop the live trace extractor if it's running."""
    #     if self.live_extractor:
    #         try:
    #             self.live_extractor.stop()
    #             self.live_extractor = None
    #             GPU.log_INFO("Live trace extractor stopped.")
    #         except Exception as e:
    #             GPU.log_ERRO(f"Failed to stop live trace extractor: {e}")
    def stop_live_traces(self):
        """Safely stop the live trace extractor if it's running."""
        if self.live_extractor:
            try:
                if hasattr(self.live_extractor, "stop"):
                    self.live_extractor.stop()
                else:
                    GPU.log_WARN("live_extractor has no stop() method.")
            except Exception as e:
                GPU.log_ERRO(f"Failed to stop live trace extractor: {e}")
            finally:
                self.live_extractor = None

    def stop_live_traces_napari(self):
        """Safely stop the live trace extractor if it's running."""
        if self.live_extractor_napari:
            try:
                if hasattr(self.live_extractor_napari, "stop"):
                    self.live_extractor_napari.stop()
                else:
                    GPU.log_WARN("live_extractor has no stop() method.")
            except Exception as e:
                GPU.log_ERRO(f"Failed to stop live trace extractor: {e}")
            finally:
                self.live_extractor_napari = None


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

        from PyQt5.QtWidgets import QToolButton, QMenu, QAction

        # 3) Detect ROIs
        dd = QToolButton()
        dd.setText("➤ Discover Mask")
        dd.setPopupMode(QToolButton.InstantPopup)

        menu = QMenu(dd)

        for method in ("Suite2p", "CaImAn", "Custom", "OTSU"):
            act = QAction(method, dd)
            # When the user picks “Suite2p” (etc.), we call run_discover_rois(method)
            act.triggered.connect(lambda checked=False, m=method: self.run_discover_rois(m))
            menu.addAction(act)

        dd.setMenu(menu)
        grid.addWidget(dd, row, 2)

        # 4) Refine curated ROIs
        btn = QPushButton("➤ Manual Mask Editor")
        btn.clicked.connect(self.run_refine_rois)
        grid.addWidget(btn, row, 3)

        # 5) Extract traces
        # btn = QPushButton("➤ Extract Traces")
        # btn.clicked.connect(self.run_extract_traces)
        # grid.addWidget(btn, row, 4)

        # 6) View traces
        btn = QPushButton("▶ Export Traces")
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

    def run_discover_rois(self, method="OTSU"):
        self._discover_method = method
        threading.Thread(target=self._thread_discover_rois, daemon=True).start()

  

    def _thread_discover_rois(self):
        GPU.log_NOTI("Discovering ROIs…")
        self.stop_live_traces()

        try:

            if self._discover_method == "OTSU":
                # Load memmap video
                movie = np.load(self.memmap_path, mmap_mode='r')
                self.discovered = compute_mean_projection(movie, calib_frames=5400, chunk_size=200)
            

                self.discovered = cv2.resize(self.discovered, (1936, 1096), interpolation=cv2.INTER_NEAREST)

                # Threshold and denoise to get masks
                masks, sizes = denoise_and_threshold_gpu(
                    self.discovered, gauss_ksize=(3,3), gauss_sigma=1.5,
                    min_area=60, max_area=300
                )
            

                labeled_image = np.zeros_like(masks[0], dtype=np.int32)
                for i, mask in enumerate(masks, start=1):
                    labeled_image[mask] = i

            elif self._discover_method == "Suite2p":
                pass
            
            elif self._discover_method == "CaImAn":
                pass


            elif self._discover_method == "Custom":
                pass

            else:
                raise ValueError(f"Unknown ROI Method: {self._discover_method}")
            # Save original discovered ROIs
           

            # ==== 👇 Project thresholded masks on STIMViewer ====
            # from skimage.color import label2rgb
            # from projection import ProjectDisplay
            # from PyQt5.QtGui import QGuiApplication
            # rgb_image = (label2rgb(labeled_image, bg_label=0) * 255).astype(np.uint8)
            # screen = QGuiApplication.screens()[1]  # or [0] if only one
            # size = screen.size()
            # h, w = size.height(), size.width()
            # rgb_image = cv2.resize(rgb_image, (w, h), interpolation=cv2.INTER_NEAREST)
            # screens = QGuiApplication.screens()
            # screen = screens[1] if len(screens) > 1 else screens[0]
            # self.proj_display = ProjectDisplay(screen)
            # self.proj_display.show_image_fullscreen_on_second_monitor(rgb_image, homography_matrix=None)
            # ==== 👇 Project thresholded masks on STIMViewer ====
            from skimage.color import label2rgb
            from projection import ProjectDisplay
            from PyQt5.QtGui import QGuiApplication

            # 1) camera-label image → RGB
            rgb_image = (label2rgb(labeled_image, bg_label=0) * 255).astype(np.uint8)

            # 2) load camera→projector homography you saved during calibration
            H = np.load("homography_cam2proj.npy")          # shape (3, 3)

            # 3) warp directly to the projector’s native resolution
            screen   = QGuiApplication.screens()[1] if len(QGuiApplication.screens()) > 1 \
                    else QGuiApplication.screens()[0]
            proj_w, proj_h = screen.size().width(), screen.size().height()

            rgb_image = cv2.warpPerspective(
                rgb_image, H, (proj_w, proj_h),            # output size = projector pixels
                flags=cv2.INTER_NEAREST,                   # keep crisp label edges
                borderMode=cv2.BORDER_CONSTANT, borderValue=0
            )

            # 4) show it – no further resize, no internal homography
            self.proj_display = ProjectDisplay(screen)
            self.proj_display.show_image_fullscreen_on_second_monitor(
                rgb_image, homography_matrix=None          # already warped
            )

            np.savez_compressed(self.rois_path, masks=masks, sizes=sizes, labels=labeled_image)
            GPU.log_INFO(f"ROIs written to {self.rois_path}")
      
            QtCore.QMetaObject.invokeMethod(self, "start_live_traces", QtCore.Qt.QueuedConnection)
            GPU.log_INFO("Live trace extraction requested after ROI discovery.")

            if not self.camera.is_recording:
                QtCore.QMetaObject.invokeMethod(self.camera, "start_recording", QtCore.Qt.QueuedConnection)
                GPU.log_INFO("Recording requested after ROI discovery.")

        except Exception as e:
            GPU.log_ERRO(f"ROI discovery failed: {e}")


    def run_refine_rois(self):
        threading.Thread(target=self._thread_refine_rois, daemon=True).start()
    
    @pyqtSlot()
    def start_live_traces(self):
        print("Camera acquisition_running:", self.camera.acquisition_running)

        if self.live_extractor is not None:
            GPU.log_NOTI("Live trace extractor already running.")
            return

        if not self.camera.acquisition_running:
            GPU.log_WARN("Camera acquisition is not running; attempting to start...")
            started = self.camera.start_realtime_acquisition()
            if not started:
                GPU.log_ERRO("Failed to start camera acquisition. Aborting live trace initialization.")
                return
            else:
                GPU.log_INFO("Camera acquisition started for live trace extraction.")

        roi_path = self.rois_path
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

    @pyqtSlot()
    def start_live_traces_napari(self):
        print("Camera acquisition_running:", self.camera.acquisition_running)

        if self.live_extractor_napari is not None:
            GPU.log_NOTI("Live trace extractor already running.")
            return

        if not self.camera.acquisition_running:
            GPU.log_WARN("Camera acquisition is not running; attempting to start...")
            started = self.camera.start_realtime_acquisition()
            if not started:
                GPU.log_ERRO("Failed to start camera acquisition. Aborting live trace initialization.")
                return
            else:
                GPU.log_INFO("Camera acquisition started for live trace extraction.")

        roi_path = self.rois_path
        if not os.path.exists(roi_path):
            GPU.log_ERRO("No ROI file found. Run Discover or Refine ROIs first.")
            return

        try:
            self.live_extractor_napari = LiveTraceExtractorNapari(
                camera=self.camera,
                label_path=roi_path,
                plot_widget=self.trace_plot,
                max_points=300
            )
            GPU.log_INFO(f"Live trace extraction started using {os.path.basename(roi_path)}.")
        except Exception as e:
            GPU.log_ERRO(f"Failed to start live traces: {e}")

    def _wait_until_camera_stops(self, timeout: float = 2.0):
        """
        Block (on the GUI thread) until camera.acquisition_running and camera.is_recording
        are both False, or until `timeout` seconds have elapsed.
        
        This polling ensures the camera’s internal event loop has actually stopped
        before we begin CPU/GPU work.
        """
        start = time.time()
        # First, tell the camera to stop streaming & recording:
        try:
            # It’s often best to stop acquisition before stopping recording,
            # but your Camera API may differ. If your camera stops recording
            # first, then streaming, feel free to swap these two lines.
            if self.camera.acquisition_running:
                self.camera.stop_realtime_acquisition()
            if self.camera.is_recording:
                self.camera.stop_recording()
        except Exception as e:
            GPU.log_WARN(f"Error while requesting camera stop: {e}")

        # Now poll until both flags are False or we exceed `timeout`.
        while True:
            still_streaming = getattr(self.camera, "acquisition_running", False)
            still_recording = getattr(self.camera, "is_recording", False)
            if not still_streaming and not still_recording:
                return True
            if (time.time() - start) > timeout:
                # Timed out waiting for the camera to become idle
                return False
            # Sleep very briefly so we don’t lock up the GUI entirely.
            # Qt will still process events between each short sleep.
            QtCore.QCoreApplication.processEvents()  # allow Qt to update/wheel
            time.sleep(0.02)

    def _thread_refine_rois(self):
        self.stop_live_traces_napari()
        GPU.log_NOTI("Refining ROIs in GUI…")
        try:
            # load the mean, masks, run your roi_editor logic 
            from otsu_thresh import load_movie, compute_mean_projection
            mean = compute_mean_projection(load_movie(self.video_path), calib_frames=5400)
            mean = cv2.resize(mean, (1936, 1096), interpolation=cv2.INTER_NEAREST)
            masks = np.load(self.rois_path)["masks"]
            
            self.refineRequested.emit(mean, masks)
           
        except Exception as e:
            GPU.log_ERRO(f"ROI refinement failed: {e}")

    @pyqtSlot(object, object)
    def _launch_napari_viewer(self, mean, masks):
        from roi_editor import refine_rois
        self.stop_live_traces()
        # import napari
        ok = self._wait_until_camera_stops(timeout=2.0)
        GPU.log_INFO("Recording stopped before launching napari.")


        # === Step 1: Pause conflicting components ===
        try:
            if self.proj_display:
                self.proj_display.close()
            self.camera.stop_realtime_acquisition()
            GPU.log_INFO("Paused camera and projection before launching napari.")
        except Exception as e:
            GPU.log_WARN(f"Failed to pause components before napari: {e}")

        _, viewer = refine_rois(mean, masks, return_viewer=True)  # refine_rois must support return_viewer=True

       
        def restore_after_napari(event=None):
            try:
                from skimage.color import label2rgb
                from PyQt5.QtGui import QGuiApplication
                import numpy as np, cv2
                from projection import ProjectDisplay

                # --- load latest labels and make them RGB -------------------------
                labels     = np.load("rois.npz")["labels"]
                rgb_image  = (label2rgb(labels, bg_label=0) * 255).astype(np.uint8)

                # --- apply camera→projector homography once -----------------------
                H = np.load("homography_cam2proj.npy")            # 3×3

                screens   = QGuiApplication.screens()
                screen    = screens[1] if len(screens) > 1 else screens[0]
                proj_w, proj_h = screen.size().width(), screen.size().height()

                rgb_image = cv2.warpPerspective(
                    rgb_image, H, (proj_w, proj_h),
                    flags=cv2.INTER_NEAREST,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0
                )
                # ------------------------------------------------------------------

                # launch / refresh projector window
                if self.proj_display:
                    self.proj_display.close()
                self.proj_display = ProjectDisplay(screen)
                self.proj_display.show_image_fullscreen_on_second_monitor(
                    rgb_image, homography_matrix=None      # already warped
                )

                GPU.log_INFO("Mask projected after napari closed.")
                # QtCore.QTimer.singleShot(50, self._finish_restore)
                # Restart acquisition, recording, and live traces
                # self.camera.start_realtime_acquisition()
                # self.camera.start_recording()
                self.camera.start_realtime_acquisition()
                self.camera.start_recording()

                # Only launch LiveTraceExtractor once, in Pygame mode:
                self.live_extractor_napari = LiveTraceExtractorNapari(
                    camera=self.camera,
                    label_path=self.rois_path,
                    plot_widget=self.trace_plot,
                    max_points=300,
                    use_pygame_plot=True          # force Pygame mode
                )
                self.start_live_traces_napari()
                GPU.log_INFO("Camera and live trace restarted after napari.")

            except Exception as e:
                GPU.log_ERRO(f"Failed to restore after napari: {e}")



        viewer.window._qt_window.closeEvent = restore_after_napari

    # def _finish_restore(self):
    #     # Called ~50 ms after acquisition started
    #     if not self.camera.is_recording:
    #         self.camera.start_recording()
    #         GPU.log_INFO("Camera recording restarted.")

    #     # Start LiveTraceExtractor with PyQtGraph (no Pygame)
    #     try:
    #         self.live_extractor = LiveTraceExtractor(
    #             camera=self.camera,
    #             label_path=self.rois_path,
    #             plot_widget=self.trace_plot,
    #             max_points=300,
    #         )
    #         GPU.log_INFO("LiveTraceExtractor re‐launched.")
    #     except Exception as e:
    #         GPU.log_ERRO(f"Failed to relaunch LiveTraceExtractor: {e}")

    def run_view_traces(self):

        if not self.live_extractor:
            GPU.log_ERRO("Live trace extractor is not running.")
            return
        try:
            self.live_extractor.export_traces("live_traces.npy")
        except Exception as e:
            GPU.log_ERRO(f"Trace view failed: {e}")


    def closeEvent(self, event):
        # Properly stop recording and acquisition
        if self.live_extractor:
            self.live_extractor.stop()
            self.live_extractor = None
        if self.live_extractor_napari:
            self.live_extractor_napari.stop()
            self.live_extractor_napari = None
        if self.camera:
            self.camera.stop_recording()
            self.camera.stop_realtime_acquisition()
        self.closed.emit()
        event.accept()  # Allow the window to actually close


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
