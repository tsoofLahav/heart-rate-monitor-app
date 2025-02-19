import numpy as np


# Convert peaks to time gaps, and extreact last interval
def convert_peaks_to_timegaps(peaks, fps, total_duration, time, last_interval, ave_gap):
    if len(peaks) == 0:
        return np.array([total_duration])

    time_gaps = [peaks[0] / fps]

    if len(peaks) > 1:
        time_gaps.extend(np.diff(peaks) / fps)

    time_gaps.append((time - peaks[-1]) / fps)

    if last_interval + time_gaps[0] > 1.5 * ave_gap:
        time_gaps = [0] + time_gaps
    return np.array(time_gaps), time_gaps[-1]


# compute average gap and bpm
def compute_average_gap_and_bpm(time_gaps, last_interval):
    average = -1
    if last_interval == -1:
        sum_up = sum(time_gaps[1:-1])
        if len(time_gaps[1:-1]) != 0:
            average = sum_up / len(time_gaps[1:-1])
    else:
        sum_up = sum(time_gaps[:-1]) + last_interval
        if len(time_gaps[:-1]) != 0:
            average = sum_up / len(time_gaps[:-1])
    bpm = 60 / average
    return average, bpm


def creating_new_list(total_duration, last_interval, ave_gap):
    new_start = False
    new_list = []
    first_interval = ave_gap - last_interval
    if first_interval <= 0:
        new_start = True
    else:
        new_list.append(first_interval)
        total_duration -= first_interval
    while total_duration >= ave_gap:
        total_duration -= ave_gap
        new_list.append(ave_gap)
    new_list.append(total_duration)
    return new_list, new_start
