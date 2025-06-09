import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks
from classifier import classify_signal_segment
from reconstruction import reconstruct_missing


def butter_bandpass_filter(signal, fs, lowcut=0.8, highcut=3.0, order=6):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def regularize_signal(signal):
    """Normalize the signal to have mean 0 and std 1."""
    mean = np.mean(signal)
    std = np.std(signal)
    return (signal - mean) / (std + 1e-8)  # Avoid division by zero


def denoise_ppg(raw_signal, fs):
    """
    Denoise PPG signal, detect if it's readable, and find peaks.

    Args:
        raw_signal (list or np.array): 10 second raw PPG signal.
        fs (int): Frames per second.

    Returns:
        clean_signal (np.array): Cleaned or reconstructed signal.
        filtered_signal (np.array): Bandpass-filtered signal.
        not_reading (bool): Whether the signal is unreadable.
        peaks (list): Detected peaks (absolute times in seconds).
    """
    raw_signal = np.array(raw_signal)

    # Step 1: Bandpass Filter
    filtered_signal = butter_bandpass_filter(raw_signal, fs)

    # Step 2: Regularization
    normalized_signal = regularize_signal(filtered_signal)

    # Step 3: Classification of 2-second segments
    window_size = int(2 * fs)
    num_windows = len(normalized_signal) // window_size

    classifications = []
    for i in range(num_windows):
        start = i * window_size
        end = start + window_size
        segment = normalized_signal[start:end]
        label = classify_signal_segment(segment)  # 0 = bad, 1 = good
        classifications.append((i, label))

    # Step 4: Decision Logic
    bad_windows = [i for i, label in classifications if label == 0]

    if len(bad_windows) >= 2:
        return None, filtered_signal, True, []

    if len(bad_windows) == 1:
        bad_window = bad_windows[0]
        bad_start_sec = bad_window * 2

        if bad_start_sec >= 4:
            start = bad_window * window_size
            end = start + window_size

            # Zero out bad part
            corrupted_signal = normalized_signal.copy()
            corrupted_signal[start:end] = 0.0

            # Reconstruct
            reconstructed_segment = reconstruct_missing(corrupted_signal)

            # Replace
            normalized_signal[start:end] = reconstructed_segment[start:end]

    # Step 5: Peak Detection
    peak_indices, _ = find_peaks(normalized_signal, distance=int(0.3 * fs), height=0)  # >300ms between beats
    peak_times = (np.array(peak_indices) / fs).tolist()

    return normalized_signal, filtered_signal, False, peak_times
