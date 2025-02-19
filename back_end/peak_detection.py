import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks


# Moving average filter
def moving_average_filter(data, window_size):
    return np.convolve(data, np.ones(window_size) / window_size, mode='same')


def normalize_signal(signal):
    """Normalize signal to have mean 0 and unit variance."""
    return (signal - np.mean(signal)) / np.std(signal)


def bandpass_filter(signal, fps, lowcut=0.7, highcut=4.0, order=3):
    """Apply a Butterworth band-pass filter to isolate heart rate frequency range."""
    nyquist = 0.5 * fps
    low = lowcut / nyquist
    high = highcut / nyquist
    sos = butter(order, [low, high], btype="band", output="sos")
    return sosfiltfilt(sos, signal)


# Peak detection function
def detect_peaks(signal, fps, min_bpm=40, max_bpm=200, prominence=0.3):
    """
    Detect peaks in a PPG signal using adaptive thresholding.

    Parameters:
        signal (array-like): Processed PPG signal.
        fps (float): Frames per second of the video.
        min_bpm (int): Minimum expected heart rate.
        max_bpm (int): Maximum expected heart rate.
        prominence (float): Minimum prominence of peaks (adjust as needed).

    Returns:
        peaks (array): Indices of detected peaks.
    """
    # Convert BPM range to time (seconds per beat)
    min_gap = 60 / max_bpm
    max_gap = 60 / min_bpm

    # Convert to sample distance
    min_distance = int(min_gap * fps)
    max_distance = int(max_gap * fps)

    # Peak detection with prominence-based filtering
    peaks, _ = find_peaks(signal, distance=min_distance, prominence=prominence)

    return peaks


def detect_unstable_reading(filtered_signal, baseline, std_dev, std_threshold=1.5):
    #  If all values are (near) zero, mark as unstable
    if np.all(filtered_signal == 0) or baseline == 0:
        return True

    #  If standard deviation is too high, mark as unstable
    if std_dev > std_threshold * baseline:
        return True

    return False  # Otherwise, signal is stable
