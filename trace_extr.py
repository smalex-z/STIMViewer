# # trace_extractor.py
# import os


# import cupy as cp, numpy as np, napari

# def extract_traces(memmap_path, curated_path, trace_path):
#     #movie = np.load('movie_mmap.npy', mmap_mode='r') # Load the mmap in read only mode
#     movie = np.load(memmap_path, mmap_mode='r')
#     # masks = np.load('rois_current.npz')['masks']  # Load the roi mask file 
#     masks = np.load(curated_path)['masks']

#     # Return 1-D array of every integer value that appears in the label image masks
#     ids  = np.unique(masks)[1:] # Skip label 0 which is the background
#     # Masks was a 2-D array where 0 is the background and 1-N is all the ROI IDs

#     # For each ROI label store a 1-D CuPy array of flattened indicies so we can grab them later
#     pix  = [cp.asarray(np.flatnonzero(masks.ravel()==i)) for i in ids]
#     # Masks.ravel flattens the 2-D mask into 1-d so the shape = H * W
#     # setting it to i is making the boolean mask by selecting pixels that belong to ROI i
#     # np.flatnonzero returns the flattened integer indicies of those true pixels
#     # Each element is converted to a cupy array so it lives on the GPU
#     # as a result pix[k] holds a 1-D index list for ROI ids[k]

#     T,H,W = movie.shape # unpack the dimensions of the movie to be T = frame count, H is image height and W is width
#     tr   = cp.zeros((len(ids),T), cp.float32) # allocate an output array one row per ROI and one column per fram on the GPU
#     # all entries start with 0 and are of float32 to keep consistent

#     # extract mean fluorescence per ROI per frame
#     for t in range(T): # loop per frame
#         f = cp.asarray(movie[t].ravel()) #movie[t] reads frame t as a 2-D numpy slice and ravel flattens it
#         # cp.asarray copies the 1-D array to the GPU as float32
#         for k, idx in enumerate(pix): # iterate over each ROI where k is the row index in tr idx is the CuPy index array from earlier
#             tr[k,t] = f[idx].mean() # f[idx] gathers all pixels that belong to ROI k in GPU memory .mean() computes the average intensity and stores it in tr[k, t]

#     # cp.save('traces_live.npy', tr) # save the traces as a .npy file 
#     cp.save(trace_path, tr)

#     # Simulate projecting the traces
#     # Launch a napari viewer window
#     view = napari.Viewer()
#     blank = np.zeros_like(movie[0]) # blank 2-d Array of with same shape and dtype as a frame 
#     blank[masks>0] = movie[0][masks>0] # copy the ROI pixels from frame 0 into blank while everything else is zero
#     # mimics how the DMD would only illuminate just the ROIs we selected
#     view.add_image(blank, name='proj', contrast_limits=(0,blank.max()))
#     # display the masked image
#     napari.run()

