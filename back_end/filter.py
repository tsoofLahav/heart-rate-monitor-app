import numpy as np
from scipy.signal import butter, sosfiltfilt
from scipy.signal import correlate
from scipy.interpolate import interp1d
import logging

not_reading = False
logging.basicConfig(level=logging.DEBUG)


def butter_bandpass_filter(signal, fs, lowcut=0.5, highcut=5.0, order=4):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def align_reference(noisy_signal, reference_signal, num_taps):
    """Aligns a reference signal to match a padded noisy signal using cross-correlation and resampling."""

    # **Step 1: Pad the Noisy Signal (Since It's Shorter)**
    pad_size = int((1.5 * num_taps - num_taps) / 2)
    padded_noisy_signal = np.pad(noisy_signal, (pad_size, pad_size), mode='edge')

    # **Step 2: Find the Best Shift Using Cross-Correlation**
    correlation = correlate(padded_noisy_signal[:int(1.5 * num_taps)], reference_signal, mode='valid')
    shift = np.argmax(correlation) - (len(reference_signal) // 2)

    # **Step 3: Dynamically Trim Reference Based on Shift**
    left_trim = max(0, pad_size - shift)  # Reduce left trim if shifted left
    right_trim = max(0, pad_size + shift)  # Reduce right trim if shifted right
    aligned_reference = reference_signal[left_trim:len(reference_signal) - right_trim]

    # Ensure aligned_reference matches noisy_signal length exactly
    if len(aligned_reference) < len(noisy_signal):
        aligned_reference = np.pad(aligned_reference, (0, len(noisy_signal) - len(aligned_reference)), mode='edge')
    elif len(aligned_reference) > len(noisy_signal):
        aligned_reference = aligned_reference[:len(noisy_signal)]

    # **Step 4: Resample to Match the Noisy Signal More Accurately**
    resample_factor = len(noisy_signal) / len(aligned_reference)
    resampler = interp1d(np.linspace(0, 1, len(aligned_reference)), aligned_reference, kind='cubic', fill_value="extrapolate")
    aligned_reference = resampler(np.linspace(0, 1, len(noisy_signal)))

    return aligned_reference  # Final aligned reference, same length as noisy signal


def lms_filter(noisy_signal, reference_signal, mu=0.05, fps=30, beta=1.2, gamma=2.0,
               min_trust=0.05, max_trust=0.99, max_artifact_streak=5, trust_artifact_threshold=0.98):
    """Adaptive LMS filter with improved artifact detection and rhythm correction."""

    global not_reading

    num_taps = int(fps * 2)

    # **Trim reference to 1.5 * num_taps**
    reference_signal = reference_signal[:int(3 * num_taps)]

    # **Initialize weight matrix**
    w = np.zeros((num_taps, num_taps))

    # Ensure signal length is a multiple of num_taps
    valid_length = (len(noisy_signal) // num_taps) * num_taps
    noisy_signal = noisy_signal[:valid_length]
    n = len(noisy_signal)
    filtered_signal = np.zeros(n)

    # **Artifact tracking**
    artifact_streak = 0

    for i in range(0, n, num_taps):
        end_idx = min(i + num_taps, n)

        # **Align Reference Segment**
        aligned_reference = align_reference(noisy_signal[i:end_idx], reference_signal, num_taps)

        x = aligned_reference[:end_idx - i]  # Trim to match chunk
        y = np.dot(w, x)  # LMS Prediction
        e = noisy_signal[i:end_idx] - y  # Error vector

        # **Trust Factor Calculation with Absolute Difference**
        error_norm = np.linalg.norm(e)
        ref_norm = np.linalg.norm(x)

        trust_factor = np.tanh(beta * ((error_norm / (ref_norm + 1e-8)) ** gamma))
        trust_factor = np.clip(trust_factor, min_trust, max_trust)

        # **New Artifact Detection: More Sensitive**
        absolute_diff = np.mean(np.abs(noisy_signal[i:end_idx] - x))  # Avg absolute difference
        is_artifact = trust_factor < trust_artifact_threshold or absolute_diff > 1.15 * np.std(x)  # More aggressive check

        # **Track artifact streak**
        if is_artifact:
            artifact_streak += 1
            if artifact_streak >= max_artifact_streak:
                not_reading = True  # Too many artifacts → Mark as unreliable
        else:
            artifact_streak = 0  # Reset streak

        # **Set Output Based on Artifact Detection**
        if is_artifact:
            adaptive_mu = 0  # Stop learning
            filtered_signal[i:end_idx] = x  # Fully replace with reference
        else:
            adaptive_mu = mu / (1 + 0.1 * i / num_taps)
            blend_factor = np.clip(1 - trust_factor, 0.6, 0.95)  # Lower trust = more reference

            filtered_signal[i:end_idx] = blend_factor * x + (1 - blend_factor) * noisy_signal[i:end_idx]

        # **Update Weights Only for Clean Segments**
        w += adaptive_mu * np.outer(trust_factor * e, x)

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
    clean_signal = lms_filter(filtered_signal, reference_signal, fps=fs)

    return clean_signal.flatten(), filtered_signal.flatten(), reference_signal.flatten(), not_reading
