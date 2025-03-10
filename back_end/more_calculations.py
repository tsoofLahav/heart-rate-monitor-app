
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
