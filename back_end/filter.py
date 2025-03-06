from scipy.signal import sosfiltfilt, butter
import numpy as np


def denoise_ppg(ppg_signal, fs, lowcut=0.5, highcut=5.0, order=8, pad_len=50):
    """
    Denoise PPG signal using a band-pass filter with padding (SOS format).
    """
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq

    # Get filter coefficients in SOS format
    sos = butter(order, [low, high], btype='band', output='sos')

    # Pad signal
    padded_signal = np.pad(ppg_signal, pad_len, mode='reflect')

    # Apply zero-phase filtering
    filtered_signal = sosfiltfilt(sos, padded_signal)

    # Remove padding
    return filtered_signal[pad_len:-pad_len]
