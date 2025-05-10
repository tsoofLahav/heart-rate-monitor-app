import numpy as np
from flask import Flask, request, jsonify
import os
from filter import denoise_ppg
from peak_predict import process_peaks, merge_intervals
from more_calculations import compute_bpm_hrv
from create_reference import create_ppg
import ast
import globals
from video_edit import process_video_frames
import logging
from data_route import save_prediction_to_db



logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s", force=True)


def setup_video_route(app):
    @app.route('/process_video', methods=['POST'])
    def process_video():
        try:
# ############ part 1: video -> intensities ###################
            file = request.files.get('video')
            if not file:
                return jsonify({'error': 'No video file received.'}), 400

            # Save video file
            video_path = './temp_video.mp4'
            file.save(video_path)

            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                raise Exception("Invalid video file.")

            # Process video: adjust FPS & extract intensities
            fps, intensities = process_video_frames(video_path, target_duration=5)

            if not intensities:
                raise Exception("No frames were processed.")

# ############ part 2: concatenating ###################
            segment_length = int(5 * fps)

            globals.round_count += 1
            if globals.round_count == 1:
                globals.concatenated_intensities.extend(intensities)
                return jsonify({'loading': True})
            else:
                if globals.round_count == 2:
                    globals.concatenated_intensities.extend(intensities)
                else:
                    globals.concatenated_intensities = globals.concatenated_intensities[segment_length:] + intensities

# ############ part 3: filtering ####################
                if globals.reference_signal is None:
                    with open("reference.txt", "r") as file:
                        globals.reference_signal = ast.literal_eval(file.read())

                clean_signal, filtered_signal, not_reading = denoise_ppg(
                    globals.concatenated_intensities, fps, globals.reference_signal)

                # handle not reading.
                if not_reading:
                    globals.concatenated_intensities = []
                    globals.round_count = 0
                    globals.history = []
                    globals.past_intervals = None
                    globals.average_gap = None
                    return jsonify({'not_reading': True})

# ############ part 4: peak detection and learning ###################
                intervals, predicted_intervals = process_peaks(fps)
                # time_stamps = np.arange(len(clean_signal)) / fps
                # globals.average_gap = np.mean(intervals[1:-1])
                # if globals.round_count < 5:
                #     globals.list_intervals_lists.append(predicted_intervals)
                #     # Return processed data as a JSON response
                #     return jsonify({
                #         'final': clean_signal.tolist(),
                #         'filtered': filtered_signal.tolist(),
                #         'intervals': intervals.tolist(),
                #         'time_stamps': time_stamps.tolist()
                #     })
                # else:
                #     globals.list_intervals_lists.append(predicted_intervals)
                #     concatenated_intervals = merge_intervals(globals.list_intervals_lists[-4],
                #                                              globals.list_intervals_lists[-3])
                #     # Return processed data as a JSON response
                #     return jsonify({
                #         'final': clean_signal.tolist(),
                #         'filtered': filtered_signal.tolist(),
                #         'intervals': intervals.tolist(),
                #         'predicted_intervals': concatenated_intervals.tolist(),
                #         'time_stamps': time_stamps.tolist()
                #     })
############ part 5: computations and storage ###################
                save_prediction_to_db(predicted_intervals)
                bpm = compute_bpm_hrv(intervals)
############ part 6: send to front ###################
                return jsonify({
                    'intervals': predicted_intervals.tolist(),
                    'bpm': bpm
                })

        except Exception as e:
            logging.exception("Unhandled exception:")
            globals.concatenated_intensities = []
            globals.round_count = 0
            globals.history = []
            globals.past_intervals = None
            globals.average_gap = None
            return jsonify({'server_error': True}), 500
