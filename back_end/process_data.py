import numpy as np
from flask import jsonify

import peak_detection
import create_data

last_interval = -1
ave_gap = 1
list_for_storage = []


def detect_pulse(intensities, fps):
    global ave_gap, last_interval
    #
    #
    # detect peaks and unstable reading using peak_detection file
    signal = np.array(intensities)
    filtered_signal = peak_detection.moving_average_filter(signal, window_size=3)
    baseline = np.mean(filtered_signal)
    std_dev = np.std(filtered_signal)
    not_reading = peak_detection.detect_unstable_reading(filtered_signal, baseline, std_dev)
    if not_reading:
        return True, [], False, 0.0
    dynamic_threshold = baseline + (0.5 * std_dev)
    peaks = peak_detection.detect_peaks(filtered_signal, dynamic_threshold)
    total_duration = len(signal) / fps
    #
    #
    # create new data to send to front end, using the peaks, using create_data file
    # if last_interval != -1:
    #     list_for_storage.append(last_interval)
    time_gaps, last_interval = create_data.convert_peaks_to_timegaps(peaks, fps, total_duration, len(signal),
                                                                     last_interval, ave_gap)
    ave_gap, bpm = create_data.compute_average_gap_and_bpm(time_gaps, last_interval)
    new_list, new_start = create_data.creating_new_list(total_duration, last_interval, ave_gap)
    #
    #
    # send to storage and return to front end
    # if last_interval != -1:
    #     list_for_storage[-1] += time_gaps[0]
    # else:
    #     list_for_storage.append(time_gaps[0])
    # list_for_storage.append(time_gaps[1:])
    return not_reading, new_list, new_start, bpm
