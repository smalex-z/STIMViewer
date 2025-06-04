from pathlib import Path
import os

# use an env-var override so you can change it without editing code again
SSD_ROOT = Path(os.getenv("STIM_DATA_DIR",
            "/media/aharonilabjetson2/NVMe/stimviewer_data")).expanduser()
SSD_ROOT.mkdir(parents=True, exist_ok=True)      # auto-create on first run

import numpy as np
from otsu_thresh import load_movie

def make_memmap(video_path, memmap_path):
    if not video_path:
        raise ValueError("video_path must be provided")
    mov = load_movie(video_path)

    frames = []
    while True:
        # cv2.VideoCapture has .read(); HDF5/numpy memmap won’t
        if hasattr(mov, "read"):
            ret, fr = mov.read()
        else:
            # (optional) handle h5py slicing here
            ret, fr = False, None

        if not ret:
            break

        # if color, pick first channel
        if fr.ndim == 3:
            fr = fr[..., 0]

        frames.append(fr.astype(np.float32))

    # Stack into (T, H, W)
    arr = np.stack(frames)

    # Save as plain .npy
    np.save(memmap_path, arr)

    # Report back
    loaded = np.load(memmap_path, mmap_mode='r')
    print(f"Wrote {memmap_path} → shape {loaded.shape}")
