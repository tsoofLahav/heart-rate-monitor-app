from flask import Flask, request, jsonify
import numpy as np
import cv2
from utils.peak_detection import peaks_detection


def setup_video_route(app):
    @app.route('/process_video', methods=['POST'])
    def process_video():

        try:
            # Receive video file from request
            file = request.files['video']
            video_path = './temp_video.mp4'
            file.save(video_path)

            # Open video and read frames
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)

            intensities = []
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                intensities.append(np.mean(gray))
            cap.release()

            peaks, bpm, hrv = peaks_detection(intensities, fps)

            return jsonify({'heart_rate': bpm, 'average_gap': hrv, 'peaks': peaks.tolist()})

        except Exception as e:
            print(f"Error processing signal: {e}")
            return jsonify({'heart_rate': 0.0, 'peaks': []})
