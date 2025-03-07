from flask import Flask, request, jsonify
import numpy as np
import cv2
import os
from filter import denoise_ppg
import ast
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
bpm_history = []  # Global list to store last 3 BPM values


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


def setup_video_route(app):
    @app.route('/process_video', methods=['POST'])
    def process_video():
        try:
            # Receive video file from request
            file = request.files.get('video')
            if not file:
                return jsonify({'error': 'No video file received.'}), 400

            # Save video file
            video_path = './temp_video.mp4'
            file.save(video_path)

            # Check if the file exists and has a valid size
            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                raise Exception("Invalid video file.")

            # Open video with OpenCV
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Failed to open video file with OpenCV.")

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Define center and radius of the circular ROI
            center_x, center_y = frame_width // 2, frame_height // 2
            radius = min(center_x, center_y) // 2  # Adjust the divisor to change ROI size

            # Create a circular mask
            Y, X = np.ogrid[:frame_height, :frame_width]
            dist_from_center = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
            mask = dist_from_center <= radius

            # Process video frames (Extract green channel intensity within ROI)
            intensities = []
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Extract green channel
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Apply mask to isolate circular ROI
                roi_values = gray_frame[mask]

                # Compute average intensity within the ROI
                mean_intensity = np.mean(roi_values)
                intensities.append(-mean_intensity)  # Invert intensity

            cap.release()

            # Check if intensities were successfully captured
            if not intensities:
                raise Exception("No frames were processed from the video.")

            with open("reference.txt", "r") as file:
                reference_signal = ast.literal_eval(file.read())  # Convert string to list

            # intervals = convert_peaks_to_intervals(peaks, fps, len(intensities))

            # bpm = calculate_bpm(intervals)
            clean_signal, filtered_signal, aligned_reference = denoise_ppg(intensities, fps, reference_signal)
            time_stamps = np.arange(len(intensities)) / fps

            # Return processed data as a JSON response
            return jsonify({
                'filtered': filtered_signal.tolist(),
                'final': clean_signal.tolist(),
                'reference': aligned_reference.tolist(),
                'intensities': intensities,
                'time_stamps': time_stamps.tolist()
            })
            # return jsonify({
            #     'intervals': intervals,
            #     'bpm': bpm,
            #     'not_reading': False
            # })

        except Exception as e:
            logging.error("Error processing PPG:\n%s", traceback.format_exc())
            return jsonify({'server_error': True}), 500
