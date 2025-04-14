import numpy as np
import imageio
from numpy.random import default_rng
from scipy.stats import multivariate_normal
from scipy.ndimage import gaussian_filter1d

rng = default_rng() # Initialize a random number generator

def generate_markov_spikes(num_frames: int, P: np.ndarray):
    """
    Generate a 1D spike train using a two-state Markov chain.
    
    Parameters
    ----------
    num_frames : int
        Number of timepoints/frames to simulate.
    P : np.ndarray of shape (2, 2)
        Transition matrix, where P[i, j] is the probability of transitioning
        from state i to state j.
    P: A 2×2 transition probability matrix. P[i, j] = probability of moving from state i (0 or 1) 
    to state j (0 or 1) on the next time step.
    Returns
    -------
    spikes : np.ndarray
        A binary spike train of length num_frames.
    """
    assert P.shape == (2, 2), "Transition matrix must be 2x2."
    assert np.allclose(P.sum(axis=1), 1), "Each row of P must sum to 1."
    
    while True:
        spikes = np.zeros(num_frames, dtype=int)
        for i in range(1, num_frames):
            spikes[i] = rng.choice([0, 1], p=P[spikes[i-1], :])
        if spikes.sum() > 0:  # ensure at least one spike
            break
    return spikes

def ar2_coeffs(tau_decay: float, tau_rise: float):
    """
    Convert exponential decay/rise constants (tau_decay, tau_rise)
    into AR(2) coefficients. A simplified formula:
        z1 = exp(-1/tau_decay), z2 = exp(-1/tau_rise)
        theta1 = z1 + z2, theta2 = -z1*z2
    """
    z1 = np.exp(-1.0 / tau_decay)
    z2 = np.exp(-1.0 / tau_rise)
    return z1 + z2, -z1 * z2

def apply_ar2_filter(spikes: np.ndarray, theta: tuple[float, float]):
    """
    Filter a binary spike train with an AR(2) model given by two coefficients.
    The model: C[n] = spikes[n] + theta1*C[n-1] + theta2*C[n-2].
    
    Returns the calcium trace.
    """
    theta1, theta2 = theta
    C = np.zeros_like(spikes, dtype=float)
    for i in range(len(spikes)):
        if i == 0:
            C[i] = spikes[i]
        elif i == 1:
            C[i] = spikes[i] + theta1*C[i-1]
        else:
            C[i] = spikes[i] + theta1*C[i-1] + theta2*C[i-2]
    return C

def bi_exp_filter(spikes: np.ndarray, tau_decay: float, tau_rise: float):
    """
    Convolve binary spikes with a difference of exponentials kernel:
        kernel(t) = exp(-t/tau_decay) - exp(-t/tau_rise)
    """
    # Build kernel
    length = len(spikes)
    t = np.arange(length)
    kernel = np.exp(-t / tau_decay) - np.exp(-t / tau_rise)
    # Convolve
    conv = np.convolve(spikes, kernel, mode='full')[:length]
    return conv

def random_motion(num_frames: int, max_shift: int = 5, smoothing: float = 2.0):
    """
    Generate random 2D integer shifts (x, y) for each frame, optionally smoothed.
    """
    # Create random walk in 2D
    raw_shifts = rng.normal(0, max_shift / 3, size=(num_frames, 2))
    # Smooth
    for dim in range(2):
        raw_shifts[:, dim] = gaussian_filter1d(raw_shifts[:, dim], smoothing)
    # Round to integer
    return np.round(raw_shifts).astype(int)

def shift_frame(frame2d: np.ndarray, shift: tuple[int, int], fill=0):
    """
    Shift a single 2D frame by (dy, dx). Outside region filled with 'fill'.
    """
    dy, dx = shift
    shifted = np.full_like(frame2d, fill, dtype=frame2d.dtype)
    
    # Compute valid slice
    h, w = frame2d.shape
    y_start = max(0, dy)
    y_end   = min(h, h + dy) 
    x_start = max(0, dx)
    x_end   = min(w, w + dx)
    
    src_y_start = max(0, -dy)
    src_y_end   = src_y_start + (y_end - y_start)
    src_x_start = max(0, -dx)
    src_x_end   = src_x_start + (x_end - x_start)
    
    shifted[y_start:y_end, x_start:x_end] = frame2d[src_y_start:src_y_end, src_x_start:src_x_end]
    return shifted

def generate_gaussian_footprint(height: int, width: int, center: tuple[int,int],
                                sigma_y: float, sigma_x: float, normalize=True):
    """
    Create a 2D Gaussian footprint at 'center' with standard deviations
    sigma_y and sigma_x.
    """
    yy, xx = np.mgrid[:height, :width]
    cov = np.array([[sigma_y**2, 0], [0, sigma_x**2]])
    rv = multivariate_normal(mean=center, cov=cov)
    footprint = rv.pdf(np.dstack([yy, xx]))
    if normalize:
        footprint -= footprint.min()
        footprint /= (footprint.max() + 1e-12)
    return footprint

def generate_synthetic_calcium_movie(
    num_cells=45,
    num_frames=200,
    height=512,
    width=512,
    spike_transition_matrix=None,
    tau_decay=10.0,
    tau_rise=4.0,
    use_ar2=True,
    cell_snr=5.0,
    background_strength=0.1,
    motion_smoothing=5.0,
    max_shift=0,
    noise_sigma=5.0,
):
    """
    Generate a synthetic calcium imaging movie.

    Parameters
    ----------
    num_cells : int
        Number of cells to simulate.
    num_frames : int
        Number of frames (time points).
    height, width : int
        Spatial dimensions of each frame.
    spike_transition_matrix : np.ndarray or None
        2x2 transition matrix for spike generation. If None, use a default.
    tau_decay, tau_rise : float
        Time constants (in frames) for either AR(2) conversion or bi-exponential filter.
    use_ar2 : bool
        If True, use an AR(2) model. If False, use a difference-of-exponentials model.
    cell_snr : float
        Scalar controlling amplitude of cell signals relative to background.
    background_strength : float
        Base background intensity added to all pixels, in approximate [0,1].
    motion_smoothing : float
        Gaussian filter sigma for random motion smoothing.
    max_shift : int
        Approximate scale for random motion (pixels).
    noise_sigma : float
        Std dev of Gaussian noise added to the final frames.

    Returns
    -------
    movie : np.ndarray, shape (num_frames, height, width)
        Simulated calcium imaging movie (8-bit).
    cell_masks : np.ndarray, shape (num_cells, height, width)
        The 2D Gaussian footprint for each cell.
    cell_traces : np.ndarray, shape (num_cells, num_frames)
        The calcium time course for each cell (before motion / scaling).
    spikes : np.ndarray, shape (num_cells, num_frames)
        The underlying spike trains for each cell.
    motion_shifts : np.ndarray, shape (num_frames, 2)
        The integer (dy, dx) shift for each frame.
    """
    if spike_transition_matrix is None:
        # Example: P = [[p_stay_off, p_switch_on],
        #               [p_switch_off, p_stay_on]]
        # Usually a fairly small chance of switching to on, etc.
        spike_transition_matrix = np.array([[0.98, 0.02],
                                            [0.02, 0.98]])
    
    # Pre-allocate
    movie = np.zeros((num_frames, height, width), dtype=np.float32)
    cell_masks = np.zeros((num_cells, height, width), dtype=np.float32)
    cell_traces = np.zeros((num_cells, num_frames), dtype=np.float32)
    spikes_all = np.zeros((num_cells, num_frames), dtype=np.int32)
    
    # Generate random motion for each frame
    motion_shifts = random_motion(num_frames, max_shift=max_shift, smoothing=motion_smoothing)
    
    # 1) Create cell footprints (2D Gaussians)
    for i in range(num_cells):
        # Random center within image, with some padding
        center_y = rng.integers(low=5, high=height-5)
        center_x = rng.integers(low=5, high=width-5)
        # Random sizes (some variation)
        sy = rng.uniform(3, 4.0)
        sx = rng.uniform(3, 4.0)
        
        footprint = generate_gaussian_footprint(height, width, (center_y, center_x),
                                                sy, sx, normalize=True)
        cell_masks[i] = footprint

    # 2) Generate spike trains and corresponding calcium signals
    for i in range(num_cells):
        spikes = generate_markov_spikes(num_frames, spike_transition_matrix)
        spikes_all[i] = spikes
        
        if use_ar2:
            # AR(2) approach
            theta = ar2_coeffs(tau_decay, tau_rise)
            trace = apply_ar2_filter(spikes, theta)
        else:
            # Bi-exponential approach
            trace = bi_exp_filter(spikes, tau_decay, tau_rise)
        
        cell_traces[i] = trace
    
    # 3) Combine footprints × traces to get raw (no-motion) movie
    # Accumulate each cell’s contribution
    for i in range(num_cells):
        # Outer product: time trace vs. spatial footprint
        # We'll scale each cell by "cell_snr" to get a noticeable amplitude
        for t in range(num_frames):
            movie[t] += cell_traces[i, t] * cell_masks[i]
    
    # 4) Add baseline background
    movie += background_strength
    
    # 5) Apply random motion shifts, frame by frame
    moved_movie = np.zeros_like(movie)
    for t in range(num_frames):
        shifted = shift_frame(movie[t], shift=motion_shifts[t], fill=background_strength)
        moved_movie[t] = shifted
    
    # 6) Add Gaussian noise
    noise = rng.normal(loc=0, scale=noise_sigma, size=moved_movie.shape)
    moved_movie += noise
    
    # 7) Clip/scale to 8-bit
    moved_movie = np.clip(moved_movie, 0, 255).astype(np.uint8)
    
    return moved_movie, cell_masks, cell_traces, spikes_all, motion_shifts

# ---------------------
# Example usage:
if __name__ == "__main__":
    synthetic_movie, masks, traces, spikes, motion = generate_synthetic_calcium_movie(
        num_cells=60,
        num_frames=500,
        height=512,
        width=512,
        tau_decay=15.0,
        tau_rise=5.0,
        use_ar2=True,
        cell_snr=5.0,
        background_strength=0.3,
        motion_smoothing=5.0,
        max_shift=0,
        noise_sigma=1.0,
    )
    
    print("Synthetic movie shape:", synthetic_movie.shape)  # (300, 64, 64)

    # Now save the movie as an MP4
    import imageio
    # The function expects frames in (frames, height, width, channels).
    # So we add a dummy channel axis for grayscale.
    movie_4d = synthetic_movie[..., None]  # shape: (300, 64, 64, 1)

    imageio.mimwrite(
    "synthetic_calcium_movie.mp4",
    movie_4d,
    fps=30,

)


    print("MP4 video saved as 'synthetic_calcium_movie.mp4'.")