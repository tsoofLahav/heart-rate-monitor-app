import numpy as np
from scipy.signal import find_peaks
from statsmodels.tsa.ar_model import AutoReg

# Global storage for learning from previous data


def detect_peaks(signal, fps):

    min_distance = int(fps * 0.33)  # Ensure peaks are spaced by at least 0.25s
    prominence = 0.1  # Peak must stand out
    min_height = 0.75  # Minimum height threshold

    # Detect peaks normally
    peaks, properties = find_peaks(signal, height=min_height, distance=min_distance, prominence=prominence)

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


def ar_predict(intervals, target_time=10.0):
    """Predicts intervals until total sum reaches or slightly exceeds target_time."""

    print("Received intervals:", intervals)

    if len(intervals) < 3:  # Ensure there is enough data after trimming
        print("Not enough data for AR model. Returning mean interval.")
        return np.full(10, np.mean(intervals))

    last_interval = intervals[-1]
    target_time = target_time + last_interval

    # Remove first and last interval from training
    intervals = intervals[1:-1] if len(intervals) > 2 else intervals

    print("Intervals after trimming:", intervals)

    lags = max(2, min(4, len(intervals) - 1))  # Ensure at least 2 lags
    print("Using lags:", lags)

    if lags < 1:
        print("Lags too small, returning mean interval.")
        return np.full(10, np.mean(intervals))

    # Train the model
    try:
        model = AutoReg(intervals, lags=lags)
        model_fit = model.fit()
    except Exception as e:
        print("Error fitting AutoReg model:", e)
        return np.full(10, np.mean(intervals))  # Fallback if model fitting fails

    # Predict more steps than needed (e.g., 16 steps)
    num_steps = 16  # Arbitrary large number to exceed target_time
    try:
        predicted_intervals = model_fit.predict(start=len(intervals), end=len(intervals) + num_steps - 1, dynamic=True)
        print("Raw predicted intervals:", predicted_intervals)
    except Exception as e:
        print("Error during prediction:", e)
        return np.full(10, np.mean(intervals))  # Fallback if prediction fails

    # Trim the prediction to exactly match target_time
    total_time = 0.0
    index = 0

    while total_time + predicted_intervals[index] < target_time:
        total_time += predicted_intervals[index]
        index += 1

    predicted_intervals = predicted_intervals[:index]
    predicted_intervals.append(target_time - total_time)
    print("Final intervals before adjustment:", predicted_intervals)

    # Ensure final_intervals is not empty before accessing index 0
    if predicted_intervals:
        if predicted_intervals[0] - last_interval <= 0:
            print("First interval too small, removing it.")
            final_intervals = predicted_intervals[1:] if len(predicted_intervals) > 1 else [target_time]
        else:
            predicted_intervals[0] = predicted_intervals[0] - last_interval

    print("Final intervals after adjustment:", predicted_intervals)
    return np.array(predicted_intervals)


def split_intervals_exactly(intervals, target_time=5.0):
    """Splits a list of intervals (totaling 10s) into two parts of exactly 5s each."""
    chunk1, chunk2 = [], []
    sum_time = 0.0

    for i, interval in enumerate(intervals):
        if sum_time + interval <= target_time:
            chunk1.append(interval)
            sum_time += interval
        else:
            remaining_time = target_time - sum_time
            chunk1.append(remaining_time)  # Cut interval to fit exactly 5s
            chunk2.append(interval - remaining_time)  # Remaining part in chunk2
            chunk2.extend(intervals[i + 1:])  # Add remaining intervals to chunk2
            break  # Stop after reaching 5s

    return np.array(chunk1), np.array(chunk2)


def process_peaks(filtered_signal, fps):
    """Process 15s filtered signal, detect peaks, predict next intervals, and return x4."""

    # Convert to time
    segment_length = 5.0  # Fixed at 5s
    total_length = 15.0  # Full signal

    # Detect peaks and convert to intervals
    peaks = detect_peaks(filtered_signal, fps)
    intervals = compute_intervals(peaks, total_length, fps)

    # **Predict next slightly over 10s**
    predicted_intervals = ar_predict(intervals, target_time=10)

    # **Trim predicted intervals into 5s chunks**
    x3_intervals, x4_intervals = split_intervals_exactly(predicted_intervals, segment_length)

    # Save x1, x2, x3 for learning
    # previous_intervals = np.concatenate([x1_intervals, x2_intervals, x3_intervals])

    return intervals, x4_intervals  # Return x4 to main page

