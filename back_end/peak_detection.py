import numpy as np

extra_beat = False
missing_beat = False


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


# Convert peaks to time gaps
def convert_peaks_to_timegaps(peaks, fps, total_duration, time):
    if len(peaks) == 0:
        return np.array([total_duration])

    time_gaps = [peaks[0] / fps]

    if len(peaks) > 1:
        time_gaps.extend(np.diff(peaks) / fps)

    time_gaps.append((time - peaks[-1]) / fps)
    return np.array(time_gaps)


# Detect duplicate beats
def detect_duplicate_beats(fps, peaks):
    global extra_beat
    if len(peaks) > 0 and peaks[0] < fps / 15 and extra_beat:
        peaks = peaks[1:]  # Remove the first peak if it is too close to the start and extra_beat is flagged

    if len(peaks) > 0 and (fps - peaks[-1]) < fps / 15:
        peaks = peaks[:-1]  # Remove the last peak if it is too close to the end
        extra_beat = True
    else:
        extra_beat = False

    return peaks


# Detect missing beats
def detect_missing_beats(time_gaps, ave_gap, new_start):
    global missing_beat
    if len(time_gaps) > 0 and time_gaps[0] >= ave_gap and missing_beat:
        new_start = True

    if len(time_gaps) > 0 and time_gaps[-1] >= ave_gap:
        missing_beat = True
    else:
        missing_beat = False

    return new_start


# Detect unstable readings
def detect_unstable_reading(filtered_signal, baseline, std_dev, std_threshold=1.5):
    #  If all values are (near) zero, mark as unstable
    if np.all(filtered_signal == 0) or baseline == 0:
        return True

    #  If standard deviation is too high, mark as unstable
    if std_dev > std_threshold * baseline:
        return True

    return False  # Otherwise, signal is stable


# Detect pulse
def detect_pulse(intensities, fps, ave_gap):
    global extra_beat, missing_beat

    # Apply moving average filter
    signal = np.array(intensities)
    filtered_signal = moving_average_filter(signal, window_size=3)
    new_start = extra_beat

    #  Compute baseline & std_dev **once**
    baseline = np.mean(filtered_signal)
    std_dev = np.std(filtered_signal)

    #  Check for unstable readings **using precomputed values**
    not_reading = detect_unstable_reading(filtered_signal, baseline, std_dev)

    if not_reading:
        return not_reading, [], False

    #  Compute dynamic threshold using precomputed baseline & std_dev
    dynamic_threshold = baseline + (0.5 * std_dev)
    peaks = detect_peaks(filtered_signal, dynamic_threshold)
    total_duration = len(signal) / fps

    # Detect duplicate beats
    peaks = detect_duplicate_beats(fps, peaks)

    # Convert peaks to time gaps
    time_gaps = convert_peaks_to_timegaps(peaks, fps, total_duration, len(signal))

    # Detect missing beats
    new_start = detect_missing_beats(time_gaps, ave_gap, new_start)

    return not_reading, time_gaps, new_start

