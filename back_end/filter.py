import numpy as np
from scipy.signal import butter, sosfiltfilt

def butter_bandpass_filter(signal, fs, lowcut=0.5, highcut=5.0, order=4):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)

def adaptive_lms(noisy_signal, reference_signal, mu=0.02, beta=0.2, gamma=2.0, fps=30):
    """
    Improved LMS with stronger reference correction:
    - Beta: Controls the reference signal influence.
    - Gamma: Nonlinear enhancement to correct rhythm mismatches.
    - Mu: Learning rate for weight updates.
    """
    num_taps = int(fps * 2)
    n = len(noisy_signal)
    w = np.zeros((num_taps, num_taps))  # Weight matrix for learning waveforms
    filtered_signal = np.zeros(n)

    for i in range(num_taps, n):
        x = reference_signal[i - num_taps:i]  # Input window
        y = np.dot(w, x)  # Predicted waveform
        e = noisy_signal[i - num_taps:i] - y  # Error vector

        # Strengthen learning when signal deviates a lot
        error_norm = np.linalg.norm(e)
        ref_norm = np.linalg.norm(reference_signal[i - num_taps:i])
        trust_factor = np.tanh(beta * (error_norm / (ref_norm + 1e-8)) ** gamma)  # Nonlinear scaling

        # Weight update (stronger learning from reference when needed)
        w += mu * np.outer(trust_factor * e, x)

        # Output: weighted blend (increase reference influence)
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

