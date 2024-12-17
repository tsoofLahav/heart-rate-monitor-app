import numpy as np
from bpm_and_hrv import bpm_and_hrv_calculator

gap = 0  # gap from last beat of the last video
hrv = 1
newStart = False


# Moving average filter
def moving_average_filter(data, window_size):
    return np.convolve(data, np.ones(window_size) / window_size, mode='valid')


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


def peaks_detection(intensities, fps):
    global gap, hrv, newStart
    # Apply moving average filter
    signal = np.array(intensities)
    filtered_signal = moving_average_filter(signal, window_size=3)
    newStart = False

    # Calculate dynamic threshold and detect peaks
    baseline = np.mean(filtered_signal)
    std_dev = np.std(filtered_signal)
    dynamic_threshold = baseline*0.5
    peaks = detect_peaks(filtered_signal, dynamic_threshold)

    # Convert peaks to time values based on fps
    peaks_in_time = [peak / fps for peak in peaks]

    # Damage control 1: too much noise
    if len(peaks_in_time) > 3:
        return [-1], -1, -1, False

    # Add or remove peak in case of peak landing on gap between videos
    if len(peaks_in_time) != 0:
        if gap + peaks_in_time[0] < 0.25:
            del peaks_in_time[0]
        elif gap + peaks_in_time[0] > 2 * hrv:
            newStart = True
            peaks_in_time.insert(0, 0)
        gap = 1 - peaks_in_time[-1]
    else:
        if 1 + gap > 2 * hrv:
            peaks_in_time.insert(0, 0)
            newStart = True
            gap = 1
        else:
            gap += 1

    # Damage control 2: pulse is not detected for two seconds
    if gap > 2:
        peaks_in_time = [-1]
        bpm, hrv = -1
    else:
        bpm, hrv = bpm_and_hrv_calculator(peaks_in_time)
    return peaks_in_time, bpm, hrv, newStart
