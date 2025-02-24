from flask import Flask, request, jsonify
import numpy as np
import cv2
import os
import logging
import test_methods  # Ensure this module is available for detect_pulse function

logging.basicConfig(level=logging.ERROR)

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
                green_channel = frame[:, :, 1]

                # Apply mask to isolate circular ROI
                roi_values = green_channel[mask]

                # Compute average intensity within the ROI
                mean_intensity = np.mean(roi_values)
                intensities.append(mean_intensity)

            cap.release()

            # Check if intensities were successfully captured
            if not intensities:
                raise Exception("No frames were processed from the video.")

            # Detect pulse using the extracted intensities
            peaks, bpm, not_reading, intensities, time_stamps = test_methods.detect_pulse(intensities, fps)

            # Return the ppg_data as a JSON response
            return jsonify({
                'not_reading': not_reading,
                'heart_rate': bpm,
                'peaks': peaks,
                'intensities': intensities,
                'time_stamps': time_stamps
            })

        except Exception as e:
            logging.error(f"Error processing video: {str(e)}")
            return jsonify({'server_error': True}), 500
