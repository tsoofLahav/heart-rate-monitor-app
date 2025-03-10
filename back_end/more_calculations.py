import numpy as np

def convert_peaks_to_intervals(peaks, fps, total_frames):
    """
    Convert peak indices into time intervals (gaps between peaks) in seconds,
    including the gaps from the start of the interval to the first peak
    and from the last peak to the end of the interval.

    Parameters:
    - peaks: List or array of detected peak indices.
    - fps: Frames per second of the video.
    - total_frames: Total number of frames in the intensities signal.

    Returns:
    - intervals: List of time intervals (seconds) including start and end gaps.
    """

    if len(peaks) == 0:
        return [total_frames / fps]  # If no peaks, return the whole interval length

    # Convert peak indices to time (seconds)
    peak_times = np.array(peaks) / fps

    # Include gap from start to first peak
    start_gap = peak_times[0]  # Time from 0 to first peak

    # Compute intervals between consecutive peaks
    peak_intervals = np.diff(peak_times).tolist()

    # Include gap from last peak to end of interval
    end_gap = (total_frames / fps) - peak_times[-1]  # Time from last peak to end

    # Combine all intervals
    intervals = [start_gap] + peak_intervals + [end_gap]

    return intervals


def calculate_bpm(intervals):
    """
    Calculate BPM from peak intervals, averaging over the last 3 cycles.

    Parameters:
    - intervals: List of time intervals (seconds) including start and end gaps.

    Returns:
    - bpm: Calculated beats per minute (BPM) as an integer, or None if not enough peaks.
    """

    global bpm_history  # Use global list to store previous BPM values

    if len(intervals) <= 2:
        return None  # Not enough peak-to-peak intervals

    # Remove the first and last intervals (start and end gaps)
    peak_intervals = intervals[1:-1]

    if len(peak_intervals) == 0:
        return None  # No valid peak intervals

    # Compute the average interval between peaks (seconds per beat)
    avg_interval = sum(peak_intervals) / len(peak_intervals)

    # Convert to BPM
    bpm = round(60.0 / avg_interval)  # Round to int

    # Store BPM in history
    bpm_history.append(bpm)

    # First cycle: return immediately
    if len(bpm_history) == 1:
        return bpm

    # Keep only last 3 BPM values
    if len(bpm_history) > 3:
        bpm_history.pop(0)  # Remove oldest value

    # Return the average of the last 3 values (rounded)
    return round(sum(bpm_history) / len(bpm_history))
