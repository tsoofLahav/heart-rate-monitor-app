import numpy as np
from AdvEMDpy.AdvEMDpy import EMD


def detect_pulse(intensities, fps):
    """
    Decompose the PPG signal into Intrinsic Mode Functions (IMFs) using EMD.

    Parameters:
    - intensities: List or array of PPG signal intensities.
    - fps: Frames per second of the video (sampling frequency).

    Returns:
    - imfs: List of extracted IMFs.
    - time_stamps: List of time stamps corresponding to each intensity value.
    """

    # Convert intensities to a numpy array
    intensities = np.array(intensities)

    # Generate time stamps based on the sampling frequency
    time_stamps = np.arange(len(intensities)) / fps

    # Initialize EMD with time and signal data
    emd = EMD(time=time_stamps, time_series=intensities)

    # Perform EMD decomposition with default spline fitting
    imfs, _, _, _, _, _ = emd.empirical_mode_decomposition(knots=None, knot_time=None)

    return imfs.tolist(), time_stamps.tolist()
