import numpy as np
from scipy.signal import butter, sosfiltfilt

not_reading = False


def butter_bandpass_filter(signal, fs, lowcut=0.5, highcut=5.0, order=4):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def lms_filter(noisy_signal, reference_signal, mu=0.05, fps=30, alpha=0.99, beta=0.7, gamma=1.5,
               artifact_threshold=1.5, min_trust=0.1, max_trust=0.95, consecutive_artifact_limit=5):
    """Adaptive LMS filter that avoids learning artifacts and corrects rhythm mismatches."""

    num_taps = int(fps * 2)
    n = len(noisy_signal)
    w = np.zeros((num_taps, num_taps))  # Weight matrix for learning patterns
    filtered_signal = np.zeros(n)

    consecutive_artifacts = 0
    global not_reading  # Flag for prolonged artifacts
    not_reading = False

    for i in range(0, n - num_taps, num_taps):  # Process in rhythmic chunks
        x = reference_signal[i:i + num_taps]  # Reference window
        y = np.dot(w, x)  # LMS Prediction
        e = noisy_signal[i:i + num_taps] - y  # Error vector

        # **Unified Artifact Detection & Trust Factor**
        ref_variance = np.std(reference_signal[i:i + num_taps]) + 1e-8
        local_variance = np.std(noisy_signal[i:i + num_taps]) + 1e-8
        artifact_strength = local_variance / ref_variance  # Compare noise level

        is_artifact = artifact_strength > artifact_threshold or artifact_strength < 1 / artifact_threshold  # High or Low Variance
        trust_factor = np.clip(np.tanh(beta * (artifact_strength ** gamma)), min_trust, max_trust)

        # **Handle Consecutive Artifacts**
        if is_artifact:
            consecutive_artifacts += 1
        else:
            consecutive_artifacts = 0

        if consecutive_artifacts >= consecutive_artifact_limit:
            not_reading = True  # Trigger the global flag

        # **Dynamic Learning Rate**
        adaptive_mu = 0 if is_artifact else mu / (1 + 0.1 * i / num_taps)  # Stop learning artifacts

        # **Update Weights**
        w += adaptive_mu * np.outer(trust_factor * e, x)

        # **Final Signal Correction**
        if is_artifact:
            filtered_signal[i:i + num_taps] = x  # Fully trust reference when artifact detected
        else:
            filtered_signal[i:i + num_taps] = trust_factor * y + (1 - trust_factor) * noisy_signal[i:i + num_taps]

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

