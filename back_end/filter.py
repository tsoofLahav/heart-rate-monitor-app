import numpy as np
from scipy.signal import butter, sosfiltfilt
from scipy.signal import correlate
from scipy.interpolate import interp1d
import logging

not_reading = False
logging.basicConfig(level=logging.DEBUG)
# w = None


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


def lms_filter(noisy_signal, reference_signal, mu=0.05, fps=24,
               beta_correction=2.5, gamma_correction=3.5,  # More aggressive for correction
               beta_flagging=1.5, gamma_flagging=2,  # Less aggressive for flagging artifacts
               min_trust=0.1, max_trust=0.9,
               max_artifact_streak=5, trust_threshold_correction=0.9, trust_threshold_flagging=0.5):
    """Adaptive LMS filter with strong correction but less aggressive artifact streak detection."""

    global not_reading

    num_taps = fps
    reference_signal = reference_signal[:3 * num_taps]  # Trim reference
    w = np.zeros((num_taps, num_taps))  # Initialize weight matrix

    n = len(noisy_signal)
    filtered_signal = np.zeros(n)

    artifact_streak = 0

    for i in range(0, n, num_taps):
        signal = noisy_signal[i:i + num_taps]
        x = align_reference(signal, reference_signal, num_taps)

        y = np.dot(w, x)  # LMS Prediction
        e = signal - y  # Error

        # **Aggressive correction trust factor**
        trust_factor_correction = np.tanh(beta_correction * (np.linalg.norm(e) / (np.linalg.norm(x) + 1e-8)) ** gamma_correction)
        trust_factor_correction = np.clip(trust_factor_correction, min_trust, max_trust)

        # **Less aggressive artifact streak detection trust factor**
        trust_factor_flagging = np.tanh(beta_flagging * (np.linalg.norm(e) / (np.linalg.norm(x) + 1e-8)) ** gamma_flagging)
        trust_factor_flagging = np.clip(trust_factor_flagging, min_trust, max_trust)

        # **Detection thresholds**
        is_artifact_correction = trust_factor_correction < trust_threshold_correction  # More aggressive for correction
        is_artifact_flagging = trust_factor_flagging < trust_threshold_flagging  # Less aggressive for flagging

        # **Flag only on less aggressive detection**
        artifact_streak = artifact_streak + 1 if is_artifact_flagging else 0
        not_reading = artifact_streak >= max_artifact_streak

        # **Correction: If artifact detected, fully replace signal with reference x**
        if is_artifact_correction:
            filtered_signal[i:i + num_taps] = x  # Full correction
        else:
            blend_factor = np.clip(1 - trust_factor_correction, 0.75, 1.0)
            filtered_signal[i:i + num_taps] = blend_factor * x + (1 - blend_factor) * signal  # Partial correction

        # **Allow adaptation unless artifact is flagged (less aggressive)**
        w += (mu * np.outer(trust_factor_correction * e, x)) if not is_artifact_flagging else 0

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

    return clean_signal.flatten(), filtered_signal.flatten(), not_reading
