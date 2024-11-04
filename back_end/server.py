from flask import Flask, request, jsonify
import numpy as np
import cv2

app = Flask(__name__)

# Moving average filter
def moving_average_filter(data, window_size):
    return np.convolve(data, np.ones(window_size) / window_size, mode='valid')

# Peak detection function
def detect_peaks(signal, dynamic_threshold):
    peaks = []
    for i in range(1, len(signal) - 1):
        if signal[i] > signal[i - 1] and signal[i] > signal[i + 1] and signal[i] > dynamic_threshold:
            peaks.append(i)
    return np.array(peaks)

# Variables to accumulate peaks and track time
cumulative_peaks = []  # Store all peaks across multiple chunks
last_video_last_peak_time = None  # To store the time of the last peak in the previous video

@app.route('/process_video', methods=['POST'])
def process_video():
    global last_video_last_peak_time, cumulative_peaks

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

        # Apply moving average filter
        signal = np.array(intensities)
        filtered_signal = moving_average_filter(signal, window_size=5)

        # Dynamic threshold based on the signal's baseline intensity
        baseline = np.mean(filtered_signal)
        dynamic_threshold = baseline * 0.5  # Existing threshold

        # Detect peaks using dynamic threshold
        peaks = detect_peaks(filtered_signal, dynamic_threshold)

        # Convert peaks to time values based on fps and add to cumulative peaks
        peaks_in_time = [peak / fps for peak in peaks]
        if last_video_last_peak_time:
            peaks_in_time = [last_video_last_peak_time + time for time in peaks_in_time]

        # Update last peak time for continuity
        if peaks_in_time:
            last_video_last_peak_time = peaks_in_time[-1]

        # Add peaks to cumulative list
        cumulative_peaks.extend(peaks_in_time)

        # Calculate BPM based on cumulative peaks
        if len(cumulative_peaks) > 1:
            peak_intervals = np.diff(cumulative_peaks)  # Time intervals between peaks
            average_gap = np.mean(peak_intervals)
            heart_rate = (60.0 / average_gap) if average_gap > 0 else 0.0  # Convert to BPM
        else:
            heart_rate = 0.0

        # Limit cumulative peaks to avoid memory overload (e.g., last 10 seconds)
        max_time_window = 10.0  # seconds
        cumulative_peaks = [t for t in cumulative_peaks if last_video_last_peak_time - t <= max_time_window]

        return jsonify({'heart_rate': heart_rate, 'peaks': peaks.tolist()})

    except Exception as e:
        print(f"Error processing signal: {e}")
        return jsonify({'heart_rate': 0.0, 'peaks': []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
