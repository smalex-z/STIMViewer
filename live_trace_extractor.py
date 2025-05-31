

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


# class LiveTraceExtractor(QObject):
#     update_plot_signal = pyqtSignal()

#     def __init__(self, camera, label_path, plot_widget=None, max_points=500, max_rois=8, use_pygame_plot=True):
#         super().__init__()
#         self.camera = camera
#         self.use_pygame_plot = use_pygame_plot
#         self.update_plot_signal.connect(self._update_plot)
#         self.frame_queue = queue.Queue(maxsize=10)
#         self.running = True
#         self.worker_thread = threading.Thread(target=self._frame_processor, daemon=True)
#         self.worker_thread.start()

#         labels = np.load(label_path)['labels']
#         frame_h, frame_w = 1096, 1936
#         if labels.shape != (frame_h, frame_w):
#             print(f"⚠️ Resizing ROI labels from {labels.shape} to {(frame_h, frame_w)}")
#             labels = cv2.resize(labels, (frame_w, frame_h), interpolation=cv2.INTER_NEAREST)
#         self.check_labels = labels

#         self.ids = np.unique(labels)
#         self.ids = self.ids[self.ids > 0][:max_rois] # max rois limit can change  by removing[:maxrois]
#         flat_labels = labels.ravel()
#         self.pix = [cp.asarray(np.flatnonzero(flat_labels == rid)) for rid in self.ids]

#         self.buffers = {rid: deque(maxlen=max_points) for rid in self.ids}

#         if self.use_pygame_plot:
#             pygame.init()
#             self.screen_width, self.screen_height = 800, 600
#             self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
#             pygame.display.set_caption("Live ROI Traces")
#             self.clock = pygame.time.Clock()
#         else:
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
#             for rid in self.ids:
#                 curve = pi.plot(pen=pg.mkPen(width=2), name=f"ROI {rid}")
#                 self.curves[rid] = curve

#         camera.frame_ready.connect(self.on_frame)

class LiveTraceExtractor(QObject):
    update_plot_signal = pyqtSignal()

    def __init__(self,
                 camera,
                 label_path,
                 plot_widget=None,
                 max_points=500,
                 max_rois=8,
                 use_pygame_plot=True):
        super().__init__()
        self.camera = camera
        self.use_pygame_plot = use_pygame_plot
        self.update_plot_signal.connect(self._update_plot)
        self.frame_queue = queue.Queue(maxsize=10)
        self.running = True

        # ─── FIRST, initialize Pygame if requested ───────────────────────────
        if self.use_pygame_plot:
            # initialize the SDL video system immediately
            pygame.init()
            self.screen_width, self.screen_height = 800, 600
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height)
            )
            pygame.display.set_caption("Live ROI Traces")
            self.clock = pygame.time.Clock()
        else:
            # (PyQtGraph setup)…
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
            labels = np.load(label_path)['labels']
            self.ids = np.unique(labels)
            for rid in self.ids:
                self.curves[rid] = pi.plot(pen=pg.mkPen(width=2),
                                            name=f"ROI {rid}")

        # ─── ONLY AFTER pygame (or pyqtgraph) window is ready,
        #        start the background thread ───────────────────────────
        self.worker_thread = threading.Thread(
            target=self._frame_processor,
            daemon=True
        )
        self.worker_thread.start()

        # … now load labels, build self.pix, etc. …
        labels = np.load(label_path)['labels']
        frame_h, frame_w = 1096, 1936
        if labels.shape != (frame_h, frame_w):
            print(f"⚠️ Resizing ROI labels from {labels.shape} to "
                  f"{(frame_h, frame_w)}")
            labels = cv2.resize(labels,
                                (frame_w, frame_h),
                                interpolation=cv2.INTER_NEAREST)
        self.check_labels = labels

        self.ids = np.unique(labels)
        self.ids = self.ids[self.ids > 0][:max_rois]
        flat_labels = labels.ravel()
        self.pix = [cp.asarray(np.flatnonzero(flat_labels == rid))
                    for rid in self.ids]
        self.buffers = {rid: deque(maxlen=max_points) for rid in self.ids}

        # Only now connect to camera frames:
        camera.frame_ready.connect(self.on_frame)


    def on_frame(self, frame):
        try:
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass

    @staticmethod
    def generate_colors(n):
        return [tuple(int(c * 255) for c in colorsys.hsv_to_rgb(i / n, 1.0, 1.0)) for i in range(n)]



    def _update_plot(self):
        if not pygame.display.get_init():
            return

        if self.use_pygame_plot:
            self.screen.fill((0, 0, 0))
            # colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
            colors = self.generate_colors(len(self.ids))

            font = pygame.font.SysFont("Arial", 14)
            margin = 50
            axis_color = (200, 200, 200)
            pygame.draw.line(self.screen, axis_color, (margin, margin), (margin, self.screen_height - margin), 2)  # Y axis
            pygame.draw.line(self.screen, axis_color, (margin, self.screen_height - margin), (self.screen_width - margin, self.screen_height - margin), 2)  # X axis
                    # Add Y-axis ticks and labels (Intensity)
            for i in range(0, 256, 50):
                y = int(self.screen_height - margin - i * ((self.screen_height - 2 * margin) / 255))
                pygame.draw.line(self.screen, axis_color, (margin - 5, y), (margin + 5, y), 1)
                label = font.render(str(i), True, axis_color)
                self.screen.blit(label, (5, y - 7))

            # Add X-axis ticks and labels (Frames ago)
            x_len = max((len(self.buffers[rid]) for rid in self.ids), default=1)
            for i in range(0, x_len, max(1, x_len // 10)):
                x = int(margin + i * ((self.screen_width - 2 * margin) / x_len))
                pygame.draw.line(self.screen, axis_color, (x, self.screen_height - margin - 5), (x, self.screen_height - margin + 5), 1)
                label = font.render(str(-x_len + i + 1), True, axis_color)
                self.screen.blit(label, (x - 10, self.screen_height - margin + 10))

            for idx, rid in enumerate(self.ids):
                y_vals = list(self.buffers[rid])
                if len(y_vals) < 2:
                    continue
                max_y = max(max(y_vals), 1)
                scale_x = (self.screen_width - 2 * margin) / len(y_vals)
                scale_y = (self.screen_height - 2 * margin) / max_y

                # Plot points
                points = [
                    (int(margin + i * scale_x), int(self.screen_height - margin - val * scale_y))
                    for i, val in enumerate(y_vals)
                ]
                pygame.draw.lines(self.screen, colors[idx % len(colors)], False, points, 2)

                label = f"ROI {rid}"
                
                text = font.render(label, True, colors[idx % len(colors)])
                self.screen.blit(text, (10, 20 * idx))  # Y offset to separate labels

                # y_vals = list(self.buffers[rid])
                # if len(y_vals) < 2:
                #     continue
                # max_y = max(max(y_vals), 1)
                # scale_x = self.screen_width / len(y_vals)
                # scale_y = self.screen_height / max_y
                # points = [
                #     (int(i * scale_x), int(self.screen_height - val * scale_y))
                #     for i, val in enumerate(y_vals)
                # ]
                # pygame.draw.lines(self.screen, colors[idx % len(colors)], False, points, 2)
            pygame.display.flip()
            self.clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop()
                    return
        else:
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
                continue

            try:
                if hasattr(frame, "get_numpy_1D"):
                    h, w = frame.Height(), frame.Width()
                    assert self.check_labels.shape == (h, w)
                    np_frame = np.array(frame.get_numpy_1D(), dtype=np.uint8).reshape((h, w, 4))
                    frame = np_frame[..., 0]
                elif isinstance(frame, np.ndarray):
                    if frame.ndim == 3 and frame.shape[2] == 3:
                        frame = frame[..., 0]
                    elif frame.ndim == 2:
                        pass
                    else:
                        raise ValueError("Unsupported frame format.")

                f_gpu = cp.asarray(frame.ravel(), dtype=cp.float32)
                for rid, mask_indices in zip(self.ids, self.pix):
                    if mask_indices.size == 0:
                        continue
                    try:
                        val = float(f_gpu[mask_indices].mean().get())
                        self.buffers[rid].append(val)
                    except Exception as e:
                        print(f"❌ Error computing mean for ROI {rid}: {e}")

                self.update_plot_signal.emit()
            except Exception as e:
                continue

    def export_traces(self, output_path="live_traces.npy", rois_path="rois.npz", last_n=100, max_rois=10):
        try:
            if len(self.ids) == 0 or not self.buffers or all(len(self.buffers[rid]) == 0 for rid in self.ids):
                print("❌ No ROI traces available for export.")
                return
            trace_matrix = np.stack([list(self.buffers[rid]) for rid in self.ids], axis=1)
            np.save(output_path, trace_matrix)
            print(f"✅ Traces exported to {output_path} — shape: {trace_matrix.shape}")
        except Exception as e:
            print(f"❌ Failed to export traces: {e}")

    def stop(self):
        self.running = False
        self.worker_thread.join(timeout=1.0)
        if hasattr(self.camera, "frame_ready"):
            self.camera.frame_ready.disconnect(self.on_frame)
        if self.use_pygame_plot:
            pygame.quit()