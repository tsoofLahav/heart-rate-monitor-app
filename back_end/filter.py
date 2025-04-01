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
               overlap_ratio=0.5, trust_threshold=0.75):
    """Adaptive LMS filter with artifact detection and overlap for smoother transitions."""

    global not_reading

    num_taps = fps
    overlap = int(num_taps * overlap_ratio)
    step = num_taps - overlap

    if globals.w is None:
        w = np.zeros((num_taps, num_taps))
    else:
        w = globals.w

    n = len(noisy_signal)
    filtered_signal = np.zeros(n)
    prev_filtered = np.zeros(overlap)

    i = 0
    while i + num_taps <= n:
        signal = noisy_signal[i:i + num_taps]
        x = reference_signal[i:i + num_taps]

        y = np.dot(w, x)
        e = signal - y

        # Trust factor based on signal amplitude similarity
        std_ratio = np.std(signal) / (np.std(x) + 1e-8)
        trust_factor = np.exp(-abs(np.log(std_ratio)))
        print("trust_factor:", trust_factor)

        is_artifact = trust_factor < trust_threshold
        not_reading = is_artifact

        # Output: trust signal when clean, fall back to model when artifact
        if is_artifact:
            filtered_chunk = x
        else:
            # Use both LMS and signal in the output
            filtered_chunk = trust_factor * signal + (1 - trust_factor) * y
            w += mu * np.outer(e, x)  # still adapt weights

        # Blending for overlap
        if i == 0:
            filtered_signal[i:i + step] = filtered_chunk[:step]
        else:
            blended = 0.5 * prev_filtered + 0.5 * filtered_chunk[:overlap]
            filtered_signal[i:i + overlap] = blended
            filtered_signal[i + overlap:i + num_taps] = filtered_chunk[overlap:]

        prev_filtered = filtered_chunk[-overlap:]
        i += step

    globals.w = w
    return filtered_signal


def denoise_ppg(ppg_signal, fs, reference_signal):
    """Denoises PPG using LMS filtering without DTW."""
    ppg_signal = np.array(ppg_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()

    # Normalize each to zero mean
    ppg_signal -= np.mean(ppg_signal)
    reference_signal -= np.mean(reference_signal)

    # Scale both to have the same std (e.g., the average std).
    mad = np.median(np.abs(ppg_signal - np.median(ppg_signal)))
    robust_std = mad * 1.4826
    ppg_signal = (ppg_signal / robust_std) * np.std(reference_signal)

    # Step 1: Band-pass filter to remove unwanted noise
    filtered_signal = butter_bandpass_filter(ppg_signal, fs)

    aligned_reference = match_reference_segment(filtered_signal, reference_signal)

    # Step 2: Apply LMS filtering directly (no DTW).
    clean_signal = lms_filter(filtered_signal, aligned_reference, fps=fs)

    return clean_signal.flatten(), filtered_signal.flatten(), not_reading, aligned_reference
