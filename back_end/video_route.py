from flask import Flask, request, jsonify
import os
from filter import denoise_ppg
from peak_predict import process_peaks
from more_calculations import compute_bpm_hrv
import ast
import traceback
import globals
from video_edit import process_video_frames
import logging

logging.basicConfig(level=logging.DEBUG)


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
            fps, intensities = process_video_frames(video_path)

            if not intensities:
                raise Exception("No frames were processed.")

# ############ part 2: concatenating ###################
            segment_length = int(5 * fps)

            globals.round_count += 1
            if globals.round_count < 3:
                globals.concatenated_intensities.extend(intensities)
                return jsonify({'loading': True})
            else:
                if globals.round_count == 3:
                    globals.concatenated_intensities.extend(intensities)
                else:
                    globals.concatenated_intensities = globals.concatenated_intensities[segment_length:] + intensities

# ############ part 3: filtering ###################
                with open("reference.txt", "r") as file:
                    reference_signal = ast.literal_eval(file.read())  # Convert string to list

                clean_signal, filtered_signal, not_reading = denoise_ppg(globals.concatenated_intensities, fps,
                                                                         reference_signal)

                # handle not reading
                if not_reading:
                    globals.concatenated_intensities = []
                    return jsonify({'not_reading': True})

# ############ part 4: peak detection and learning ###################
                intervals, predicted_intervals = process_peaks(clean_signal, fps)

# ############ part 5: computations and storage ###################
                bpm = compute_bpm_hrv(intervals)
# ############ part 6: send to front ###################
                return jsonify({
                    'intervals': predicted_intervals,
                    'bpm': bpm
                })

        except Exception as e:
            logging.error("Error processing PPG:\n%s", traceback.format_exc())
            return jsonify({'server_error': True}), 500
