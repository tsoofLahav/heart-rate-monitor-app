import numpy as np
from flask import Flask, request, jsonify
import os
import logging
from classifier import load_mlp_model
from reconstruction import load_reconstruction_model

from video_edit import process_video_frames           # part 2: video -> signal
from filter_and_peaks import denoise_ppg                        # part 4: filter + detect
from predict_model import predict_future_sequence, load_predictor_model           # part 6: prediction
from data_route import save_prediction_to_db          # part 7: store
import globals

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s", force=True)

def setup_video_route(app):
    @app.route('/process_video', methods=['POST'])
    def process_video():
        try:
            # ---------- Part 1: Get video ----------
            # 🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍🤍
            file = request.files.get('video')
            if not file:
                return jsonify({'error': 'No video file received.'}), 400

            video_path = './temp_video.mp4'
            file.save(video_path)
            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                raise Exception("Invalid video file.")

            # ---------- Part 2: Video to signal ----------
            # 🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷🩷
            fps, intensities = process_video_frames(video_path, target_duration=5)
            if not intensities:
                raise Exception("No frames were processed.")

            segment_length = int(5 * fps)
            globals.round_count += 1

            # ---------- Part 3: Concatenate raw signal (10s sliding window) ----------
            # 🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡🧡
            if globals.round_count == 1:
                globals.raw_buffer.extend(intensities)  # first 5s only
                # loading the models at first round
                load_mlp_model()
                load_reconstruction_model()
                load_predictor_model()
                return jsonify({'loading': True})
            else:
                if globals.round_count == 2:
                    globals.raw_buffer.extend(intensities)  # now 10s total
                else:
                    globals.raw_buffer = globals.raw_buffer[segment_length:] + intensities  # slide 5s forward

            # ---------- Part 4: Filter + detect peaks + check signal quality ----------
            # 💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛💛
            clean_signal, filtered_signal, not_reading, peaks_in_window = denoise_ppg(
                globals.raw_buffer, fps)

            if not_reading:
                globals.reset_all()  # also resets raw, peaks, etc.
                return jsonify({'not_reading': True})

            # ---------- Part 5: Append clean peaks using 0.5s overlap logic ----------
            # 💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚💚
            if globals.round_count == 2:
                valid_peaks = [t for t in peaks_in_window if 0.5 <= t < 9.5]
            else:
                valid_peaks = [t for t in peaks_in_window if 4.5 <= t < 9.5]

            # Shift valid_peaks by (5 * (globals.round_count - 2)) seconds
            time_shift = 5 * (globals.round_count - 2)
            valid_peaks_shifted = [t + time_shift for t in valid_peaks]

            # Add to history
            globals.peak_history.extend(valid_peaks_shifted)

            # Keep only the last 20 peaks
            if len(globals.peak_history) > 20:
                globals.peak_history = globals.peak_history[-20:]

            # ---------- Part 6: Predict 30 intervals from last 20 peaks ----------
            # 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
            if len(globals.peak_history) < 20:
                return jsonify({'loading': True})

            past_peaks = globals.peak_history[-20:]

            # Step 1: Convert past peaks to intervals
            past_intervals = [t2 - t1 for t1, t2 in zip(past_peaks[:-1], past_peaks[1:])]

            # Step 2: Predict intervals
            predicted_intervals = predict_future_sequence(past_intervals)

            # ⚠️ New: Add not_reading if prediction total duration < 10.5s
            if sum(predicted_intervals) < 10.5:
                globals.reset_all()
                return jsonify({'not_reading': True})

            # Step 3: Convert intervals to cumulative time points
            last_peak_time = past_peaks[-1]
            predicted_times = []
            current_time = last_peak_time
            for interval in predicted_intervals:
                current_time += interval
                predicted_times.append(current_time)

            # Step 4: Slice next 5s window (two rounds ahead)
            start = (globals.round_count + 1) * 5
            end = start + 5

            future_peaks = [t for t in predicted_times if start <= t < end]

            # Step 5: Shift back to start from 0
            future_peaks_shifted = [t - start for t in future_peaks]

            # ---------- Part 7: Save for local testing ----------
            # 💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙💙
            if globals.testing_mode:
                globals.prediction_buffer.append(future_peaks_shifted)
                response = {
                    'clean_signal': clean_signal.tolist(),
                    'filtered_signal': filtered_signal.tolist(),
                    'peaks_in_window': peaks_in_window
                }

                # Only add prediction after 4 rounds (we need 2+2 rounds to connect)
                if len(globals.prediction_buffer) >= 4:
                    prediction_round_minus3 = globals.prediction_buffer[0]  # oldest
                    prediction_round_minus2 = [t + 5.0 for t in globals.prediction_buffer[1]]  # shifted by +5s

                    connected_prediction = prediction_round_minus3 + prediction_round_minus2

                    # Pop the oldest prediction (round N-3)
                    globals.prediction_buffer.pop(0)

                    response['prediction'] = connected_prediction
                else:
                    # Not enough history yet
                    response['prediction'] = []

                # Return for local testing (early exit, skip part 8)
                return jsonify(response)

            # ---------- Part 8: Save + send to frontend ----------
            # ❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️❤️
            save_prediction_to_db(future_peaks)
            bpm = 60.0 / np.mean(past_intervals)

            return jsonify({
                'prediction': future_peaks_shifted,
                'bpm': bpm
            })
            # 💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜💜
        except Exception as e:
            logging.exception("Unhandled exception:")
            globals.reset_all()
            return jsonify({'server_error': True}), 500
