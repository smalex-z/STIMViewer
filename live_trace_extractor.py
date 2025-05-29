# live_trace_extractor.py
import os


import numpy as np
import cupy as cp
import pyqtgraph as pg
from collections import deque

class LiveTraceExtractor:
    def __init__(self, camera, label_path, plot_widget: pg.PlotWidget, max_points=500):
        """
        camera         – your Camera instance
        label_path     – path to rois_current.npz (must contain 'labels')
        plot_widget    – a pyqtgraph PlotWidget already placed in your UI
        max_points     – how many most recent frames to show
        """
        # load & prep ROIs
        lab = np.load(label_path)['labels']
        self.ids = np.unique(lab)[1:]
        flat = lab.ravel()
        self.pix = [cp.asarray(np.flatnonzero(flat == rid)) for rid in self.ids]
        
        # pre-allocate GPU traces
        self.traces_gpu = None  # we’ll allocate per-frame if we want full movie
        # but for live plotting we keep only a sliding window:
        self.buffers = {rid: deque(maxlen=max_points) for rid in self.ids}
        
        # plotting
        self.plot = plot_widget
        # self.curves = {
        #     rid: self.plot.plot(pen=pg.mkPen(width=2)) for rid in self.ids
        # }
        # self.plot.addLegend()
        # for rid, curve in self.curves.items():
        #     self.plot.legend.addItem(curve, f"ROI {rid}")
        pi = self.plot.getPlotItem()
        pi.addLegend()
        vb = pi.getViewBox()
        vb.setMouseEnabled(x=True, y=True)
        # pi = self.plot.getPlotItem()
        pi.setLabel('left','Mean Intensity')
        pi.setLabel('bottom','Frames ago')
        pi.setYRange(0, 255)          # camera 8-bit range
        pi.setLimits(xMin=0, xMax=max_points)
        pi.enableAutoRange(axis='y', enable=False)
        pi.enableAutoRange(axis='x', enable=True)

        self.curves = {}
        for rid in self.ids:
            # plot *with* a name so the legend entry is created immediately
            curve = pi.plot(pen=pg.mkPen(width=2), name=f"ROI {rid}")
            self.curves[rid] = curve

        
        # hook camera
        camera._interface.on_image_received = self.on_frame

    def on_frame(self, frame: np.ndarray):
        """
        Called on *every* new frame. frame is H×W NumPy array.
        """
        f_gpu = cp.asarray(frame.ravel(), dtype=cp.float32)
        for rid, idx in zip(self.ids, self.pix):
            val = float(f_gpu[idx].mean().get())
            self.buffers[rid].append(val)
        
        self._update_plot()

    def _update_plot(self):
        """
        Refresh each curve with its current buffer.
        """
        for rid, curve in self.curves.items():
            y = list(self.buffers[rid])
            if not y:
                continue
            x = np.arange(len(y))
            curve.setData(x, y)
