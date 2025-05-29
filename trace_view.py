# import os
# import os



# # 
# # 

# import os, sys, time, numpy as np, cupy as cp, napari
# import matplotlib.pyplot as plt
# from otsu_thresh import load_movie, compute_mean_projection

# def view_traces(trace_path):
#     # ---- sanity checks ----------------------------------------------------------
#     if not os.path.exists("rois.npz"):
#         sys.exit("❌  No rois.npz found.  Run roi_editor.py and press Export.")
#     # Checks if the user first ran roi_editor.py which would generate rois_current.npz for the ROIs they selected

#     # ---- load movie & label map -------------------------------------------------
#     lab = np.load("rois.npz")["labels"].astype(int)     # (H,W)
#     # Loads compressed labels map and extracts the 2-D label image  ensures is integer dtype int
#     ids = np.unique(lab)[1:] # Ensures every integer is non-zero so it excludes the background
#     if ids.size == 0: # makes sure the mask has ROIs
#         sys.exit("❌  Exported mask contains zero ROIs.")

#     # movie: load as a mem-map so we don’t blow RAM
#     mem = np.load("movie_mmap.npy", mmap_mode="r")              # (T,H,W)
#     T, H, W = mem.shape # extract dimensions
#     assert lab.shape == (H, W), "Label map shape mismatch with movie frame."
#     # make sure the height and width match with the initial movie

#     # ---- GPU trace extraction ---------------------------------------------------
#     # once per ROI build a flattened list of pixel indicies on the GPU
#     pix_lists = [cp.asarray(np.flatnonzero(lab.ravel() == i)) for i in ids]
#     # ravel flattens to a 1-D H W
#     # set boolean mask with lab.ravel() = i
#     # return 1-D array of integer indicies
#     # cp.asarray copies that array to device memory
#     traces_gpu = cp.zeros((len(ids), T), dtype=cp.float32)
#     # pre-allocate an output array on the GPU rows = ROIs columns = frames intialized as 0

#     t0 = time.perf_counter() # start a timer
#     for t in range(T): # For every frame
#         fr = cp.asarray(mem[t].ravel())  # use mem[t] as a 2-D numpy slices
#         # use rvel to flatten and cp.asarray to copy to the cpu once for that frame
#         for k, idx in enumerate(pix_lists): # loop over ROIs per frame fr[idx] indexes the flattened frame
#             # yields all pixels inside ROI use .mean for a reduction
#             traces_gpu[k, t] = fr[idx].mean() # store into traces_gpu
#     dt = time.perf_counter() - t0 # stop timer
#     print(f"✅  Extracted {len(ids)} traces in {dt:.1f} s")
#     # go back to cpu by transfering the entire 2-d array
#     traces = cp.asnumpy(traces_gpu)              # back to CPU
#     #np.save("traces_live.npy", traces)
#     np.save(trace_path, traces)
#     print("💾  Saved traces_live.npy  →  shape", traces.shape)
#     # save live traces
#     # ---- quick preview plot -----------------------------------------------------
#     # Plot and view the traces
#     plt.figure(figsize=(6,3))
#     plt.plot(traces.T)
#     plt.xlabel("frame"); plt.ylabel("mean pyqtSignal")
#     plt.title("Extracted traces (preview)")
#     plt.tight_layout()
#     plt.show()

#     # ---- build overlay for Napari ----------------------------------------------
#     # Stream the 5400 frames of the video maybe do more if nano can handle it
#     mean_img = compute_mean_projection(load_movie("synthetic_calcium_movie (1).mp4"), calib_frames=5400)
#     # launch blank napari window
#     viewer = napari.Viewer()
#     viewer.add_image(mean_img, name="mean", colormap="gray", blending="additive")
#     # add the mean image layer as grayscale background
#     # # add the ROI labels as an overlay
#     lbl_layer = viewer.add_labels(lab, name="chosen ROIs", opacity=0.6)
#     lbl_layer.color = {i: 'magenta' for i in ids}   # uniform magenta color for each ROI
#     viewer.camera.zoom = 0.5                        # start zoomed out
#     napari.run()
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

def view_traces(trace_path, rois_path="rois.npz", last_n=5):
    # sanity checks
    if not os.path.exists(rois_path):
        sys.exit("❌ No rois.npz found. Run ROI discovery/refinement first.")
    if not os.path.exists(trace_path):
        sys.exit(f"❌ No trace file found at {trace_path}")

    # load label map & ROI IDs
    lab = np.load(rois_path)["labels"].astype(int)
    ids = np.unique(lab)[1:]
    if ids.size == 0:
        sys.exit("❌ ROI mask contains zero ROIs.")

    # load the rolling‐trace array (T × N_rois or N_rois × T)
    traces = np.load(trace_path)
    # ensure shape is (T, N)
    if traces.shape[0] < traces.shape[-1]:
        traces = traces.T

    T, N = traces.shape
    if last_n > T:
        last_n = T

    # slice out the last `last_n` frames
    last_block = traces[-last_n:, :]  # shape (last_n, N)

    # build X axis: frames ago (0 = newest, -last_n+1 = oldest)
    x = np.arange(-last_n + 1, 1, 1)

    # quick preview
    plt.figure(figsize=(12, 6))
    for idx, rid in enumerate(ids[:N]):
        plt.plot(x, last_block[:, idx], label=f"ROI {rid}")
    plt.xlabel("Frames ago")
    plt.ylabel("Mean intensity")
    plt.title(f"Live Traces (last {last_n} frames)")
    plt.legend(loc="upper right", ncol=2, fontsize="small")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
