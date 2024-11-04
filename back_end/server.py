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

# Variables to keep track of peak timings
last_video_last_peak_time = None  # Time of last peak in the previous interval
last_interval_end_time = None     # Time at the end of the previous interval

@app.route('/process_video', methods=['POST'])
def process_video():
    global last_video_last_peak_time, last_interval_end_time

    try:
        # Receive video file from request
        file = request.files['video']
        video_path = './temp_video.mp4'
        file.save(video_path)

        # Open video and read frames
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        video_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps

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

        # Calculate dynamic threshold and detect peaks
        baseline = np.mean(filtered_signal)
        dynamic_threshold = baseline * 0.5
        peaks = detect_peaks(filtered_signal, dynamic_threshold)

        # Calculate intra-interval gaps (gaps between peaks within this interval)
        if len(peaks) > 1:
            intra_interval_gaps = np.diff(peaks) / fps
            average_intra_gap = np.mean(intra_interval_gaps)
        else:
            average_intra_gap = 0.0

        # Calculate inter-interval gap if applicable
        if last_video_last_peak_time is not None:
            # Time from the last peak of the previous interval to the end of that interval
            end_of_last_interval_gap = last_interval_end_time - last_video_last_peak_time

            # Time from the start of this interval to the first peak in this interval
            start_of_this_interval_gap = (peaks[0] / fps) if len(peaks) > 0 else video_duration

            # Total inter-interval gap
            inter_interval_gap = end_of_last_interval_gap + start_of_this_interval_gap
        else:
            inter_interval_gap = 0.0

        # Calculate overall average gap by including inter and intra interval gaps
        if average_intra_gap > 0 and inter_interval_gap > 0:
            combined_gap = np.mean([average_intra_gap, inter_interval_gap])
            heart_rate = 60.0 / combined_gap
        elif average_intra_gap > 0:
            heart_rate = 60.0 / average_intra_gap
        else:
            heart_rate = 0.0

        # Update for the next interval
        if len(peaks) > 0:
            last_video_last_peak_time = peaks[-1] / fps
        else:
            last_video_last_peak_time = None
        last_interval_end_time = video_duration

        return jsonify({'heart_rate': heart_rate, 'peaks': peaks.tolist()})

    except Exception as e:
        print(f"Error processing signal: {e}")
        return jsonify({'heart_rate': 0.0, 'peaks': []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
