# # live_trace_extractor.py

import numpy as np
import cupy as cp
import pyqtgraph as pg
from collections import deque
import threading
import queue
from PyQt5.QtCore import QObject, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QDialog, QVBoxLayout
import numpy as np
import os
import cv2


class LiveTraceExtractor(QObject):
    update_plot_signal = pyqtSignal()
    def __init__(self, camera, label_path, plot_widget: pg.PlotWidget, max_points=500, max_rois=8):
        """
        camera         – your Camera instance
        label_path     – path to rois_current.npz (must contain 'labels')
        plot_widget    – a pyqtgraph PlotWidget already placed in your UI
        max_points     – how many most recent frames to show
        """
        # Load ROI labels (assumed from projected mask)
        super().__init__()
        self.camera =camera
        self.update_plot_signal.connect(self._update_plot) 
        self.frame_queue = queue.Queue(maxsize=10)
        self.running = True
        self.worker_thread = threading.Thread(target=self._frame_processor, daemon=True)
        self.worker_thread.start()
        labels = np.load(label_path)['labels']
        frame_h, frame_w = 1096, 1936  # or dynamically extract from a sample frame
        if labels.shape != (frame_h, frame_w):
            print(f"⚠️ Resizing ROI labels from {labels.shape} to {(frame_h, frame_w)}")
            labels = cv2.resize(labels, (frame_w, frame_h), interpolation=cv2.INTER_NEAREST)
        print(f"Loaded labels shape: {labels.shape}")
        self.check_labels = np.load(label_path)['labels']
        self.ids = np.unique(labels)
        self.ids = self.ids[self.ids > 0][:max_rois]  # keep only positive ROI IDs
        print(f"Loaded ROI IDs: {self.ids}")

        flat_labels = labels.ravel()
        self.pix = [cp.asarray(np.flatnonzero(flat_labels == rid)) for rid in self.ids]

        # Pre-allocate buffers for live plotting
        self.buffers = {rid: deque(maxlen=max_points) for rid in self.ids}
        
        # Plot setup
        self.plot = plot_widget
        pi = self.plot.getPlotItem()
        pi.clear()
        pi.addLegend()
        pi.setLabel('left', 'Mean Intensity')
        pi.setLabel('bottom', 'Frames ago')
        pi.setYRange(0, 255)
        pi.setLimits(xMin=0, xMax=max_points)
        pi.enableAutoRange(axis='x', enable=True)
        pi.enableAutoRange(axis='y', enable=False)

        self.curves = {}
        for rid in self.ids:
            curve = pi.plot(pen=pg.mkPen(width=2), name=f"ROI {rid}")
            self.curves[rid] = curve

        # Hook camera callback
        camera.frame_ready.connect(self.on_frame)

    def on_frame(self, frame):
        try:
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass  # Drop frame if busy


    
    # def on_frame(self, frame):
    #     # if not isinstance(frame, np.ndarray):
    #     #     frame = np.array(frame)
    #     # try:
    #     #     self.frame_queue.put_nowait(frame)
    #     # except queue.Full:
    #     #     pass  # Drop frame if busy
    #     while self.running:
    #         try:
    #             self.frame = self.frame_queue.get(timeout=0.5)
    #         except queue.Empty:
    #             continue




    def _update_plot(self):
        all_values = []
        for rid, curve in self.curves.items():
            y = list(self.buffers[rid])
            all_values.extend(y)
            x = list(range(-len(y)+1, 1))
            curve.setData(x, y)

        if all_values:
            min_y, max_y = np.min(all_values), np.max(all_values)
            self.plot.setYRange(min_y - 5, max_y + 5)


    def _frame_processor(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=0.5)
                if hasattr(frame, "Height") and hasattr(frame, "Width"):
                    print(f"Incoming frame shape (IDS): {frame.Height()}x{frame.Width()}")
                elif isinstance(frame, np.ndarray):
                    print(f"Incoming frame shape: {frame.shape}")
                else:
                    print(f"Unknown frame type: {type(frame)}")

            except queue.Empty:
                continue  # Skip this loop, don't go further if no frame

            try:
                # print(f"Frame shape: {frame.shape}")  # ✅ This is safe now
                print(f"ROI means: {[float(f_gpu[mask].mean().get()) for mask in self.pix]}")

                # Convert IDS Image to NumPy if needed
                if hasattr(frame, "get_numpy_1D"):
                    h, w = frame.Height(), frame.Width()
                    assert self.check_labels.shape == (h, w), "Label shape does not match camera frame shape!"
                    if hasattr(frame, "Height") and hasattr(frame, "Width"):
                        print(f"Incoming frame shape (IDS): {frame.Height()}x{frame.Width()}")
                    elif isinstance(frame, np.ndarray):
                        print(f"Incoming frame shape: {frame.shape}")
                    else:
                        print(f"Unknown frame type: {type(frame)}")

                    np_frame = np.array(frame.get_numpy_1D(), dtype=np.uint8).reshape((h, w, 4))
                    frame = np_frame[..., 0]
                    # print(f"Frame shape (converted NumPy): {frame.shape}")
                elif isinstance(frame, np.ndarray):
                    if frame.ndim == 3 and frame.shape[2] == 3:
                        frame = frame[..., 0]
                    elif frame.ndim == 2:
                        pass
                    else:
                        raise ValueError("Unsupported frame format.")

                # GPU computation
                f_gpu = cp.asarray(frame.ravel(), dtype=cp.float32)
                # for rid, mask_indices in zip(self.ids, self.pix):
                #     val = float(f_gpu[mask_indices].mean().get())
                #     print(f"Appending to buffer for ROI {rid}: {val}")

                #     print(f"ROI {rid}: {val}")
                #     self.buffers[rid].append(val)
                for rid, mask_indices in zip(self.ids, self.pix):
                    if mask_indices.size == 0:
                        print(f"⚠️ Empty mask for ROI {rid}")
                        continue
                    try:
                        val = float(f_gpu[mask_indices].mean().get())
                        self.buffers[rid].append(val)
                        print(f"✅ ROI {rid}: {val} added to buffer")
                    except Exception as e:
                        print(f"❌ Error computing mean for ROI {rid}: {e}")


                self.update_plot_signal.emit()

            except Exception as e:
                if isinstance(frame, np.ndarray):
                    print(f"Frame shape: {frame.shape}")
                elif hasattr(frame, "Height") and hasattr(frame, "Width"):
                    print(f"Frame shape (IDS Image): {frame.Height()}x{frame.Width()}")
                else:
                    print("Unknown frame type:", type(frame))

                continue




    def export_traces(self, output_path="live_traces.npy", rois_path="rois.npz", last_n=100, max_rois=10):
        """
        Save and display the last N frames of ROI traces.
        """
        try:
            # Save the trace matrix
            if len(self.ids) == 0 or not self.buffers or all(len(self.buffers[rid]) == 0 for rid in self.ids):
                print("❌ No ROI traces available for export.")
                return
            trace_matrix = np.stack([list(self.buffers[rid]) for rid in self.ids], axis=1)
            np.save(output_path, trace_matrix)
            print(f"✅ Traces exported to {output_path} — shape: {trace_matrix.shape}")

            # Load labels
            if not os.path.exists(rois_path):
                print("❌ ROI file not found.")
                return
            labels = np.load(rois_path)["labels"]
            print(labels.shape)
            print(np.unique(labels))
            ids = np.unique(labels)
            ids = ids[ids > 0]
            if ids.size == 0:
                print("❌ ROI mask contains zero ROIs.")
                return

            # Prepare data for plotting
            if trace_matrix.shape[0] < trace_matrix.shape[1]:
                trace_matrix = trace_matrix.T
            T, N = trace_matrix.shape
            if last_n > T:
                last_n = T
            shown_rois = min(max_rois, N)
            trace_block = trace_matrix[-last_n:, :shown_rois]
            x = np.arange(-last_n + 1, 1, 1)

            # Create a dialog to display the plot
            dialog = QDialog()
            dialog.setWindowTitle("Live ROI Traces")
            layout = QVBoxLayout()
            dialog.setLayout(layout)

            # Create a Matplotlib figure and canvas
            fig = Figure(figsize=(12, 6))
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)
            ax = fig.add_subplot(111)

            # Plot the traces
            for i in range(shown_rois):
                ax.plot(x, trace_block[:, i], label=f"ROI {i+1}")
            ax.set_xlabel("Frames ago")
            ax.set_ylabel("Mean intensity")
            ax.set_title(f"Live ROI Traces — last {last_n} frames, {shown_rois} ROIs")
            ax.legend(loc="upper right", fontsize="small", ncol=2)
            ax.grid(True)
            fig.tight_layout()

            # Show the dialog
            dialog.exec_()

        except Exception as e:
            print(f"❌ Failed to export and display traces: {e}")




    def stop(self):
        self.running = False
        self.worker_thread.join(timeout=1.0)
        if hasattr(self.camera, "frame_ready"):
           self.camera.frame_ready.disconnect(self.on_frame)




