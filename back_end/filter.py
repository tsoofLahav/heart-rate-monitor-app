from scipy.signal import butter, sosfiltfilt
import logging
from scipy.signal import correlate
from scipy.interpolate import interp1d
import numpy as np
import globals

not_reading = False
logging.basicConfig(level=logging.DEBUG)


def butter_bandpass_filter(signal, fs, lowcut=0.5, highcut=5.0, order=4):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def align_reference(noisy_signal, reference_signal, range_width=0.3, steps=10):
    noisy_signal = np.array(noisy_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()

    low = max(0.1, globals.base_factor - range_width / 2)
    high = globals.base_factor + range_width / 2

    best_corr = -np.inf
    best_aligned = None
    best_factor = None

    for factor in np.linspace(low, high, steps):
        # Stretch reference
        stretched_len = int(len(reference_signal) * factor)
        x_old = np.linspace(0, 1, len(reference_signal))
        x_new = np.linspace(0, 1, stretched_len)
        stretched_ref = interp1d(x_old, reference_signal, kind='cubic', fill_value='extrapolate')(x_new)

        # Pad noisy signal
        pad_total = max(0, len(stretched_ref) - len(noisy_signal))
        padded_noisy = np.pad(noisy_signal, (pad_total // 2, pad_total - pad_total // 2), mode='edge')

        # Cross-correlation
        correlation = correlate(padded_noisy, stretched_ref, mode='valid')
        shift = np.argmax(correlation)

        # Cut aligned part
        if shift + len(noisy_signal) <= len(stretched_ref):
            aligned = stretched_ref[shift:shift + len(noisy_signal)]
        else:
            aligned = np.pad(stretched_ref[shift:], (0, shift + len(noisy_signal) - len(stretched_ref)), mode='edge')

        if np.max(correlation) > best_corr:
            best_corr = np.max(correlation)
            best_aligned = aligned
            best_factor = factor

        globals.base_factor = best_factor
    return best_aligned


def lms_filter(noisy_signal, reference_signal, mu=0.05, fps=24,
               beta=1.5, gamma=2,  # Less aggressive for flagging artifacts
               min_trust=0.1, max_trust=0.9,
               max_artifact_streak=5, trust_threshold_correction=0.4, trust_threshold_flagging=0.1):
    """Adaptive LMS filter with strong correction but less aggressive artifact streak detection."""

    global not_reading

    num_taps = fps
    if globals.w is None:
        w = np.zeros((num_taps, num_taps))  # Initialize weight matrix
    else:
        w = globals.w

    n = len(noisy_signal)
    filtered_signal = np.zeros(n)

    artifact_streak = 0

    for i in range(0, n, num_taps):
        signal = noisy_signal[i:i + num_taps]
        x = reference_signal[i:i + num_taps]

        y = np.dot(w, x)  # LMS Prediction
        e = signal - y  # Error

        # **Aggressive correction trust factor**
        trust_factor = np.tanh(beta * (np.linalg.norm(e) / (np.linalg.norm(x) + 1e-8)) ** gamma)
        trust_factor = np.clip(trust_factor, min_trust, max_trust)

        # **Detection thresholds**
        is_artifact_correction = trust_factor < trust_threshold_correction  # More aggressive for correction
        is_artifact_flagging = trust_factor < trust_threshold_flagging  # Less aggressive for flagging

        # **Flag only on less aggressive detection**
        artifact_streak = artifact_streak + 1 if is_artifact_flagging else 0
        not_reading = artifact_streak >= max_artifact_streak

        # **Correction: If artifact detected, fully replace signal with reference x**
        if is_artifact_correction:
            filtered_signal[i:i + num_taps] = x  # Full correction
        else:
            blend_factor = np.clip(1 - trust_factor, 0.75, 1.0)
            filtered_signal[i:i + num_taps] = blend_factor * x + (1 - blend_factor) * signal  # Partial correction

        # **Allow adaptation unless artifact is flagged (less aggressive)**
        w += (mu * np.outer(trust_factor * e, x)) if not is_artifact_flagging else 0

    globals.w = w
    return filtered_signal


def denoise_ppg(ppg_signal, fs, reference_signal):
    """Denoises PPG using LMS filtering without DTW."""
    ppg_signal = np.array(ppg_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()

    # Normalize each to zero mean
    ppg_signal -= np.mean(ppg_signal)
    reference_signal -= np.mean(reference_signal)

    # Scale both to have the same std (e.g., the average std)
    ppg_signal = (ppg_signal / np.std(ppg_signal)) * np.std(reference_signal)

    # Step 1: Band-pass filter to remove unwanted noise
    filtered_signal = butter_bandpass_filter(ppg_signal, fs)

    aligned_reference = align_reference(filtered_signal, reference_signal)

    # Step 2: Apply LMS filtering directly (no DTW)
    clean_signal = lms_filter(filtered_signal, aligned_reference, fps=fs)

    return clean_signal.flatten(), filtered_signal.flatten(), not_reading, aligned_reference
