import os
import os



# 
# 

import os, sys, time, numpy as np, cupy as cp, napari
import matplotlib.pyplot as plt
from otsu_thresh import load_movie, compute_mean_projection

def view_traces(trace_path):
    # ---- sanity checks ----------------------------------------------------------
    if not os.path.exists("rois_current.npz"):
        sys.exit("❌  No rois_current.npz found.  Run roi_editor.py and press Export.")
    # Checks if the user first ran roi_editor.py which would generate rois_current.npz for the ROIs they selected

    # ---- load movie & label map -------------------------------------------------
    lab = np.load("rois_current.npz")["labels"].astype(int)     # (H,W)
    # Loads compressed labels map and extracts the 2-D label image  ensures is integer dtype int
    ids = np.unique(lab)[1:] # Ensures every integer is non-zero so it excludes the background
    if ids.size == 0: # makes sure the mask has ROIs
        sys.exit("❌  Exported mask contains zero ROIs.")

    # movie: load as a mem-map so we don’t blow RAM
    mem = np.load("movie_mmap.npy", mmap_mode="r")              # (T,H,W)
    T, H, W = mem.shape # extract dimensions
    assert lab.shape == (H, W), "Label map shape mismatch with movie frame."
    # make sure the height and width match with the initial movie

    # ---- GPU trace extraction ---------------------------------------------------
    # once per ROI build a flattened list of pixel indicies on the GPU
    pix_lists = [cp.asarray(np.flatnonzero(lab.ravel() == i)) for i in ids]
    # ravel flattens to a 1-D H W
    # set boolean mask with lab.ravel() = i
    # return 1-D array of integer indicies
    # cp.asarray copies that array to device memory
    traces_gpu = cp.zeros((len(ids), T), dtype=cp.float32)
    # pre-allocate an output array on the GPU rows = ROIs columns = frames intialized as 0

    t0 = time.perf_counter() # start a timer
    for t in range(T): # For every frame
        fr = cp.asarray(mem[t].ravel())  # use mem[t] as a 2-D numpy slices
        # use rvel to flatten and cp.asarray to copy to the cpu once for that frame
        for k, idx in enumerate(pix_lists): # loop over ROIs per frame fr[idx] indexes the flattened frame
            # yields all pixels inside ROI use .mean for a reduction
            traces_gpu[k, t] = fr[idx].mean() # store into traces_gpu
    dt = time.perf_counter() - t0 # stop timer
    print(f"✅  Extracted {len(ids)} traces in {dt:.1f} s")
    # go back to cpu by transfering the entire 2-d array
    traces = cp.asnumpy(traces_gpu)              # back to CPU
    #np.save("traces_live.npy", traces)
    np.save(trace_path, traces)
    print("💾  Saved traces_live.npy  →  shape", traces.shape)
    # save live traces
    # ---- quick preview plot -----------------------------------------------------
    # Plot and view the traces
    plt.figure(figsize=(6,3))
    plt.plot(traces.T)
    plt.xlabel("frame"); plt.ylabel("mean pyqtSignal")
    plt.title("Extracted traces (preview)")
    plt.tight_layout()
    plt.show()

    # ---- build overlay for Napari ----------------------------------------------
    # Stream the 5400 frames of the video maybe do more if nano can handle it
    mean_img = compute_mean_projection(load_movie("cropped.avi"), calib_frames=5400)
    # launch blank napari window
    viewer = napari.Viewer()
    viewer.add_image(mean_img, name="mean", colormap="gray", blending="additive")
    # add the mean image layer as grayscale background
    # # add the ROI labels as an overlay
    lbl_layer = viewer.add_labels(lab, name="chosen ROIs", opacity=0.6)
    lbl_layer.color = {i: 'magenta' for i in ids}   # uniform magenta color for each ROI
    viewer.camera.zoom = 0.5                        # start zoomed out
    napari.run()


# import sys
# import os
# import numpy as np
# import cupy as cp
# from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QSplitter
# from PyQt5.QtCore import Qt
# import pyqtgraph as pg
# from otsu_thresh import load_movie, compute_mean_projection

# def view_traces_pyqtgraph(trace_path: str, mean_source: str = None, calib_frames: int = 5400):
#     """
#     Load and display ROI fluorescence traces and a projection overlay using PyQt5 + PyQtGraph.

#     Parameters
#     ----------
#     trace_path : str
#         Path to the NumPy .npy file containing traces array of shape (N_rois, T_frames).
#     mean_source : str, optional
#         Path to the raw movie file for computing mean projection; if None, skips projection display.
#     calib_frames : int
#         Number of frames to average when computing the mean projection.
#     """
#     # ---- Load traces ----
#     if not os.path.exists(trace_path):
#         raise FileNotFoundError(f"Trace file not found: {trace_path}")
#     traces = np.load(trace_path)  # shape: (N, T)
#     num_rois, num_frames = traces.shape

#     # ---- Create Qt Application ----
#     app = QApplication.instance() or QApplication(sys.argv)

#     # ---- Main Window Setup ----
#     win = QWidget()
#     win.setWindowTitle("Trace Viewer")
#     layout = QVBoxLayout(win)

#     # ---- PlotWidget for Traces ----
#     trace_plot = pg.PlotWidget(title="ROI Fluorescence Traces")
#     trace_plot.setLabel('left', 'Mean Intensity')
#     trace_plot.setLabel('bottom', 'Frame')
#     for k in range(num_rois):
#         trace_plot.plot(np.arange(num_frames), traces[k], pen=pg.mkPen(width=1))
#     layout.addWidget(trace_plot)

#     # ---- ImageView for Projection ----
#     if mean_source is not None and os.path.exists(mean_source):
#         # Compute mean projection
#         movie = load_movie(mean_source)
#         mean_img = compute_mean_projection(movie, calib_frames=calib_frames)
#         # Overlay only ROI pixels
#         lbl = None
#         try:
#             labels = np.load(trace_path.replace('traces_live', 'rois_current'))['labels']
#             proj = np.zeros_like(mean_img)
#             proj[labels > 0] = mean_img[labels > 0]
#         except Exception:
#             proj = mean_img
#         img_view = pg.ImageView()
#         img_view.setImage(proj.astype(np.float32), autoLevels=True)
#         img_view.ui.histogram.hide()
#         img_view.ui.roiBtn.hide()
#         img_view.ui.menuBtn.hide()
#         layout.addWidget(img_view)

#     # ---- Show Window ----
#     win.show()

#     # ---- Execute Qt Loop ----
#     if not QApplication.instance().startingUp():
#         sys.exit(app.exec_())


# if __name__ == '__main__':
#     import argparse
#     parser = argparse.ArgumentParser(description='View ROI traces and projection.')
#     parser.add_argument('trace_path', help='Path to traces .npy file')
#     parser.add_argument('--movie', help='Path to raw movie for mean projection', default=None)
#     parser.add_argument('--frames', type=int, help='Calibration frames for mean', default=5400)
#     args = parser.parse_args()
#     view_traces_pyqtgraph(args.trace_path, args.movie, args.frames)
