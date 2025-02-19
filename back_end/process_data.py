import numpy as np
import peak_detection
import create_data


def detect_pulse(intensities, fps):
    #
    #
    # detect peaks and unstable reading using peak_detection file
    # Process signal before peak detection
    filtered_signal = np.array(intensities)

    # Normalize
    filtered_signal = peak_detection.normalize_signal(filtered_signal)

    # Apply band-pass filter
    # filtered_signal = peak_detection.bandpass_filter(filtered_signal, fps)

    # Compute baseline and std deviation
    baseline = np.mean(filtered_signal)
    std_dev = np.std(filtered_signal)

    # Detect unstable reading
    not_reading = peak_detection.detect_unstable_reading(filtered_signal, baseline, std_dev)
    if not_reading:
        return True, [], False, 0.0

    # Dynamic threshold and peak detection
    # dynamic_threshold = baseline + (0.2 * std_dev)
    peaks = peak_detection.detect_peaks(filtered_signal, fps)
    total_duration = len(filtered_signal) / fps
    #
    #
    # create new data to send to front end, using the peaks, using create_data file
    # if last_interval != -1:
    #     list_for_storage.append(last_interval)
    new_start, new_list, bpm = create_data.process_peaks(peaks, fps, total_duration)
    #
    #
    # send to storage and return to front end
    # if last_interval != -1:
    #     list_for_storage[-1] += time_gaps[0]
    # else:
    #     list_for_storage.append(time_gaps[0])
    # list_for_storage.append(time_gaps[1:])
    return not_reading, new_list, new_start, bpm
