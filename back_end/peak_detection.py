import numpy as np


# Moving average filter
def moving_average_filter(data, window_size):
    return np.convolve(data, np.ones(window_size) / window_size, mode='same')


# Peak detection function
def detect_peaks(signal, dynamic_threshold):
    peaks = []
    i = 1  # Start from the second element
    while i < len(signal) - 1:
        # Check if the current value is a peak (greater or equal to neighbors and above threshold)
        if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1] and signal[i] > dynamic_threshold:
            peaks.append(i)
            # Skip over the rest of the plateau to avoid duplicate peaks
            while i < len(signal) - 1 and signal[i] == signal[i + 1]:
                i += 1
        i += 1
    return np.array(peaks)


def detect_unstable_reading(filtered_signal, baseline, std_dev, std_threshold=1.5):
    #  If all values are (near) zero, mark as unstable
    if np.all(filtered_signal == 0) or baseline == 0:
        return True

    #  If standard deviation is too high, mark as unstable
    if std_dev > std_threshold * baseline:
        return True

    return False  # Otherwise, signal is stable
