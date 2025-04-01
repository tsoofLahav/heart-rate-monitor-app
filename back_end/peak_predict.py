import numpy as np
from scipy.signal import find_peaks
from statsmodels.tsa.ar_model import AutoReg
import math
import globals
import logging

logging.basicConfig(level=logging.DEBUG)


def detect_peaks(signal, fps, std_multiplier=0.33):
    signal = np.array(signal)

    if globals.average_gap:
        min_distance = int(globals.average_gap * fps * 0.7)  # looser to allow fast changes
    else:
        min_distance = int(fps * 0.4)

    min_height = np.std(signal) * std_multiplier
    prominence = min_height * 0.33

    peaks, properties = find_peaks(
        signal,
        height=min_height,
        distance=min_distance,
        prominence=prominence,
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
    """Predicts intervals until total sum reaches or slightly exceeds target_time."""
    intervals = globals.past_intervals
    last_interval = intervals[-1]
    target_time = target_time + last_interval

    n = int(math.sqrt(len(intervals)))

    # Remove first and last interval from training
    intervals = intervals[:-1]  # remove the last interval
    if len(intervals) < 3:
        return np.array([])  # not enough data to predict reliably

    n = int(math.sqrt(len(intervals)))
    lags = min(n, len(intervals) - 2)  # ensure at least 2 more points than lags
    print(f"len(intervals): {len(intervals)}, lags: {lags}")

    model = AutoReg(intervals, lags=lags)
    model_fit = model.fit()

    # Predict more steps than needed (e.g., 16 steps)
    num_steps = 24  # Arbitrary large number to exceed target_time
    predicted_intervals = model_fit.predict(start=len(intervals), end=len(intervals) + num_steps - 1, dynamic=True)
    print("Predicted intervals:", predicted_intervals)
    print("Total predicted time:", np.sum(predicted_intervals))

    # Trim the prediction to exactly match target_time
    total_time = 0.0
    index = 0

    while total_time + predicted_intervals[index] < target_time:
        total_time += predicted_intervals[index]
        index += 1

    predicted_intervals = predicted_intervals[:index]
    predicted_intervals = np.append(predicted_intervals, target_time - total_time)

    if predicted_intervals[0] - last_interval <= 0:
        last_interval = last_interval - predicted_intervals[0]
        predicted_intervals = predicted_intervals[1:]
        predicted_intervals[0] = predicted_intervals[0] - last_interval
    else:
        predicted_intervals[0] = predicted_intervals[0] - last_interval

    return np.array(predicted_intervals)


def split_intervals_last5sec(intervals, target_time=5.0):
    """Splits a list of intervals so that the second part is exactly 5s,
    and the first part is whatever is before that."""
    total_time = sum(intervals)
    if total_time < target_time:
        raise ValueError("Total time is less than target_time for the second part.")

    chunk1, chunk2 = [], []
    sum_time = 0.0

    # Start from the end and work backward to get the last 5 seconds.
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

    return np.array(chunk1), np.array(chunk2)


def process_peaks(filtered_signal, fps):
    """Process 15s filtered signal, detect peaks, predict next intervals, and return x4."""

    # Convert to time
    segment_length = 5.0  # Fixed at 5s
    total_length = 15.0  # Full signal

    # Detect peaks and convert to intervals
    peaks = detect_peaks(filtered_signal, fps)
    intervals = compute_intervals(peaks, total_length, fps)

    if globals.past_intervals is None:
        globals.past_intervals = intervals[1:]
    else:
        x0x1_intervals, x2_intervals = split_intervals_last5sec(intervals)
        globals.past_intervals = merge_intervals(globals.past_intervals, x2_intervals)

    # **Predict next slightly over 10s**
    predicted_intervals = ar_predict(target_time=10)

    # **Trim predicted intervals into 5s chunks**
    x3_intervals, x4_intervals = split_intervals_last5sec(predicted_intervals)

    return intervals, x4_intervals  # Return x4 to main page

