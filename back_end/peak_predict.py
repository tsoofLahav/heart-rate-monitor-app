import numpy as np
from scipy.signal import find_peaks
from statsmodels.tsa.ar_model import AutoReg
import math
import globals
import logging


def detect_peaks(signal, fps, std_multiplier=0.33):
    signal = np.array(signal)

    if globals.average_gap:
        min_distance = int(globals.average_gap * fps * 0.7)  # looser to allow fast changes
    else:
        min_distance = int(fps * 0.4)

    min_height = np.std(signal) * std_multiplier

    peaks, properties = find_peaks(
        signal,
        height=min_height,
        distance=min_distance
    )

    return peaks


def compute_intervals(peaks, segment_length, fps):
    """Convert peaks to intervals in seconds, handling first and last interval corrections."""
    if len(peaks) == 0:
        return [segment_length / fps]  # No peaks detected, treat whole segment as one interval

    intervals = np.diff(peaks).tolist()  # Compute intervals between peaks

    # Convert intervals from frames to seconds
    intervals = [i / fps for i in intervals]

    # First interval correction (from start to first peak)
    first_interval = peaks[0] / fps  # From index 0 to first peak
    intervals.insert(0, first_interval)

    # Last interval correction (from last peak to the end)
    last_interval = (segment_length - (peaks[-1] / fps))   # From last peak to segment end
    intervals.append(last_interval)

    return intervals


def merge_intervals(intervals1, intervals2):
    """Merges two sets of intervals by summing the last of the first set with the first of the second set."""
    if len(intervals1) > 0 and len(intervals2) > 0:
        merged_first = intervals1[-1] + intervals2[0]  # Merge last of first set with first of second set
        merged_intervals = np.concatenate([intervals1[:-1], [merged_first], intervals2[1:]])  # Combine properly
    else:
        merged_intervals = np.concatenate([intervals1, intervals2])  # In case one of them is empty

    return merged_intervals


def ar_predict(target_time=10.0):
    """Predict ~10 seconds of intervals, continuing smoothly from past_intervals."""
    intervals = globals.past_intervals
    if len(intervals) < 5:
        return None  # not enough data

    # Remove possibly cut last interval from training
    train_data = intervals[:-1]
    last_interval = intervals[-1]

    # Use dynamic lag (e.g. max 20, or half of training)
    lags = min(20, len(train_data) // 2)
    if len(train_data) <= lags:
        return None

    # Fit AR model
    model = AutoReg(train_data, lags=lags, old_names=False)
    model_fit = model.fit()

    # Predict more than enough (e.g. 20 steps)
    predicted = model_fit.predict(start=len(train_data), end=len(train_data) + 19, dynamic=True)

    # Trim to reach ~10s
    result = []
    total = 0.0
    for val in predicted:
        if total + val >= target_time:
            result.append(target_time - total)
            break
        result.append(val)
        total += val

    # Smooth continuation from last interval
    if result:
        result[0] = result[0] - last_interval
        if result[0] <= 0 and len(result) > 1:
            result = result[1:]
            result[0] -= last_interval

    return np.array(result)


def split_intervals_last5sec(intervals, target_time=5.0):
    total_time = sum(intervals)
    logging.debug("Splitting intervals. Total time: %.3f, target time: %.3f", total_time, target_time)

    if total_time < target_time:
        raise ValueError("Total time is less than target_time for the second part.")

    chunk1, chunk2 = [], []
    sum_time = 0.0

    reversed_intervals = intervals[::-1]
    for i, interval in enumerate(reversed_intervals):
        if sum_time + interval <= target_time:
            chunk2.insert(0, interval)
            sum_time += interval
        else:
            remaining_time = target_time - sum_time
            chunk2.insert(0, remaining_time)
            chunk1 = intervals[:len(intervals) - i - 1] + [interval - remaining_time]
            break

    logging.debug("Split result: chunk1=%s, chunk2=%s", chunk1, chunk2)
    return np.array(chunk1), np.array(chunk2)


def process_peaks(filtered_signal, fps):
    total_length = 15.0
    peaks = detect_peaks(filtered_signal, fps)
    intervals = compute_intervals(peaks, total_length, fps)

    logging.debug("Detected intervals: %s", intervals)

    if globals.past_intervals is None:
        globals.past_intervals = intervals[1:]
    else:
        x0x1_intervals, x2_intervals = split_intervals_last5sec(intervals)
        globals.past_intervals = merge_intervals(globals.past_intervals, x2_intervals)

    predicted_intervals = ar_predict(target_time=10)
    logging.debug("Full predicted intervals: %s", predicted_intervals)

    x3_intervals, x4_intervals = split_intervals_last5sec(predicted_intervals)
    logging.debug("Final x4_intervals: %s", x4_intervals)

    return intervals, x4_intervals

