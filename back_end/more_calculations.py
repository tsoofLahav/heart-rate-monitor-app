import numpy as np
from data_route import store_measurement_internal, get_current_session_id
import globals


def compute_bpm_hrv(intervals):
    """Computes BPM and HRV from interval data and stores them in the database."""
    if len(intervals) < 3:
        raise ValueError("Not enough intervals to compute BPM and HRV")

    # Remove first and last intervals
    valid_intervals = intervals[1:-1]

    # Compute BPM
    avg_interval = np.mean(valid_intervals)
    bpm = 60 / avg_interval if avg_interval > 0 else 0
    globals.average_gap = avg_interval
    # Compute HRV (Standard deviation of NN intervals)
    hrv = np.std(valid_intervals)
    session_id = get_current_session_id()
    # Store in DB
    store_measurement_internal(session_id, bpm, hrv)

    return bpm
