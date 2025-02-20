import numpy as np
from scipy.signal import butter, sosfilt, find_peaks, welch


# Moving average filter
def moving_average_filter(data, window_size):
    return np.convolve(data, np.ones(window_size) / window_size, mode='same')


def normalize_signal(signal):
    """Normalize signal to have mean 0 and unit variance."""
    return (signal - np.mean(signal)) / np.std(signal)


def bandpass_filter(signal, fps, lowcut=0.7, highcut=4.0, order=2):
    """Apply a Butterworth band-pass filter to isolate heart rate frequency range."""
    nyquist = 0.5 * fps
    low = lowcut / nyquist
    high = highcut / nyquist
    sos = butter(order, [low, high], btype="band", output="sos")

    filtered_signal = sosfilt(sos, signal)

    # Normalize to maintain peak amplitudes relative to original signal
    filtered_signal = (filtered_signal - np.mean(filtered_signal)) / np.std(filtered_signal)

    return filtered_signal


def detect_peaks(signal, fps, min_bpm=40, max_bpm=200):
    """
    Detect peaks in a PPG signal using adaptive thresholding.

    Parameters:
        signal (array-like): Processed PPG signal.
        fps (float): Frames per second of the video.
        min_bpm (int): Minimum expected heart rate.
        max_bpm (int): Maximum expected heart rate.

    Returns:
        peaks (array): Indices of detected peaks.
    """
    # Convert BPM range to sample distance
    min_gap = 60 / max_bpm  # Smallest expected time between beats (sec)
    max_gap = 60 / min_bpm  # Largest expected time between beats (sec)

    min_distance = int(min_gap * fps)  # Convert to frames
    max_distance = int(max_gap * fps)

    # Adaptive Prominence Based on Filtered Signal Amplitude
    signal_std = np.std(signal)
    signal_mean = np.mean(signal)

    prominence = 0.8 * signal_std  # Dynamically adapt prominence
    height = signal_mean + 0.6 * signal_std  # Adaptive height threshold

    # Peak detection with adaptive prominence & height
    peaks, _ = find_peaks(signal, distance=min_distance, prominence=prominence, height=height)

    return peaks

def detect_unstable_reading(raw_signal, fps, min_variation=5, max_variation=250, max_jump=50, freq_range=(0.7, 4.0)):
    """
    Detect unstable readings based on amplitude, sudden jumps, peak-to-peak variability, and frequency analysis.

    Parameters:
    - raw_signal: The raw intensity signal (before filtering/normalization).
    - fps: Frames per second.
    - min_variation: Minimum allowed intensity variation (to avoid too weak signals).
    - max_variation: Maximum allowed intensity variation (to detect saturation).
    - max_jump: Maximum allowed sudden change between frames.
    - freq_range: Expected heart rate frequency range in Hz (default 0.7–4 Hz).

    Returns:
    - Boolean: True if unstable, False if stable.
    """
    if len(raw_signal) < 2:
        return True  # Too short to analyze

    # Amplitude variation check (signal too weak or too strong)
    signal_range = np.max(raw_signal) - np.min(raw_signal)
    if signal_range < min_variation or signal_range > max_variation:
        return True

    # Sudden large jumps detection
    diffs = np.abs(np.diff(raw_signal))
    if np.max(diffs) > max_jump:
        return True

    # Peak-to-peak variability check
    peaks = np.diff(np.where(raw_signal > np.mean(raw_signal))[0])
    if len(peaks) > 1 and (np.std(peaks) / np.mean(peaks)) > 0.5:  # High variability
        return True

    # Frequency analysis to check if dominant frequency is in expected range
    freqs, power = welch(raw_signal, fs=fps, nperseg=min(len(raw_signal), 256))
    dominant_freq = freqs[np.argmax(power)]
    if not (freq_range[0] <= dominant_freq <= freq_range[1]):
        return True

    return False  # Signal is stable



