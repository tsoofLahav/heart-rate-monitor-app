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
               artifact_threshold_high=1.5, artifact_threshold_low=0.5, min_trust=0.05, max_trust=0.95,
               max_artifact_streak=5):
    """Adaptive LMS filter that fully replaces artifacts with reference but prioritizes real signal otherwise."""

    global not_reading

    num_taps = int(fps * 2)
    n = len(noisy_signal)

    # **Initialize weight matrix**
    w = np.zeros((num_taps, num_taps))
    filtered_signal = np.zeros(n)

    # **Artifact tracking**
    artifact_streak = 0

    for i in range(0, n, num_taps):
        end_idx = min(i + num_taps, n)

        x = reference_signal[i:end_idx]
        y = np.dot(w[:len(x), :len(x)], x)
        e = noisy_signal[i:end_idx] - y

        # **Artifact Detection (Detect both high & low std)**
        local_variance = np.std(noisy_signal[i:end_idx])
        ref_variance = np.std(reference_signal[i:end_idx])
        artifact_strength = local_variance / (ref_variance + 1e-8)

        is_artifact = artifact_strength > artifact_threshold_high or artifact_strength < artifact_threshold_low

        # **Track artifact streak**
        if is_artifact:
            artifact_streak += 1
            if artifact_streak >= max_artifact_streak:
                not_reading = True  # Too many artifacts in a row → Mark as unreliable
        else:
            artifact_streak = 0  # Reset streak when a clean segment is found

        # **Trust Factor**
        error_norm = np.linalg.norm(e)
        ref_norm = np.linalg.norm(x)
        input_norm = np.linalg.norm(noisy_signal[i:end_idx])

        trust_factor = np.tanh(beta * ((error_norm / (ref_norm + 1e-8)) ** gamma))
        trust_factor = np.clip(trust_factor, min_trust, max_trust)

        # **Set Output Based on Artifact Detection**
        if is_artifact:
            adaptive_mu = 0  # Stop learning completely
            filtered_signal[i:end_idx] = x  # Completely replace with reference
        else:
            adaptive_mu = mu / (1 + 0.1 * i / num_taps)
            blend_factor = 1 - (input_norm / (input_norm + ref_norm + 1e-8))
            blend_factor = np.clip(blend_factor, 0.7, 0.95)  # Prioritize actual signal

            filtered_signal[i:end_idx] = blend_factor * noisy_signal[i:end_idx] + (1 - blend_factor) * y

        # **Update Weights Only for Clean Segments**
        w[:len(x), :len(x)] += adaptive_mu * np.outer(trust_factor * e, x)

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

    return clean_signal.flatten(), filtered_signal.flatten(), reference_signal.flatten()

