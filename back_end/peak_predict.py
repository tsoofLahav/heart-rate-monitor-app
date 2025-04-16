import numpy as np
from scipy.signal import find_peaks
from statsmodels.tsa.arima.model import ARIMA
import globals


def detect_peaks(signal, fps, std_multiplier=0.4):
    signal = np.array(signal)
    min_height = np.std(signal) * std_multiplier

    max_peaks, _ = find_peaks(signal, height=min_height)
    min_peaks, _ = find_peaks(-signal, height=min_height)

    max_peaks = list(max_peaks)
    min_peaks = sorted(min_peaks)
    valid_peaks = []

    # Create boundaries: start → min[0], min[0]→min[1], ..., min[-1]→end
    boundaries = [-1] + min_peaks + [len(signal)]

    for i in range(len(boundaries) - 1):
        start, end = boundaries[i], boundaries[i + 1]
        in_range = [p for p in max_peaks if start < p < end]
        if in_range:
            valid_peaks.append(in_range[0])

    return np.array(valid_peaks)


def compute_intervals(peaks, segment_length, fps):
    """Convert peaks to intervals in seconds, handling first and last interval corrections."""
    if len(peaks) == 0:
        return [segment_length / fps]  # No peaks detected, treat whole segment as one interval

    intervals = np.diff(peaks).tolist()  # Compute intervals between peaks.

    # Convert intervals from frames to seconds
    intervals = [i / fps for i in intervals]

    # First interval correction (from start to first peak)
    first_interval = peaks[0] / fps  # From index 0 to first peak
    intervals.insert(0, first_interval)

    # Last interval correction (from last peak to the end)
    last_interval = (segment_length - (peaks[-1] / fps))   # From last peak to segment end
    intervals.append(last_interval)

    return intervals


def merge_intervals(intervals1, intervals2, fps=24):
    """Merge intervals across a cut point, skipping short double-peak intervals."""
    if len(intervals1) > 0 and len(intervals2) > 0:
        gap_sum = intervals1[-1] + intervals2[0]
        if gap_sum < 0.2 * fps and len(intervals2) > 1:
            merged_first = intervals2[0] + intervals2[1]  # merge into the next one only
            merged_intervals = np.concatenate([
                intervals1,
                [merged_first],
                intervals2[2:]
            ])
        else:
            merged_first = intervals1[-1] + intervals2[0]
            merged_intervals = np.concatenate([
                intervals1[:-1],
                [merged_first],
                intervals2[1:]
            ])
    else:
        merged_intervals = np.concatenate([intervals1, intervals2])

    return merged_intervals


def ar_predict(target_time=10.0):
    """Predicts intervals until total sum reaches or slightly exceeds target_time using ARIMA."""
    intervals = globals.past_intervals[-30:]

    last_interval = intervals[-1]
    target_time += last_interval
    train_data = intervals[:-1]

    if len(train_data) <= 5:
        return None

    # ARIMA(p=8, d=0, q=0) is equivalent to AR with 8 lags
    p = min(8, (len(train_data) // 2) - 1)
    d = 0
    q = 6  # allows small error correction

    model = ARIMA(train_data, order=(p, d, q))
    model_fit = model.fit()

    predicted = model_fit.forecast(steps=20)

    predicted[0] -= last_interval
    if predicted[0] <= 0:
        target_time += predicted[0]
        predicted[0] = 0

    total = 0.0
    index = 0
    while index < len(predicted) and total + predicted[index] < target_time:
        total += predicted[index]
        index += 1

    result = predicted[:index]
    if index < len(predicted):
        result = np.append(result, target_time - total)

    return np.array(result)


def split_intervals_last5sec(intervals, target_time=5.0):
    total_time = sum(intervals)

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

    return np.array(chunk1), np.array(chunk2)


def process_peaks(filtered_signal, fps):
    peaks = detect_peaks(filtered_signal, fps)
    intervals = compute_intervals(peaks, 10, fps)
    print(f"intervals:", str(intervals))
    if globals.past_intervals is None:
        globals.past_intervals = intervals[1:]
    else:
        x1_intervals, x2_intervals = split_intervals_last5sec(intervals)
        globals.past_intervals = merge_intervals(globals.past_intervals, x2_intervals)

    predicted_intervals = ar_predict(target_time=10)

    x3_intervals, x4_intervals = split_intervals_last5sec(predicted_intervals)

    return intervals, x4_intervals

