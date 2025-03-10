import numpy as np
from scipy.signal import find_peaks
from statsmodels.tsa.ar_model import AutoReg

# Global storage for learning from previous data
previous_intervals = []
previous_end_had_peak = False  # Global flag to handle repeated peaks


def detect_peaks(signal, fps):
    """Detect peaks in the signal with additional handling for edges."""
    global previous_end_had_peak

    min_distance = int(fps * 0.25)  # Avoid peaks too close
    peaks, _ = find_peaks(signal, height=0, distance=min_distance, prominence=0.1)

    # Handle edge cases for start and end
    if len(peaks) > 0:
        if signal[0] > signal[1]:  # First sample is a local max
            peaks = np.insert(peaks, 0, 0)

        if signal[-1] > signal[-2]:  # Last sample is a local max
            peaks = np.append(peaks, len(signal) - 1)
            previous_end_had_peak = True  # Flag to check in the next interval
        else:
            previous_end_had_peak = False

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
    last_interval = (segment_length - peaks[-1]) / fps  # From last peak to segment end
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


def ar_predict(intervals, steps=5):
    """Predicts next intervals using an Autoregressive model without error correction."""
    if len(intervals) < 5:  # Not enough data to train AR model
        return np.full(steps, np.mean(intervals))  # Default to mean interval

    # Train AutoRegressive model on past intervals
    lags = min(3, len(intervals) - 1)
    model = AutoReg(intervals, lags=lags)
    model_fit = model.fit()

    # Predict next intervals
    predicted_intervals = model_fit.predict(len(intervals), len(intervals) + steps - 1)

    return predicted_intervals


def process_peaks(filtered_signal, fps):
    """Process 15s filtered signal, detect peaks, predict next intervals, and return x4."""
    global previous_intervals, previous_end_had_peak

    # Split 15s signal into 5s segments
    segment_length = int(5 * fps)
    x0 = filtered_signal[:segment_length]
    x1 = filtered_signal[segment_length:2 * segment_length]
    x2 = filtered_signal[2 * segment_length:]

    # Detect peaks in each segment
    peaks_x0 = detect_peaks(x0, fps)
    peaks_x1 = detect_peaks(x1, fps)
    peaks_x2 = detect_peaks(x2, fps)

    # Convert peaks to intervals
    intervals_x0 = compute_intervals(peaks_x0, segment_length, fps)
    intervals_x1 = compute_intervals(peaks_x1, segment_length, fps)
    intervals_x2 = compute_intervals(peaks_x2, segment_length, fps)

    # Merge overlapping intervals across segment boundaries
    merged_x0_x1 = merge_intervals(intervals_x0, intervals_x1)
    merged_x1_x2 = merge_intervals(intervals_x1, intervals_x2)

    # Use only the merged x0-x2 intervals for prediction
    all_intervals = merge_intervals(merged_x0_x1, intervals_x2)

    # Predict next intervals (x3, x4)
    predicted_intervals = ar_predict(all_intervals, steps=len(intervals_x1) + len(intervals_x2))

    # Save x1, x2, x3 for next round learning
    # previous_intervals = merge_intervals(merged_x1_x2, predicted_intervals[:len(intervals_x1)])
    previous_end_had_peak = False

    return all_intervals, predicted_intervals[len(intervals_x1):]  # Return x4 to the main page
