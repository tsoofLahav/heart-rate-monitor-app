import heartpy as hp
import numpy as np


def detect_pulse(intensities, fps):
    """
    Process the PPG signal to detect peaks and calculate BPM.

    Parameters:
    - intensities: List or array of PPG signal intensities.
    - fps: Frames per second of the video (sampling frequency).

    Returns:
    - peaks: Indices of detected peaks in the signal.
    - bpm: Calculated beats per minute.
    - not_reading: Boolean indicating if the signal is too noisy or unreadable.
    - normalized_intensities: The normalized PPG signal.
    - time_stamps: Time stamps corresponding to each intensity value.
    """

    # Convert intensities to a numpy array
    intensities = np.array(intensities)

    # Normalize the signal to zero mean and unit variance
    normalized_intensities = (intensities - np.mean(intensities)) / np.std(intensities)

    # Generate time stamps based on the sampling frequency
    time_stamps = np.arange(len(normalized_intensities)) / fps

    try:
        # Process the signal with HeartPy
        wd, m = hp.process(normalized_intensities, sample_rate=fps)

        # Extract peak indices
        peaks = wd['peaklist']

        # Extract calculated BPM
        bpm = m['bpm']

        # Determine if the signal is readable based on Heart.py's 'is_good' flag
        not_reading = not wd['is_good']

    except Exception as e:
        # In case of an error (e.g., too noisy signal), set defaults
        peaks = []
        bpm = 0
        not_reading = True

    return peaks, bpm, not_reading, normalized_intensities.tolist(), time_stamps.tolist()
