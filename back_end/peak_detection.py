import numpy as np

last_interval = -1
old_ave_gap = 1
new_ave_gap = 1


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


def compute_average_gap(time_gaps, last_interval):
    if last_interval == -1:
        sum_up = sum(time_gaps[1:-1])
        average = sum_up / len(time_gaps[1:-1])
    else:
        sum_up = sum(time_gaps[:-1]) + last_interval
        average = sum_up / len(time_gaps[:-1])
    return average


def creating_new_list(time_gaps, old_ave_gap, new_ave_gap, total_duration):
    global last_interval

    if last_interval == -1:
        last_interval = time_gaps[-1]
        old_ave_gap = new_ave_gap
    new_start = False
    new_list = []
    first_interval = (new_ave_gap - last_interval) + (new_ave_gap - old_ave_gap)
    if first_interval < 0:
        first_interval = new_ave_gap + first_interval
        new_list.append(first_interval)
        new_start = True
    elif first_interval == 0:
        new_start = True
    else:
        new_list.append(first_interval)
    total_duration -= first_interval
    while total_duration >= new_ave_gap:
        total_duration -= new_ave_gap
        new_list.append(new_ave_gap)
    new_list.append(total_duration)
    last_interval = total_duration
    return new_list, new_start

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
    global old_ave_gap, new_ave_gap, last_interval
    # Apply moving average filter
    signal = np.array(intensities)
    filtered_signal = moving_average_filter(signal, window_size=3)

    #  Compute baseline & std_dev **once**
    baseline = np.mean(filtered_signal)
    std_dev = np.std(filtered_signal)

    #  Check for unstable readings **using precomputed values**
    not_reading = detect_unstable_reading(filtered_signal, baseline, std_dev)

    if not_reading:
        return True, [], False

    #  Compute dynamic threshold using precomputed baseline & std_dev
    dynamic_threshold = baseline + (0.5 * std_dev)
    peaks = detect_peaks(filtered_signal, dynamic_threshold)
    total_duration = len(signal) / fps

    # Convert peaks to time gaps
    time_gaps = convert_peaks_to_timegaps(peaks, fps, total_duration, len(signal))

    # defining average gaps
    old_ave_gap = new_ave_gap
    new_ave_gap = compute_average_gap(time_gaps, last_interval)

    # defining a beat between the intervals
    new_list, new_start = creating_new_list(time_gaps, old_ave_gap, new_ave_gap, total_duration)

    return not_reading, new_list, new_start, last_interval
