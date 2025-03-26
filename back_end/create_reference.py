from scipy.signal import butter, sosfiltfilt
import numpy as np


def butter_bandpass_filter(signal, fs, lowcut=0.8, highcut=2.8, order=6):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def create_ppg(ppg_signal, fs):
    ppg_signal = np.array(ppg_signal).flatten()

    # Normalize each to zero mean
    ppg_signal -= np.mean(ppg_signal)

    # Scale both to have the same std (e.g., the average std)
    ppg_signal = ppg_signal / np.std(ppg_signal)

    # Step 1: Band-pass filter to remove unwanted noise
    filtered_signal = butter_bandpass_filter(ppg_signal, fs)

    return filtered_signal.flatten()
