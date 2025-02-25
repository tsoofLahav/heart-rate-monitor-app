import numpy as np
from scipy.signal import butter, filtfilt, sosfilt
import heartpy as hp


def bandpass_filter(intensities, fps, lowcut=0.5, highcut=3.0, order=2):
    """
    Apply a bandpass filter to the PPG signal and detect peaks.

    Parameters:
    - intensities: List or array of PPG signal intensities.
    - fps: Frames per second of the video (sampling frequency).
    - lowcut: Lower cutoff frequency (default 0.5 Hz for heart rate).
    - highcut: Upper cutoff frequency (default 3.0 Hz).
    - order: Order of the filter (default 2).

    Returns:
    - filtered_signal: The filtered PPG signal.
    - peaks: Indices of detected peaks.
    """
    # Convert to numpy array
    intensities = np.array(intensities)

    # Design Butterworth bandpass filter using second-order sections (sos)
    nyquist = 0.5 * fps
    low = lowcut / nyquist
    high = highcut / nyquist
    sos = butter(order, [low, high], btype='band', output='sos')

    # Apply filter using sosfiltfilt (zero-phase filtering)
    filtered_signal = sosfilt(sos, intensities)

    return filtered_signal.tolist()
