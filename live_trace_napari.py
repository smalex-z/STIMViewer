
from pathlib import Path
import os

# use an env-var override so you can change it without editing code again
SSD_ROOT = Path(os.getenv("STIM_DATA_DIR",
            "/media/aharonilabjetson2/NVMe/stimviewer_data")).expanduser()
SSD_ROOT.mkdir(parents=True, exist_ok=True)      # auto-create on first run

import numpy as np
import cupy as cp

import colorsys

import pyqtgraph as pg
from collections import deque
import threading
import queue
from PyQt5.QtCore import QObject, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.figure import Figure
# from PyQt5.QtWidgets import QDialog, QVBoxLayout
import cv2
import pygame


# # class LiveTraceExtractor(QObject):
# #     update_plot_signal = pyqtSignal()

# #     def __init__(self, camera, label_path, plot_widget=None, max_points=500, max_rois=8, use_pygame_plot=True):
# #         super().__init__()
# #         self.camera = camera
# #         self.use_pygame_plot = use_pygame_plot
# #         self.update_plot_signal.connect(self._update_plot)
# #         self.frame_queue = queue.Queue(maxsize=10)
# #         self.running = True
# #         self.worker_thread = threading.Thread(target=self._frame_processor, daemon=True)
# #         self.worker_thread.start()

# #         labels = np.load(label_path)['labels']
# #         frame_h, frame_w = 1096, 1936
# #         if labels.shape != (frame_h, frame_w):
# #             print(f"⚠️ Resizing ROI labels from {labels.shape} to {(frame_h, frame_w)}")
# #             labels = cv2.resize(labels, (frame_w, frame_h), interpolation=cv2.INTER_NEAREST)
# #         self.check_labels = labels

# #         self.ids = np.unique(labels)
# #         self.ids = self.ids[self.ids > 0][:max_rois] # max rois limit can change  by removing[:maxrois]
# #         flat_labels = labels.ravel()
# #         self.pix = [cp.asarray(np.flatnonzero(flat_labels == rid)) for rid in self.ids]

# #         self.buffers = {rid: deque(maxlen=max_points) for rid in self.ids}

# #         if self.use_pygame_plot:
# #             pygame.init()
# #             self.screen_width, self.screen_height = 800, 600
# #             self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
# #             pygame.display.set_caption("Live ROI Traces")
# #             self.clock = pygame.time.Clock()
# #         else:
# #             self.plot = plot_widget
# #             pi = self.plot.getPlotItem()
# #             pi.clear()
# #             pi.addLegend()
# #             pi.setLabel('left', 'Mean Intensity')
# #             pi.setLabel('bottom', 'Frames ago')
# #             pi.setYRange(0, 255)
# #             pi.setLimits(xMin=0, xMax=max_points)
# #             pi.enableAutoRange(axis='x', enable=True)
# #             pi.enableAutoRange(axis='y', enable=False)
# #             self.curves = {}
# #             for rid in self.ids:
# #                 curve = pi.plot(pen=pg.mkPen(width=2), name=f"ROI {rid}")
# #                 self.curves[rid] = curve

# #         camera.frame_ready.connect(self.on_frame)

# class LiveTraceExtractor(QObject):
#     update_plot_signal = pyqtSignal()

#     def __init__(self,
#                  camera,
#                  label_path,
#                  plot_widget=None,
#                  max_points=500,
#                  max_rois=8,
#                  use_pygame_plot=True):
#         super().__init__()
#         self.camera = camera
#         self.use_pygame_plot = use_pygame_plot
#         self.update_plot_signal.connect(self._update_plot)
#         self.frame_queue = queue.Queue(maxsize=10)
#         self.running = True
#         self._frame_count = 0
#         self._update_every_n = 3

#         # ─── FIRST, initialize Pygame if requested ───────────────────────────
#         if self.use_pygame_plot:
#             # initialize the SDL video system immediately
#             pygame.init()
#             self.screen_width, self.screen_height = 800, 600
#             self.screen = pygame.display.set_mode(
#                 (self.screen_width, self.screen_height)
#             )
#             pygame.display.set_caption("Live ROI Traces")
#             self.clock = pygame.time.Clock()
#         else:
#             # (PyQtGraph setup)…
#             self.plot = plot_widget
#             pi = self.plot.getPlotItem()
#             pi.clear()
#             pi.addLegend()
#             pi.setLabel('left', 'Mean Intensity')
#             pi.setLabel('bottom', 'Frames ago')
#             pi.setYRange(0, 255)
#             pi.setLimits(xMin=0, xMax=max_points)
#             pi.enableAutoRange(axis='x', enable=True)
#             pi.enableAutoRange(axis='y', enable=False)
#             self.curves = {}
#             labels = np.load(label_path)['labels']
#             self.ids = np.unique(labels)
#             for rid in self.ids:
#                 self.curves[rid] = pi.plot(pen=pg.mkPen(width=2),
#                                             name=f"ROI {rid}")

#         # ─── ONLY AFTER pygame (or pyqtgraph) window is ready,
#         #        start the background thread ───────────────────────────
#         self.worker_thread = threading.Thread(
#             target=self._frame_processor,
#             daemon=True
#         )
#         self.worker_thread.start()

#         # … now load labels, build self.pix, etc. …
#         labels = np.load(label_path)['labels']
#         frame_h, frame_w = 1096, 1936
#         if labels.shape != (frame_h, frame_w):
#             print(f"⚠️ Resizing ROI labels from {labels.shape} to "
#                   f"{(frame_h, frame_w)}")
#             labels = cv2.resize(labels,
#                                 (frame_w, frame_h),
#                                 interpolation=cv2.INTER_NEAREST)
#         self.check_labels = labels

#         self.ids = np.unique(labels)
#         self.ids = self.ids[self.ids > 0][:max_rois]
#         flat_labels = labels.ravel()
#         self.pix = [cp.asarray(np.flatnonzero(flat_labels == rid))
#                     for rid in self.ids]
#         self.buffers = {rid: deque(maxlen=max_points) for rid in self.ids}

#         # Only now connect to camera frames:
#         camera.frame_ready.connect(self.on_frame)


#     def on_frame(self, frame):
#         try:
#             self.frame_queue.put_nowait(frame)
#         except queue.Full:
#             pass

#     @staticmethod
#     def generate_colors(n):
#         return [tuple(int(c * 255) for c in colorsys.hsv_to_rgb(i / n, 1.0, 1.0)) for i in range(n)]



#     def _update_plot(self):
#         if not pygame.display.get_init():
#             return

#         if self.use_pygame_plot:
#             self.screen.fill((0, 0, 0))
#             # colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
#             colors = self.generate_colors(len(self.ids))

#             font = pygame.font.SysFont("Arial", 14)
#             margin = 50
#             axis_color = (200, 200, 200)
#             pygame.draw.line(self.screen, axis_color, (margin, margin), (margin, self.screen_height - margin), 2)  # Y axis
#             pygame.draw.line(self.screen, axis_color, (margin, self.screen_height - margin), (self.screen_width - margin, self.screen_height - margin), 2)  # X axis
#                     # Add Y-axis ticks and labels (Intensity)
#             for i in range(0, 256, 50):
#                 y = int(self.screen_height - margin - i * ((self.screen_height - 2 * margin) / 255))
#                 pygame.draw.line(self.screen, axis_color, (margin - 5, y), (margin + 5, y), 1)
#                 label = font.render(str(i), True, axis_color)
#                 self.screen.blit(label, (5, y - 7))

#             # Add X-axis ticks and labels (Frames ago)
#             x_len = max((len(self.buffers[rid]) for rid in self.ids), default=1)
#             for i in range(0, x_len, max(1, x_len // 10)):
#                 x = int(margin + i * ((self.screen_width - 2 * margin) / x_len))
#                 pygame.draw.line(self.screen, axis_color, (x, self.screen_height - margin - 5), (x, self.screen_height - margin + 5), 1)
#                 label = font.render(str(-x_len + i + 1), True, axis_color)
#                 self.screen.blit(label, (x - 10, self.screen_height - margin + 10))

#             for idx, rid in enumerate(self.ids):
#                 y_vals = list(self.buffers[rid])
#                 if len(y_vals) < 2:
#                     continue
#                 max_y = max(max(y_vals), 1)
#                 scale_x = (self.screen_width - 2 * margin) / len(y_vals)
#                 scale_y = (self.screen_height - 2 * margin) / max_y

#                 # Plot points
#                 points = [
#                     (int(margin + i * scale_x), int(self.screen_height - margin - val * scale_y))
#                     for i, val in enumerate(y_vals)
#                 ]
#                 pygame.draw.lines(self.screen, colors[idx % len(colors)], False, points, 2)

#                 label = f"ROI {rid}"
                
#                 text = font.render(label, True, colors[idx % len(colors)])
#                 self.screen.blit(text, (10, 20 * idx))  # Y offset to separate labels

#                 # y_vals = list(self.buffers[rid])
#                 # if len(y_vals) < 2:
#                 #     continue
#                 # max_y = max(max(y_vals), 1)
#                 # scale_x = self.screen_width / len(y_vals)
#                 # scale_y = self.screen_height / max_y
#                 # points = [
#                 #     (int(i * scale_x), int(self.screen_height - val * scale_y))
#                 #     for i, val in enumerate(y_vals)
#                 # ]
#                 # pygame.draw.lines(self.screen, colors[idx % len(colors)], False, points, 2)
#             pygame.display.flip()
#             self.clock.tick(30)
#             for event in pygame.event.get():
#                 if event.type == pygame.QUIT:
#                     self.stop()
#                     return
#         else:
#             all_values = []
#             for rid, curve in self.curves.items():
#                 y = list(self.buffers[rid])
#                 all_values.extend(y)
#                 x = list(range(-len(y)+1, 1))
#                 curve.setData(x, y)
#             if all_values:
#                 min_y, max_y = np.min(all_values), np.max(all_values)
#                 self.plot.setYRange(min_y - 5, max_y + 5)

#     def _frame_processor(self):
#         while self.running:
#             try:
#                 frame = self.frame_queue.get(timeout=0.5)
#             except queue.Empty:
#                 continue

#             try:
#                 if hasattr(frame, "get_numpy_1D"):
#                     h, w = frame.Height(), frame.Width()
#                     assert self.check_labels.shape == (h, w)
#                     np_frame = np.array(frame.get_numpy_1D(), dtype=np.uint8).reshape((h, w, 4))
#                     frame = np_frame[..., 0]
#                 elif isinstance(frame, np.ndarray):
#                     if frame.ndim == 3 and frame.shape[2] == 3:
#                         frame = frame[..., 0]
#                     elif frame.ndim == 2:
#                         pass
#                     else:
#                         raise ValueError("Unsupported frame format.")

#                 f_gpu = cp.asarray(frame.ravel(), dtype=cp.float32)
#                 for rid, mask_indices in zip(self.ids, self.pix):
#                     if mask_indices.size == 0:
#                         continue
#                     try:
#                         val = float(f_gpu[mask_indices].mean().get())
#                         self.buffers[rid].append(val)
#                     except Exception as e:
#                         print(f"❌ Error computing mean for ROI {rid}: {e}")

#                 self.update_plot_signal.emit()
#             except Exception as e:
#                 continue

#     def export_traces(self, output_path="live_traces.npy", rois_path="rois.npz", last_n=100, max_rois=10):
#         try:
#             if len(self.ids) == 0 or not self.buffers or all(len(self.buffers[rid]) == 0 for rid in self.ids):
#                 print("❌ No ROI traces available for export.")
#                 return
#             trace_matrix = np.stack([list(self.buffers[rid]) for rid in self.ids], axis=1)
#             np.save(output_path, trace_matrix)
#             print(f"✅ Traces exported to {output_path} — shape: {trace_matrix.shape}")
#         except Exception as e:
#             print(f"❌ Failed to export traces: {e}")

#     def stop(self):
#         self.running = False
#         self.worker_thread.join(timeout=1.0)
#         if hasattr(self.camera, "frame_ready"):
#             self.camera.frame_ready.disconnect(self.on_frame)
#         if self.use_pygame_plot:
#             pygame.quit()

import threading
import queue
import numpy as np
import cupy as cp
import colorsys

from collections import deque
from PyQt5.QtCore import QObject, pyqtSignal
import pyqtgraph as pg
import pygame


class LiveTraceExtractorNapari(QObject):
    update_plot_signal = pyqtSignal()

    def __init__(
        self,
        camera,
        label_path,
        plot_widget=None,
        max_points=500,
        max_rois=8,
        use_pygame_plot=True
    ):
        super().__init__()
        self.camera = camera
        self.use_pygame_plot = use_pygame_plot
        self.update_plot_signal.connect(self._update_plot)

        # Queues and flags
        self.frame_queue = queue.Queue(maxsize=10)
        self.running = True
        self._frame_count = 0
        self._update_every_n = 3  # repaint every 3 frames

        # ── 1) LOAD ROI labels and build ONE GPU mask matrix ───────────────────
        labels = np.load(label_path)["labels"]        # shape (H, W)
        H, W = labels.shape

        flat_cpu = labels.ravel()
        ids = np.unique(labels)
        self.ids = ids[ids > 0][:max_rois]            # only positive labels, up to max_rois

        # Move labels to GPU and build a boolean mask per ROI
        flat_gpu = cp.asarray(flat_cpu, dtype=cp.int32)      # shape (H*W,)
        mask_list = []
        for rid in self.ids:
            mask_list.append((flat_gpu == int(rid)))        # each is shape (H*W,) bool
        self.mask_mat = cp.stack(mask_list, axis=0)          # shape (n_rois, H*W)
        self.roi_sizes = self.mask_mat.sum(axis=1).astype(cp.float32)  # shape (n_rois,)

        # Pre‐allocate one big GPU buffer for incoming frames
        self._f_gpu = cp.empty(H * W, dtype=cp.float32)

        # ── 2) SET UP EITHER Pygame OR PyQtGraph ────────────────────────────────
        if self.use_pygame_plot:
            # ─── Pygame initialization ────────────────────────────────────────
            pygame.init()
            self.screen_width, self.screen_height = 800, 600
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            pygame.display.set_caption("Live Traces")
            self.clock = pygame.time.Clock()

            # Pre‐compute a distinct color for each ROI
            self.colors = [
                tuple(int(c * 255) for c in colorsys.hsv_to_rgb(i / len(self.ids), 1.0, 1.0))
                for i in range(len(self.ids))
            ]

        else:
            # ─── PyQtGraph setup ─────────────────────────────────────────────
            self.plot = plot_widget
            pi = self.plot.getPlotItem()
            pi.clear()
            pi.addLegend()
            pi.setLabel('left', 'Mean Intensity')
            pi.setLabel('bottom', 'Frames elapsed')
            pi.setYRange(0, 255)
            pi.setLimits(xMin=0, xMax=max_points)
            pi.enableAutoRange(axis='x', enable=True)
            pi.enableAutoRange(axis='y', enable=False)
            self.curves = {}
            for rid in self.ids:
                curve = pi.plot(pen=pg.mkPen(width=2), name=f"ROI {rid}")
                self.curves[rid] = curve

        # ── 3) BUILD CPU buffers to store the “last max_points” for each ROI ───
        self.buffers = {rid: deque(maxlen=max_points) for rid in self.ids}

        # ── 4) CONNECT & START THREAD ────────────────────────────────────────
        self.worker_thread = threading.Thread(target=self._frame_processor, daemon=True)
        self.worker_thread.start()
        camera.frame_ready.connect(self.on_frame)


    def on_frame(self, frame):
        """Receive a new camera frame and enqueue it for processing."""
        try:
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass


    # def _frame_processor(self):
    #     """Background thread: copy each frame to GPU, compute ROI means, update buffers, and signal repaint."""
    #     while self.running:
    #         try:
    #             frame = self.frame_queue.get(timeout=0.5)
    #         except queue.Empty:
    #             continue

    #         # ── A) COPY the new frame into our pre‐allocated GPU buffer ─────────────
    #         flat_cpu = frame.ravel().astype(np.float32)
    #         self._f_gpu.set(flat_cpu)  # one cudaMemcpy from host→device

    #         # ── B) COMPUTE all ROI sums in one big matrix‐multiply style step ──────
    #         #     mask_mat shape = (n_rois, H*W); _f_gpu shape = (H*W,)
    #         sums = (self.mask_mat * self._f_gpu).sum(axis=1)  # GPU result: (n_rois,)
    #         means_gpu = sums / self.roi_sizes                   # still on GPU
    #         means = means_gpu.get()                             # transfer length‐n_rois array back to CPU

    #         # ── C) APPEND each ROI’s mean to its ring buffer ───────────────────────
    #         for i, rid in enumerate(self.ids):
    #             self.buffers[rid].append(float(means[i]))

    #         # ── D) THROTTLE repaint frequency ─────────────────────────────────────
    #         self._frame_count += 1
    #         if self._frame_count >= self._update_every_n:
    #             self._frame_count = 0
    #             self.update_plot_signal.emit()

    def _frame_processor(self):
        """Background thread: copy each frame to GPU, compute ROI means, update buffers, and signal repaint."""
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            # ── A) UNPACK “frame” into a 2D gray‐scale NumPy array ───────────────────────────
            if hasattr(frame, "get_numpy_1D"):
                # IDS‐Peak “Image” object
                h, w = frame.Height(), frame.Width()
                arr4 = np.array(frame.get_numpy_1D(), dtype=np.uint8).reshape((h, w, 4))
                gray = arr4[..., 0]
            elif isinstance(frame, np.ndarray):
                if frame.ndim == 3 and frame.shape[2] == 3:
                    gray = frame[..., 0]
                elif frame.ndim == 2:
                    gray = frame
                else:
                    # unsupported format
                    continue
            else:
                # unknown frame type
                continue

            flat_cpu = gray.ravel().astype(np.float32)
            self._f_gpu.set(flat_cpu)  # one cudaMemcpy from host→device

            # ── B) COMPUTE all ROI sums in one big matrix‐multiply step ───────────────────
            sums = (self.mask_mat * self._f_gpu).sum(axis=1)   # GPU: (n_rois,)
            means_gpu = sums / self.roi_sizes                  # still on GPU
            means = means_gpu.get()                            # CPU: length‐n_rois

            # ── C) APPEND each ROI’s mean to its ring buffer ─────────────────────────────
            for i, rid in enumerate(self.ids):
                self.buffers[rid].append(float(means[i]))

            # ── D) THROTTLE repaint frequency ──────────────────────────────────────────
            self._frame_count += 1
            if self._frame_count >= self._update_every_n:
                self._frame_count = 0
                self.update_plot_signal.emit()



    def _update_plot(self):
        """
        Called once every _update_every_n frames.  
        Draw either in PyQtGraph or in Pygame, depending on the mode.
        """
        if self.use_pygame_plot:
            # ── Pygame drawing ───────────────────────────────────────────────────
            self.screen.fill((0, 0, 0))
            margin = 50
            axis_color = (200, 200, 200)
            font = pygame.font.SysFont("Arial", 14)

            # Draw Y‐axis
            pygame.draw.line(
                self.screen, axis_color,
                (margin, margin),
                (margin, self.screen_height - margin),
                2
            )
            # Draw X‐axis
            pygame.draw.line(
                self.screen, axis_color,
                (margin, self.screen_height - margin),
                (self.screen_width - margin, self.screen_height - margin),
                2
            )

            # Y‐axis ticks and labels (intensity scale 0→255)
            for i in range(0, 256, 50):
                y = int(self.screen_height - margin - i * ((self.screen_height - 2 * margin) / 255))
                pygame.draw.line(
                    self.screen, axis_color,
                    (margin - 5, y), (margin + 5, y), 1
                )
                label = font.render(str(i), True, axis_color)
                self.screen.blit(label, (5, y - 7))

            # X-axis ticks and labels (frames elapsed)
            x_len = max((len(self.buffers[rid]) for rid in self.ids), default=1)
            for i in range(0, x_len, max(1, x_len // 10)):
                x = int(margin + i * ((self.screen_width - 2 * margin) / x_len))
                pygame.draw.line(
                    self.screen, axis_color,
                    (x, self.screen_height - margin - 5),
                    (x, self.screen_height - margin + 5),
                    1
                )
                # Show positive frame index (0, 1, 2, …)
                label = font.render(str(i), True, axis_color)
                self.screen.blit(label, (x - 10, self.screen_height - margin + 10))

            # Plot each ROI’s trace
            for idx, rid in enumerate(self.ids):
                y_vals = list(self.buffers[rid])
                if len(y_vals) < 2:
                    continue

                # Scale so that max(y_vals) maps to top margin
                max_y = max(max(y_vals), 1)
                scale_x = (self.screen_width - 2 * margin) / len(y_vals)
                scale_y = (self.screen_height - 2 * margin) / max_y

                points = [
                    (
                        int(margin + i * scale_x),
                        int(self.screen_height - margin - val * scale_y)
                    )
                    for i, val in enumerate(y_vals)
                ]
                pygame.draw.lines(self.screen, self.colors[idx % len(self.colors)], False, points, 2)

                # Label “ROI {rid}” in matching color
                text = font.render(f"ROI {rid}", True, self.colors[idx % len(self.colors)])
                self.screen.blit(text, (10, 20 * idx))

            pygame.display.flip()
            self.clock.tick(30)

            # Handle Pygame window events (e.g. user clicking the close button)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop()
                    return

        else:
            # ── PyQtGraph drawing ────────────────────────────────────────────────
            all_y = []
            for rid, curve in self.curves.items():
                y = list(self.buffers[rid])
                if not y:
                    continue
                x = list(range(len(y)))  # use 0..(len−1) as “frames elapsed”
                curve.setData(x, y)
                all_y.extend(y)

            if all_y:
                mn, mx = min(all_y), max(all_y)
                self.plot.setYRange(mn - 5, mx + 5)


    def stop(self):
        """Stop the worker thread and disconnect the camera signal."""
        self.running = False
        self.worker_thread.join(timeout=1.0)
        if hasattr(self.camera, "frame_ready"):
            self.camera.frame_ready.disconnect(self.on_frame)
        if self.use_pygame_plot:
            pygame.quit()
