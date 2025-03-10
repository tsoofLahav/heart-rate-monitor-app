from flask import Flask, request, jsonify
import numpy as np
import cv2
import os
from filter import denoise_ppg
from more_calculations import calculate_bpm, convert_peaks_to_intervals
import ast
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)
bpm_history = []  # Global list to store last 3 BPM values


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

            # ############ part 2: concatenating ###################

            # ############ part 3: filtering ###################
            clean_signal, filtered_signal, aligned_reference, not_reading = denoise_ppg(intensities, fps, reference_signal)

            # handle not reading

            # ############ part 4: peak detection and learning ###################
            # peaks, future_peaks = peak_detection_and_forcast

            # ############ part 5: storage ###################
            # ############ part 6: computing for front ###################
            # part for testing only
            time_stamps = np.arange(len(clean_signal)) / fps
            intensities = intensities[:len(clean_signal)]
            filtered_signal = filtered_signal[:len(clean_signal)]
            aligned_reference = aligned_reference[:len(clean_signal)]

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
