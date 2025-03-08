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


def lms_filter(noisy_signal, reference_signal, mu=0.1, fps=30):
    """Applies LMS adaptive filtering with vector-based error and weights as a matrix."""
    num_taps = int(2 * fps)
    n = len(noisy_signal)
    w = np.zeros((num_taps, num_taps))  # Weight matrix for learning waveforms
    filtered_signal = np.zeros((n, num_taps))

    for i in range(num_taps, n):
        x = reference_signal[i - num_taps:i]  # Input window
        y = np.dot(w, x)  # Predicted waveform
        e = noisy_signal[i - num_taps:i] - y  # Error as a vector
        w += mu * np.outer(e, x)  # Update weight matrix using outer product
        filtered_signal[i] = y

    return np.sum(filtered_signal, axis=1)  # Sum across taps to get final output


def dtw_align(reference_signal, target_signal):
    """Aligns the target signal to the reference signal using DTW only for initial phase alignment."""
    reference_signal = np.array(reference_signal).flatten()
    target_signal = np.array(target_signal).flatten()

    # Add padding to target signal before DTW
    pad_length = len(reference_signal) - len(target_signal)
    if pad_length > 0:
        target_signal = np.concatenate((target_signal, np.zeros(pad_length)))

    print("DTW Reference Signal Shape:", reference_signal.shape)
    print("DTW Target Signal Shape:", target_signal.shape)

    # Run DTW only for start position alignment
    _, path = fastdtw(reference_signal.tolist(), target_signal.tolist(),
                      dist=lambda x, y: euclidean(np.atleast_1d(x), np.atleast_1d(y)))
    start_shift = path[0][0] - path[0][1]  # Get initial alignment shift
    reference_signal = np.roll(reference_signal, -start_shift)  # Shift reference

    # Remove the wrap-around part from the end
    if start_shift > 0:
        reference_signal[-start_shift:] = 0  # Zero out the wrapped part

    # Trim the actual signal from the end to match reference length.
    target_signal = target_signal[:len(reference_signal)]

    return reference_signal, target_signal


def denoise_ppg(ppg_signal, fs, reference_signal):
    """Denoises PPG using DTW for initial alignment and LMS for adaptive filtering."""
    ppg_signal = np.array(ppg_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()
    scaling_factor = np.std(reference_signal)  # Use reference std as a baseline
    reference_signal = (reference_signal - np.mean(reference_signal)) / scaling_factor
    ppg_signal = (ppg_signal - np.mean(ppg_signal)) / scaling_factor

    # Step 1: Band-pass filter to remove unwanted noise
    filtered_signal = butter_bandpass_filter(ppg_signal, fs)

    # Step 2: Align start position with DTW
    aligned_reference, aligned_signal = dtw_align(reference_signal, filtered_signal)

    # Step 3: Apply LMS filtering for adaptive noise removal
    clean_signal = lms_filter(aligned_signal, aligned_reference, fps=fs)
    aligned_reference = aligned_reference[:len(clean_signal)]

    return clean_signal.flatten(), filtered_signal.flatten(), aligned_reference.flatten()


