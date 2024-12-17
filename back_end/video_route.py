from flask import request, jsonify
import numpy as np
import cv2
from peak_detection import peaks_detection


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

            if not cap.isOpened():
                raise Exception("Failed to open video file.")

            intensities = []
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                intensities.append(np.mean(gray))
            cap.release()

            peaks, bpm, hrv, startnew = peaks_detection(intensities, fps)
            differences = []

            if peaks != [-1]:
                peaks.insert(0, 0)
                peaks.append(1)
                for i in range(len(peaks) - 1):
                    differences.append(peaks[i+1] - peaks[i])
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

