import numpy as np
from scipy.signal import butter, sosfiltfilt


def butter_bandpass_filter(signal, fs, lowcut=0.5, highcut=5.0, order=4):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def lms_filter(noisy_signal, reference_signal, mu=0.05, fps=30, alpha=0.99, beta=0.7, gamma=1.5,
               artifact_threshold=1.5, min_trust=0.1, max_trust=0.95):
    """Adaptive LMS filter that avoids learning artifacts and corrects rhythm mismatches."""

    num_taps = int(fps * 2)
    n = len(noisy_signal)
    w = np.zeros((num_taps, num_taps))  # Weight matrix for learning patterns
    filtered_signal = np.zeros(n)

    for i in range(0, n - num_taps, num_taps):  # Process in rhythmic chunks
        x = reference_signal[i:i + num_taps]  # Reference window
        y = np.dot(w, x)  # LMS Prediction
        e = noisy_signal[i:i + num_taps] - y  # Error vector

        # **Artifact Detection**
        local_variance = np.std(noisy_signal[i:i + num_taps])
        ref_variance = np.std(reference_signal[i:i + num_taps])
        artifact_strength = local_variance / (ref_variance + 1e-8)  # Compare noise level
        is_artifact = artifact_strength > artifact_threshold  # Mark artifacts

        # **Trust Factor: Ignore noisy input when artifacts are present**
        error_norm = np.linalg.norm(e)
        ref_norm = np.linalg.norm(x)
        input_norm = np.linalg.norm(noisy_signal[i:i + num_taps])

        trust_factor = np.tanh(beta * ((error_norm / (ref_norm + 1e-8)) ** gamma))
        trust_factor = np.clip(trust_factor, min_trust, max_trust)

        # **Dynamic Learning Rate**
        adaptive_mu = mu / (1 + 0.1 * i / num_taps)  # Decay learning over time
        adaptive_mu = 0 if is_artifact else adaptive_mu  # Completely stop learning artifacts

        # **Prevent artifact learning in weight updates**
        w += adaptive_mu * np.outer(trust_factor * e, x)

        # **Blend Factor: Adjust correction intensity**
        if is_artifact:
            blend_factor = 0.9  # Strongly correct artifacts
        else:
            blend_factor = 1 - (input_norm / (input_norm + ref_norm + 1e-8))
            blend_factor = np.clip(blend_factor, 0.2, 0.8)

        # **Final Signal Correction**
        filtered_signal[i:i + num_taps] = blend_factor * y + (1 - blend_factor) * noisy_signal[i:i + num_taps]

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

