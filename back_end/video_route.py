from flask import request, jsonify
import os
import numpy as np
import cv2
import logging
import process_data
import traceback

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
            fps = cap.get(cv2.CAP_PROP_FPS)
            if not cap.isOpened():
                raise Exception("Failed to open video file with OpenCV.")

            # Process video frames
            intensities = []
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                intensities.append(np.mean(gray))
            cap.release()

            # Check if intensities were successfully captured
            if not intensities:
                raise Exception("No frames were processed from the video.")

            return jsonify({"fps": fps}), 200

            try:
                not_reading, intervals, new_start, bpm = process_data.detect_pulse(intensities, fps)
            except Exception as e:
                error_message = traceback.format_exc()
                logging.error(f"detect_pulse() crashed: {error_message}")
                return jsonify({'server_error': True, 'error_message': error_message}), 500

            if not not_reading:
                return jsonify(
                    {'not_reading': not_reading, 'heart_rate': bpm, 'intervals': intervals, 'startNew': new_start})
            else:
                return jsonify(
                    {'not_reading': True, 'heart_rate': -1, 'intervals': [], 'startNew': False})


        except Exception as e:

            logging.error(f"Error processing video: {str(e)}")  # Logs the error to the backend logs
            return jsonify({'server_error': True}), 500  # Sends only a boolean flag to the frontend
