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
    logger.info(f"Raw Intensities: {filtered_signal}")

    # Apply band-pass filter
    filtered_signal = peak_detection.bandpass_filter(filtered_signal, fps)
    logger.info(f"After Band-Pass Filter: {filtered_signal}")

    # Normalize
    filtered_signal = peak_detection.normalize_signal(filtered_signal)
    logger.info(f"Normalized Signal: {filtered_signal}")

    # Compute baseline and std deviation
    baseline = np.mean(filtered_signal)
    std_dev = np.std(filtered_signal)
    logger.info(f"Baseline: {baseline}, Std Dev: {std_dev}")

    # Dynamic threshold and peak detection
    peaks = peak_detection.detect_peaks(filtered_signal, fps)
    logger.info(f"Detected Peaks: {peaks}")

    total_duration = len(filtered_signal) / fps
    logger.info(f"Total Duration: {total_duration}")

    # Create new data to send to front end, using the peaks, using create_data file
    new_start, new_list, bpm = create_data.process_peaks(peaks, fps, total_duration)

    return False, new_list, new_start, bpm
