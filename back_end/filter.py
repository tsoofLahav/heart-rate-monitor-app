import numpy as np
from fastdtw import fastdtw
from scipy.signal import butter, sosfiltfilt
from scipy.spatial.distance import euclidean


def butter_bandpass_filter(signal, fs, lowcut=0.5, highcut=5.0, order=4):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def lms_filter(noisy_signal, reference_signal, mu=0.05, num_taps=64):
    """Applies LMS adaptive filtering."""

    n = len(noisy_signal)
    w = np.zeros(num_taps)  # Adaptive filter weights
    filtered_signal = np.zeros(n)

    for i in range(num_taps, n):
        x = reference_signal[i - num_taps:i].flatten()  # Ensure 1D
        y = np.dot(w, x)  # Filter output
        e = noisy_signal[i] - y  # Error signal
        w += mu * e * x  # Weight update (LMS adaptation)
        filtered_signal[i] = y

    return filtered_signal.flatten()


def dtw_align(reference_signal, target_signal):
    """Aligns the target signal to the reference signal using Dynamic Time Warping (DTW)."""
    reference_signal = np.array(reference_signal).flatten()
    target_signal = np.array(target_signal).flatten()

    print("DTW Reference Signal Shape:", reference_signal.shape)
    print("DTW Target Signal Shape:", target_signal.shape)

    # Ensure all elements in DTW are treated as 1D scalars
    distance, path = fastdtw(reference_signal.tolist(), target_signal.tolist(),
                             dist=lambda x, y: euclidean(np.atleast_1d(x), np.atleast_1d(y)))

    aligned_signal = np.zeros(len(target_signal))

    for (i, j) in path:
        if i < len(reference_signal) and j < len(aligned_signal):  # Prevent index errors
            aligned_signal[j] = reference_signal[i]

    return aligned_signal.flatten()


def denoise_ppg(ppg_signal, fs, reference_signal):
    """Denoises PPG using DTW for alignment and LMS for adaptive filtering."""
    ppg_signal = np.array(ppg_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()
    reference_signal /= np.max(np.abs(reference_signal))
    ppg_signal /= np.max(np.abs(ppg_signal))

    # Step 1: Band-pass filter to remove unwanted noise
    filtered_signal = butter_bandpass_filter(ppg_signal, fs)

    # Step 2: Align with reference signal using DTW
    aligned_reference = dtw_align(reference_signal, filtered_signal)

    # Step 3: Apply LMS filtering for adaptive noise removal
    clean_signal = lms_filter(filtered_signal, aligned_reference)

    return clean_signal.flatten()
