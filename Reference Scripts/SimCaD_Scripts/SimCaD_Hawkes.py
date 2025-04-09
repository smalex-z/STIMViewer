import numpy as np
from numpy.random import default_rng
from scipy.stats import multivariate_normal
from scipy.ndimage import gaussian_filter1d

rng = default_rng()

def generate_hawkes_spikes(
    num_frames: int,
    mu: float = 0.01,
    alpha: float = 0.05,
    tau: float = 10.0
):
    """
    Generate a binary 1D spike train using a discrete-time Hawkes process.
    
    Each time bin i has intensity lambda_i = mu + sum over past spikes of 
        alpha * exp(-(i - k)/tau).
    We clamp lambda_i to 1.0 so it stays a valid probability in [0, 1].
    
    Parameters
    ----------
    num_frames : int
        Number of timepoints/frames to simulate.
    mu : float
        Baseline firing probability per frame (0 < mu < 1).
    alpha : float
        Strength of self-excitation added by a single spike.
    tau : float
        Time constant controlling how quickly excitation from past spikes decays.

    Returns
    -------
    spikes : np.ndarray
        A binary spike train of length num_frames (0 or 1).
    """
    while True:
        spikes = np.zeros(num_frames, dtype=int)
        
        for i in range(num_frames):
            # Baseline intensity
            lam_i = mu
            # Add exponential decays of past spikes
            for k in range(i):
                if spikes[k] == 1:
                    dt = i - k
                    lam_i += alpha * np.exp(-dt / tau)
            
            # Clamp to [0, 1]
            lam_i = min(lam_i, 1.0)
            
            # Draw a spike with probability lam_i
            if rng.random() < lam_i:
                spikes[i] = 1
        
        if spikes.sum() > 0:
            # Ensure at least one spike in the train
            break
    return spikes

def ar2_coeffs(tau_decay: float, tau_rise: float):
    """
    Convert time constants (tau_decay, tau_rise) into AR(2) coefficients.
    Coefficients (theta1, theta2):
        z1 = exp(-1/tau_decay), z2 = exp(-1/tau_rise)
        theta1 = z1 + z2
        theta2 = -z1 * z2
    """
    z1 = np.exp(-1.0 / tau_decay)
    z2 = np.exp(-1.0 / tau_rise)
    return z1 + z2, -z1 * z2

def apply_ar2_filter(spikes: np.ndarray, theta: tuple[float, float]):
    """
    Filter a binary spike train with an AR(2) model. 
    The update: C[n] = spikes[n] + theta1*C[n-1] + theta2*C[n-2].
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
    Convolve a spike train with a difference-of-exponentials:
        kernel(t) = exp(-t/tau_decay) - exp(-t/tau_rise).
    """
    length = len(spikes)
    t = np.arange(length)
    kernel = np.exp(-t / tau_decay) - np.exp(-t / tau_rise)
    conv = np.convolve(spikes, kernel, mode='full')[:length]
    return conv

def generate_gaussian_footprint(
    height: int,
    width: int,
    center: tuple[int, int],
    sigma_y: float,
    sigma_x: float,
    normalize: bool = True
):
    """
    Create a 2D Gaussian footprint at 'center' with std devs sigma_y, sigma_x.
    """
    yy, xx = np.mgrid[:height, :width]
    cov = np.array([[sigma_y**2, 0], [0, sigma_x**2]])
    rv = multivariate_normal(mean=center, cov=cov)
    footprint = rv.pdf(np.dstack([yy, xx]))
    if normalize:
        mn, mx = footprint.min(), footprint.max()
        if mx > mn:  # avoid divide-by-zero
            footprint = (footprint - mn) / (mx - mn)
        else:
            footprint = footprint - mn
    return footprint

def shift_frame(frame2d: np.ndarray, shift: tuple[int, int], fill=0):
    """
    Shift a single 2D frame by (dy, dx). 
    The region that "falls out" is filled with 'fill'.
    """
    dy, dx = shift
    h, w = frame2d.shape
    shifted = np.full_like(frame2d, fill, dtype=frame2d.dtype)
    
    # Dest coords
    y_start = max(0, dy)
    y_end   = min(h, h + dy)
    x_start = max(0, dx)
    x_end   = min(w, w + dx)
    
    # Source coords
    src_y_start = max(0, -dy)
    src_y_end   = src_y_start + (y_end - y_start)
    src_x_start = max(0, -dx)
    src_x_end   = src_x_start + (x_end - x_start)
    
    shifted[y_start:y_end, x_start:x_end] = frame2d[src_y_start:src_y_end,
                                                    src_x_start:src_x_end]
    return shifted

def random_motion(num_frames: int, max_shift: int = 5, smoothing: float = 2.0):
    """
    Generate random 2D integer shifts for each frame, optionally smoothed.
    """
    raw_shifts = rng.normal(0, max_shift / 3, size=(num_frames, 2))
    # Smooth
    for dim in range(2):
        raw_shifts[:, dim] = gaussian_filter1d(raw_shifts[:, dim], smoothing)
    # Round to integer
    return np.round(raw_shifts).astype(int)

def generate_synthetic_calcium_movie(
    num_cells=5,
    num_frames=200,
    height=64,
    width=64,
    # Hawkes parameters
    hawkes_mu=0.01,
    hawkes_alpha=0.05,
    hawkes_tau=10.0,
    # Calcium dynamics parameters
    tau_decay=20.0,
    tau_rise=5.0,
    use_ar2=True,
    # Cell footprint amplitude
    cell_snr=5.0,
    # Background
    background_strength=0.3,
    # Motion
    motion_smoothing=2.0,
    max_shift=5,
    # Noise
    noise_sigma=3.0
):
    """
    Generate a synthetic calcium imaging movie using a Hawkes process to generate spikes.
    
    Parameters
    ----------
    num_cells : int
        Number of cells to simulate.
    num_frames : int
        Number of frames (time points).
    height, width : int
        Spatial dimensions of each frame.
    hawkes_mu, hawkes_alpha, hawkes_tau : float
        Parameters controlling the discrete-time Hawkes process for spiking.
    tau_decay, tau_rise : float
        Time constants for AR(2) or bi-exponential filter.
    use_ar2 : bool
        If True, use AR(2) to generate calcium from spikes; else use a difference-of-exponentials.
    cell_snr : float
        Scalar controlling amplitude of cell signals relative to background.
    background_strength : float
        Base background intensity in frames, typically in [0,1].
    motion_smoothing : float
        Gaussian filter sigma for random motion smoothing.
    max_shift : int
        Approximate maximum shift (pixels) for motion.
    noise_sigma : float
        Std dev of Gaussian noise added to the final frames.

    Returns
    -------
    movie : np.ndarray, shape (num_frames, height, width)
        Simulated calcium imaging movie (8-bit).
    cell_masks : np.ndarray, shape (num_cells, height, width)
        The 2D Gaussian footprint for each cell.
    cell_traces : np.ndarray, shape (num_cells, num_frames)
        The calcium time course for each cell.
    spikes_all : np.ndarray, shape (num_cells, num_frames)
        The underlying spike trains for each cell.
    motion_shifts : np.ndarray, shape (num_frames, 2)
        The integer (dy, dx) shift for each frame.
    """
    # Allocate
    movie = np.zeros((num_frames, height, width), dtype=np.float32)
    cell_masks = np.zeros((num_cells, height, width), dtype=np.float32)
    cell_traces = np.zeros((num_cells, num_frames), dtype=np.float32)
    spikes_all = np.zeros((num_cells, num_frames), dtype=int)
    
    # Generate motion
    motion_shifts = random_motion(num_frames, max_shift=max_shift, smoothing=motion_smoothing)
    
    # Generate footprints
    for i in range(num_cells):
        # Random center with some padding
        cy = rng.integers(low=5, high=height-5)
        cx = rng.integers(low=5, high=width-5)
        # Random sizes -> smaller sigma => sharper edges
        sy = rng.uniform(3.0, 5.0)
        sx = rng.uniform(3.0, 5.0)
        
        footprint = generate_gaussian_footprint(height, width, (cy, cx),
                                                sy, sx, normalize=True)
        cell_masks[i] = footprint
    
    # Generate spikes with Hawkes, then create calcium traces
    for i in range(num_cells):
        # Hawkes-based spikes
        spikes = generate_hawkes_spikes(num_frames, 
                                        mu=hawkes_mu,
                                        alpha=hawkes_alpha,
                                        tau=hawkes_tau)
        spikes_all[i] = spikes
        
        # Now create a calcium trace from these spikes
        if use_ar2:
            # AR(2)
            theta = ar2_coeffs(tau_decay, tau_rise)
            trace = apply_ar2_filter(spikes, theta)
        else:
            # Bi-exponential
            trace = bi_exp_filter(spikes, tau_decay, tau_rise)
        
        cell_traces[i] = trace
    
    # Combine footprints × traces (raw, no motion yet)
    for i in range(num_cells):
        for t in range(num_frames):
            # Each cell is scaled by "cell_snr" to stand out from background
            movie[t] += cell_traces[i, t] * cell_masks[i] * cell_snr
    
    # Add background
    movie += background_strength
    
    # Apply motion
    moved_movie = np.zeros_like(movie)
    for t in range(num_frames):
        shifted = shift_frame(movie[t], shift=motion_shifts[t], fill=background_strength)
        moved_movie[t] = shifted
    
    # Add Gaussian noise
    noise = rng.normal(loc=0, scale=noise_sigma, size=moved_movie.shape)
    moved_movie += noise
    
    # Clip/scale to 8-bit
    moved_movie = np.clip(moved_movie, 0, 255).astype(np.uint8)
    
    return moved_movie, cell_masks, cell_traces, spikes_all, motion_shifts

# -----------------
# Example usage:
if __name__ == "__main__":
    synthetic_movie, masks, traces, spikes, motion = generate_synthetic_calcium_movie(
        num_cells=60,
        num_frames=300,
        height=512,
        width=512,
        # Hawkes parameters
        hawkes_mu=0.02,      # baseline probability
        hawkes_alpha=0.05,    # self-excitation strength
        hawkes_tau=10.0,     # decay timescale for excitation
        # Calcium dynamics
        tau_decay=10.0,
        tau_rise=5.0,
        use_ar2=True,
        # SNR, background
        cell_snr=5.0,
        background_strength=0.3,
        # Motion
        motion_smoothing=2.0,
        max_shift=0,
        # Noise
        noise_sigma=3.0,
    )
    
    print("Synthetic movie shape:", synthetic_movie.shape)  # (300, 64, 64)
    print("Cell footprints shape:", masks.shape)            # (10, 64, 64)
    print("Calcium traces shape:", traces.shape)            # (10, 300)
    print("Spikes shape:", spikes.shape)                    # (10, 300)
    print("Motion shifts shape:", motion.shape)             # (300, 2)
    
    # Example: Save to an MP4 (make sure you have imageio-ffmpeg installed)
    import imageio
    movie_4d = synthetic_movie[..., None]  # shape = (frames, height, width, 1)
    imageio.mimwrite("hawkes_synthetic_calcium_movie.mp4", movie_4d, fps=30)
    print("Saved to 'hawkes_synthetic_calcium_movie.mp4'.")
