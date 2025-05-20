# make_mmap.py  (run once per new movie)
# We use this to convert a the movie into a numpy array so we can later use it 
# To access frames from multiple processes without decoding the movie each time
import numpy as np
from otsu_thresh import load_movie

path = "cropped.avi"   # must be same file that main.py used
mov  = load_movie(path) # Use load movie which made it as an opencv video capture object

frames = [] # buffer for all frames
while True: # Checks if mov has a read() method which is True if it is a cv2.VideoCapture false if its h5py or np.memmap
    ret, fr = mov.read() if hasattr(mov, "read") else (False, None)
    # Calling mov.read() returns (ret, frame) where ret is a boolean and frame is the decoded image
    if not ret: break # Needs check if a cv2 video capture because load_movie might return object with direct indexing with HDF5 or numpy mem map instead of sequential frames
    if fr.ndim == 3: fr = fr[...,0] # frames come as 3-D array (H, W, 3) when we grab [...,0] it keeps the first channel (H, W) as a greyscale
    frames.append(fr.astype("float32")) # Appends each frame as float32 which is good from Gaussian 
np.save("movie_mmap.npy", np.stack(frames)) # save list of 2-D arrays into a single 3-D array with shape (n_frames, height, width) to access any frame wihtout loading the whole thing
print("Wrote movie_mmap.npy  →  shape", np.load("movie_mmap.npy").shape) # Re-open the full file into ram and print its shape