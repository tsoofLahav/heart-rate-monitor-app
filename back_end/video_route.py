from flask import request, jsonify
import os
import numpy as np
import cv2
from peak_detection import peaks_detection


def setup_video_route(app):
    @app.route('/process_video', methods=['POST'])
    def process_video():
        try:
            # Receive video file from request
            file = request.files.get('video')
            if not file:
                return jsonify({'error': 'No video file received.'}), 400

            print(f"Received file: {file.filename}, Content-Type: {file.content_type}")

            # Save video file
            video_path = './temp_video.mp4'
            file.save(video_path)

            # Check if the file exists and has a valid size
            if not os.path.exists(video_path):
                raise Exception("Video file was not saved successfully.")
            file_size = os.path.getsize(video_path)
            print(f"Video file size: {file_size} bytes")
            if file_size == 0:
                raise Exception("Video file is empty.")

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
                try:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    intensities.append(np.mean(gray))
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    continue
            cap.release()

            # Check if intensities were successfully captured
            if not intensities:
                raise Exception("No frames were processed from the video.")

            # Perform peak detection
            peaks, bpm, hrv, startnew = peaks_detection(intensities, fps)
            differences = []

            if peaks != [-1]:
                peaks.insert(0, 0)
                peaks.append(1)
                for i in range(len(peaks) - 1):
                    differences.append(peaks[i + 1] - peaks[i])
            else:
                differences.append(-1)

            return jsonify({'heart_rate': bpm, 'average_gap': hrv, 'peaks': differences, 'startNew': startnew})

        except Exception as e:
            print(f"Error processing signal: {e}")
            return jsonify({
                'error': f'Error processing signal: {str(e)}',
                'heart_rate': 0.0,
                'peaks': [],
                'startNew': False
            }), 500
