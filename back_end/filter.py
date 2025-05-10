from scipy.signal import butter, sosfiltfilt
from scipy.interpolate import interp1d
import numpy as np
import globals
from scipy.signal import find_peaks
from sklearn.linear_model import Ridge
from fastdtw import fastdtw
import sys


def split_by_minima(signal, fs):
    std = np.std(signal)
    distance = int(0.35 * fs)
    peaks, _ = find_peaks(-signal, height=0.67 * std, distance=distance)
    edges = [0] + list(peaks) + [len(signal)]
    return [signal[edges[i]:edges[i+1]] for i in range(len(edges)-1)]


def butter_bandpass_filter(signal, fs, lowcut=0.8, highcut=3.0, order=6):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def extrapolate_to_length(y, target_length):
    y = np.array(y, dtype=np.float32)
    current_length = len(y)

    if current_length == target_length:
        return y

    x = np.linspace(0, 1, current_length)
    x_new = np.linspace(0, 1, target_length)
    return np.interp(x_new, x, y)


def pattern_filter(fps, noisy_signal, reference_signal, match_threshold=10):
    segments = split_by_minima(noisy_signal, fps)
    output = []
    buffer = []
    not_reading = False

    for i, chunk in enumerate(segments):
        if i == 0 or i == len(segments) - 1:
            output.append(chunk)
            continue
        if globals.average_gap is not None:
            reference_signal = extrapolate_to_length(reference_signal, int(globals.average_gap*fps))
        dtw_distance, _ = fastdtw(chunk, reference_signal)
        # Width difference (normalized)
        width_diff = abs(len(chunk) - len(reference_signal)) / fps
        # Amplitude difference (normalized)
        amp_diff = abs(np.std(chunk) - np.std(reference_signal)) / (np.std(reference_signal) + 1e-8)
        # Weighted combination
        distance = 0.3 * dtw_distance + 30 * width_diff + 3 * amp_diff
        print("distance:", distance)
        sys.stdout.flush()

        if distance <= match_threshold:
            if buffer:
                length = len(buffer)
                context = np.concatenate((globals.history, *output))[-120:]
                output.append(fast_predict_next_segment(context, length))
                buffer.clear()
            output.append(chunk)
        else:
            buffer.extend(chunk)
        if len(buffer) >= 72:
            not_reading = True

    if len(buffer) >= 72:
        not_reading = True
    if buffer:
        length = len(buffer)
        context = np.concatenate((globals.history, *output))[-120:]
        output.append(fast_predict_next_segment(context, length))

    return np.concatenate(output), not_reading


def fast_predict_next_segment(history, length):
    history = np.array(history[-120:], dtype=np.float32)
    if len(history) < 25:
        return np.zeros(length)

    window = 24
    X = np.array([history[i:i+window] for i in range(len(history)-window)])
    y = history[window:]

    model = Ridge(alpha=5).fit(X, y)
    seq = history[-window:].tolist()
    pred = []

    for _ in range(length):
        next_val = model.predict([seq])[0]
        pred.append(next_val)
        seq = seq[1:] + [next_val]

    return np.array(pred)


def denoise_ppg(ppg_signal, fs, reference_signal):
    """Denoises PPG using LMS filtering without DTW"""
    ppg_signal = np.array(ppg_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()

    # Normalize each to zero mean
    ppg_signal -= np.mean(ppg_signal)
    reference_signal -= np.mean(reference_signal)

    # Scale both to have the same std (e.g., the average std)
    mad = np.median(np.abs(ppg_signal - np.median(ppg_signal)))
    robust_std = mad * 1.4826
    ppg_signal = (ppg_signal / robust_std) * np.std(reference_signal)

    # Step 1: Band-pass filter to remove unwanted noise
    filtered_signal = butter_bandpass_filter(ppg_signal, fs)

    # Step 2: Apply LMS filtering directly (no DTW).
    clean_signal, not_reading = pattern_filter(fs, filtered_signal, reference_signal)
    if not not_reading:
        if globals.history is None:
            globals.history = clean_signal
        else:
            globals.history = np.concatenate((globals.history, clean_signal[fs*(-5):]))

    return clean_signal.flatten(), filtered_signal.flatten(), not_reading
