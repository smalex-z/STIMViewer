# # live_trace_extractor.py
# import os


# import numpy as np
# import cupy as cp
# import pyqtgraph as pg
# from collections import deque

# class LiveTraceExtractor:
#     def __init__(self, camera, label_path, plot_widget: pg.PlotWidget, max_points=500):
#         """
#         camera         – your Camera instance
#         label_path     – path to rois_current.npz (must contain 'labels')
#         plot_widget    – a pyqtgraph PlotWidget already placed in your UI
#         max_points     – how many most recent frames to show
#         """
#         # load & prep ROIs
#         lab = np.load(label_path)['labels']
#         self.ids = np.unique(lab)[1:]
#         flat = lab.ravel()
#         self.pix = [cp.asarray(np.flatnonzero(flat == rid)) for rid in self.ids]
        
#         # pre-allocate GPU traces
#         self.traces_gpu = None  # we’ll allocate per-frame if we want full movie
#         # but for live plotting we keep only a sliding window:
#         self.buffers = {rid: deque(maxlen=max_points) for rid in self.ids}
        
#         # plotting
#         self.plot = plot_widget
#         # self.curves = {
#         #     rid: self.plot.plot(pen=pg.mkPen(width=2)) for rid in self.ids
#         # }
#         # self.plot.addLegend()
#         # for rid, curve in self.curves.items():
#         #     self.plot.legend.addItem(curve, f"ROI {rid}")
#         pi = self.plot.getPlotItem()
#         pi.addLegend()
#         vb = pi.getViewBox()
#         vb.setMouseEnabled(x=True, y=True)
#         # pi = self.plot.getPlotItem()
#         pi.setLabel('left','Mean Intensity')
#         pi.setLabel('bottom','Frames ago')
#         pi.setYRange(0, 255)          # camera 8-bit range
#         pi.setLimits(xMin=0, xMax=max_points)
#         pi.enableAutoRange(axis='y', enable=False)
#         pi.enableAutoRange(axis='x', enable=True)

#         self.curves = {}
#         for rid in self.ids:
#             # plot *with* a name so the legend entry is created immediately
#             curve = pi.plot(pen=pg.mkPen(width=2), name=f"ROI {rid}")
#             self.curves[rid] = curve

        
#         # hook camera
#         camera._interface.on_image_received = self.on_frame

#     def on_frame(self, frame: np.ndarray):
#         """
#         Called on *every* new frame. frame is H×W NumPy array.
#         """
#         f_gpu = cp.asarray(frame.ravel(), dtype=cp.float32)
#         for rid, idx in zip(self.ids, self.pix):
#             val = float(f_gpu[idx].mean().get())
#             self.buffers[rid].append(val)
        
#         self._update_plot()

#     def _update_plot(self):
#         """
#         Refresh each curve with its current buffer.
#         """
#         for rid, curve in self.curves.items():
#             y = list(self.buffers[rid])
#             if not y:
#                 continue
#             x = np.arange(len(y))
#             curve.setData(x, y)
import numpy as np
import cupy as cp
import pyqtgraph as pg
from collections import deque
import threading
import queue
from PyQt5.QtCore import QObject, pyqtSignal


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
        
        self.check_labels = np.load(label_path)['labels']
        self.ids = np.unique(labels)
        self.ids = self.ids[self.ids > 0][:max_rois]  # keep only positive ROI IDs

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
            except queue.Empty:
                continue  # Skip this loop, don't go further if no frame

            try:
                print(f"Frame shape: {frame.shape}")  # ✅ This is safe now

                # Convert IDS Image to NumPy if needed
                if hasattr(frame, "get_numpy_1D"):
                    h, w = frame.Height(), frame.Width()
                    assert self.labels.shape == (h, w), "Label shape does not match camera frame shape!"

                    np_frame = np.array(frame.get_numpy_1D(), dtype=np.uint8).reshape((h, w, 4))
                    frame = np_frame[..., 0]
                    print(f"Frame shape (converted NumPy): {frame.shape}")
                elif isinstance(frame, np.ndarray):
                    if frame.ndim == 3 and frame.shape[2] == 3:
                        frame = frame[..., 0]
                    elif frame.ndim == 2:
                        pass
                    else:
                        raise ValueError("Unsupported frame format.")

                # GPU computation
                f_gpu = cp.asarray(frame.ravel(), dtype=cp.float32)
                for rid, mask_indices in zip(self.ids, self.pix):
                    val = float(f_gpu[mask_indices].mean().get())
                    self.buffers[rid].append(val)

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
        Save the last N frames of ROI traces to a file and visualize them.
        Each row is a frame, each column is an ROI.
        """
        try:
            trace_matrix = np.stack([list(self.buffers[rid]) for rid in self.ids], axis=1)
            np.save(output_path, trace_matrix)
            print(f"✅ Traces exported to {output_path} — shape: {trace_matrix.shape}")

            # Now show a quick plot
            import matplotlib.pyplot as plt
            import numpy as np
            import os
            import sys

            if not os.path.exists(rois_path):
                print("❌ No rois.npz found. Run ROI discovery/refinement first.")
                return
            if not os.path.exists(output_path):
                print(f"❌ No trace file found at {output_path}")
                return

            lab = np.load(rois_path)["labels"].astype(int)
            ids = np.unique(lab)
            ids = ids[ids > 0]
            if ids.size == 0:
                print("❌ ROI mask contains zero ROIs.")
                return

            traces = np.load(output_path)
            if traces.ndim != 2:
                print("❌ Trace file must be 2D (frames x ROIs).")
                return

            if traces.shape[0] < traces.shape[1]:
                traces = traces.T

            T, N = traces.shape
            if last_n > T:
                last_n = T

            shown_rois = min(max_rois, N)
            trace_block = traces[-last_n:, :shown_rois]
            x = np.arange(-last_n + 1, 1, 1)

            plt.figure(figsize=(12, 6))
            for i in range(shown_rois):
                plt.plot(x, trace_block[:, i], label=f"ROI {i+1}")
            plt.xlabel("Frames ago")
            plt.ylabel("Mean intensity")
            plt.title(f"Live ROI Traces — last {last_n} frames, {shown_rois} ROIs")
            plt.legend(loc="upper right", fontsize="small", ncol=2)
            plt.grid(True)
            plt.tight_layout()
            plt.show()

        except Exception as e:
            print(f"❌ Failed to export or visualize traces: {e}")



    def stop(self):
        self.running = False
        self.worker_thread.join(timeout=1.0)
        if hasattr(self.camera, "frame_ready"):
           self.camera.frame_ready.disconnect(self.on_frame)




