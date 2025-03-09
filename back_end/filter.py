import numpy as np
from scipy.signal import butter, sosfiltfilt


def butter_bandpass_filter(signal, fs, lowcut=0.5, highcut=5.0, order=4):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)

def adaptive_lms(noisy_signal, reference_signal, mu=0.01, beta=0.1, fps=30, alpha=0.99):
    """
    LMS filtering with adaptive correction:
    - Beta controls how much to trust the reference (higher for noise, lower for rhythm shifts).
    - Alpha stabilizes updates to avoid exploding values.
    """
    num_taps = int(fps * 2)
    n = len(noisy_signal)
    w = np.zeros((num_taps, num_taps))  # Weight matrix for learning waveforms
    filtered_signal = np.zeros(n)

    for i in range(num_taps, n):
        x = reference_signal[i - num_taps:i]  # Input window
        y = np.dot(w, x)  # Predicted waveform
        e = noisy_signal[i - num_taps:i] - y  # Error vector

        # Adaptive trust in reference: larger beta if noise is high
        error_norm = np.linalg.norm(e)
        ref_norm = np.linalg.norm(reference_signal[i - num_taps:i])
        trust_factor = np.clip(beta * (error_norm / (ref_norm + 1e-8)), 0, 1)  # Avoid div by zero

        # Weighted weight update: slowly adapt rhythm, strongly correct noise
        w = alpha * w + mu * np.outer(trust_factor * e, x)

        # Weighted output mixture: trust noisy_signal more for rhythm, reference more for noise
        filtered_signal[i - num_taps:i] = (1 - trust_factor) * noisy_signal[i - num_taps:i] + trust_factor * y

    return filtered_signal

def denoise_ppg(ppg_signal, fs, reference_signal):
    """Denoises PPG using LMS filtering without DTW."""
    ppg_signal = np.array(ppg_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()
    scaling_factor = np.std(reference_signal)  # Use reference std as a baseline
    reference_signal = (reference_signal - np.mean(reference_signal)) / scaling_factor
    ppg_signal = (ppg_signal - np.mean(ppg_signal)) / scaling_factor

    # Step 1: Band-pass filter to remove unwanted noise
    filtered_signal = butter_bandpass_filter(ppg_signal, fs)

    # Step 2: Apply LMS filtering directly (no DTW)
    clean_signal = adaptive_lms(filtered_signal, reference_signal, fps=fs)

    return clean_signal.flatten(), filtered_signal.flatten(), reference_signal.flatten()



