from scipy.signal import butter, sosfiltfilt
import logging
from scipy.signal import correlate
from scipy.interpolate import interp1d
import numpy as np
import globals

not_reading = False
logging.basicConfig(level=logging.DEBUG)


def butter_bandpass_filter(signal, fs, lowcut=0.8, highcut=3.0, order=6):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def match_reference_segment(noisy_signal, reference_signal, stretch_range=(0.6, 1.2), steps=20):
    """
    Finds the best-matching segment in a longer reference for a given noisy signal,
    allowing stretching/squeezing.
    Returns the aligned segment from the reference (same length as noisy_signal).
    """
    noisy_signal = np.array(noisy_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()

    best_corr = -np.inf
    best_segment = None

    for factor in np.linspace(*stretch_range, steps):
        # Stretch the reference
        stretched_len = int(len(reference_signal) * factor)
        x_old = np.linspace(0, 1, len(reference_signal))
        x_new = np.linspace(0, 1, stretched_len)
        stretched_ref = interp1d(x_old, reference_signal, kind='cubic', fill_value="extrapolate")(x_new)

        # Slide over the stretched reference to find best matching window
        for start in range(0, len(stretched_ref) - len(noisy_signal) + 1):
            segment = stretched_ref[start:start + len(noisy_signal)]

            # Normalize both before correlation
            segment_norm = (segment - np.mean(segment)) / (np.std(segment) + 1e-8)
            noisy_norm = (noisy_signal - np.mean(noisy_signal)) / (np.std(noisy_signal) + 1e-8)
            corr = np.dot(segment_norm, noisy_norm)

            if corr > best_corr:
                best_corr = corr
                best_segment = segment

    return best_segment


def lms_filter(noisy_signal, reference_signal, mu=0.08, fps=24,
               min_trust=0.0, max_trust=0.1,
               max_artifact_streak=5,
               trust_threshold_correction=0.02):
    """Aggressive correction if signal deviates, minimal intervention when clean."""

    global not_reading

    num_taps = fps
    if globals.w is None:
        w = np.zeros((num_taps, num_taps))
    else:
        w = globals.w

    n = len(noisy_signal)
    filtered_signal = np.zeros(n)
    artifact_streak = 0

    for i in range(0, n, num_taps):
        signal = noisy_signal[i:i + num_taps]
        x = reference_signal[i:i + num_taps]

        if len(signal) < num_taps or len(x) < num_taps:
            break

        y = np.dot(w, x)
        e = signal - y

        corr = np.corrcoef(signal, x)[0, 1]
        trust_factor = np.clip(corr, min_trust, max_trust)

        is_artifact = trust_factor < trust_threshold_correction

        artifact_streak = artifact_streak + 1 if is_artifact else 0
        not_reading = artifact_streak >= max_artifact_streak

        if is_artifact:
            # Replace with reference — stronger correction
            filtered_signal[i:i + num_taps] = x
        else:
            # Lighter correction — stay close to original
            blend_factor = np.clip(1 - trust_factor, 0.05, 0.25)  # mostly original
            filtered_signal[i:i + num_taps] = (1 - blend_factor) * signal + blend_factor * x

        # Stronger learning from clean signal
        if not is_artifact:
            w += mu * np.outer(trust_factor * e, x)

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

    aligned_reference = match_reference_segment(filtered_signal, reference_signal)

    # Step 2: Apply LMS filtering directly (no DTW)
    clean_signal = lms_filter(filtered_signal, aligned_reference, fps=fs)

    return clean_signal.flatten(), filtered_signal.flatten(), not_reading, aligned_reference
