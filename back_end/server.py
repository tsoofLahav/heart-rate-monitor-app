from flask import Flask, request, jsonify
import numpy as np
import cv2

app = Flask(__name__)

def moving_average_filter(data, window_size):
    return np.convolve(data, np.ones(window_size) / window_size, mode='valid')

def detect_peaks(signal, dynamic_threshold):
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] > signal[i - 1] and signal[i] > signal[i + 1] and signal[i] > dynamic_threshold:
            peaks.append(i)
    return np.array(peaks)

last_video_last_peak_time = None  # To store the time of the last peak in the previous video

@app.route('/process_video', methods=['POST'])
def process_video():
    global last_video_last_peak_time

    try:
        file = request.files['video']
        video_path = './temp_video.mp4'
        file.save(video_path)

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

        # Prepare signal with moving average filter
        signal = np.array(intensities)
        filtered_signal = moving_average_filter(signal, window_size=5)

        # Dynamic threshold based on the signal's baseline intensity
        baseline = np.mean(filtered_signal)
        dynamic_threshold = baseline * 0.5  # Adjust factor as needed

        # Detect peaks using dynamic threshold
        peaks = detect_peaks(filtered_signal, dynamic_threshold)

        # Calculate BPM
        if len(peaks) > 1:
            peak_intervals = np.diff(peaks) / fps  # Intervals between peaks in seconds
            average_gap = np.mean(peak_intervals)
            heart_rate = (60.0 / average_gap) if average_gap > 0 else 0.0  # Convert to BPM
        else:
            heart_rate = 0.0

        # Store the time of the last peak for the next video
        if len(peaks) > 0:
            last_video_last_peak_time = peaks[-1] / fps
        else:
            last_video_last_peak_time = None

        return jsonify({'heart_rate': heart_rate, 'peaks': peaks.tolist()})

    except Exception as e:
        print(f"Error processing signal: {e}")
        return jsonify({'heart_rate': 0.0, 'peaks': []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)