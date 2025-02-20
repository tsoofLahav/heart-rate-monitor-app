import numpy as np
import peak_detection
import create_data
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def detect_pulse(intensities, fps):
    logger.info("\n--- Detecting Pulse ---")

    # Process signal before peak detection
    filtered_signal = np.array(intensities)

    # Detect unstable reading
    # not_reading = peak_detection.detect_unstable_reading(filtered_signal, fps)
    # logger.info(f"Unstable Reading Detected: {not_reading}")
    # if not_reading:
    #     return True, [], False, 0.0

    # Apply band-pass filter
    filtered_signal = peak_detection.bandpass_filter(filtered_signal, fps)

    # Normalize
    filtered_signal = peak_detection.normalize_signal(filtered_signal)
    logger.info(f"Normalized Signal: {filtered_signal[:10]}... (showing first 10 values)")

    # Compute baseline and std deviation
    # baseline = np.mean(filtered_signal)
    # std_dev = np.std(filtered_signal)

    # Dynamic threshold and peak detection
    # dynamic_threshold = baseline + (0.2 * std_dev)
    peaks = peak_detection.detect_peaks(filtered_signal, fps)

    logger.info(f"Detected Peaks: {peaks}")

    total_duration = len(filtered_signal) / fps

    # Create new data to send to front end, using the peaks, using create_data file
    new_start, new_list, bpm = create_data.process_peaks(peaks, fps, total_duration)

    logger.info(f"New Start: {new_start}, Intervals: {new_list}, BPM: {bpm}")

    return False, new_list, new_start, bpm
