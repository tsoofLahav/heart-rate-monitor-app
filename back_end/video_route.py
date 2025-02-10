from flask import request, jsonify
import os
import numpy as np
import cv2

from bpm_and_hrv import BPMAndHRVCalculator

bpm_hrv_calculator = BPMAndHRVCalculator()
from peak_detection import detect_pulse

ave_gap = 1


def setup_video_route(app):
    @app.route('/process_video', methods=['POST'])
    def process_video():
        global ave_gap
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

            # Perform peak detection
            not_reading, intervals_list, new_start = detect_pulse(intensities, fps, ave_gap)

            bpm, hrv, ave_gap = bpm_hrv_calculator.calculate(intervals_list, new_start, not_reading)

            return jsonify(
                {'not_reading': not_reading, 'heart_rate': bpm, 'average_gap': ave_gap, 'intervals': intervals_list,
                 'startNew': new_start})

        except Exception as e:
            return jsonify(
                {'error': f'Error processing signal: {str(e)}', 'heart_rate': 0.0, 'peaks': [], 'startNew': False}), 500
