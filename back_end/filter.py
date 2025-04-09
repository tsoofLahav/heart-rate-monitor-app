from scipy.signal import butter, sosfiltfilt
from scipy.interpolate import interp1d
import numpy as np
import globals
from statsmodels.tsa.arima.model import ARIMA
from scipy.signal import find_peaks


def split_by_minima(signal, fs):
    std = np.std(signal)
    distance = int(0.35 * fs)
    peaks, _ = find_peaks(-signal, height=0.5 * std, distance=distance)
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


def pattern_filter(fps, noisy_signal, reference_signal, match_threshold=0.8):
    segments = split_by_minima(noisy_signal, fps)
    output = []
    buffer = []

    for chunk in segments:
        if len(chunk) < 4:
            continue

        aligned = extrapolate_to_length(chunk, len(reference_signal))
        similarity = np.dot(reference_signal, aligned) / (
            np.linalg.norm(reference_signal) * np.linalg.norm(aligned) + 1e-8)

        if similarity >= match_threshold:
            if buffer:
                length = sum(len(b) for b in buffer)
                context = np.concatenate((globals.history, *output))[-120:]
                output.append(arima_predict_next_segment(context, length))
                buffer.clear()
            output.append(chunk)
        else:
            buffer.append(chunk)

    if buffer:
        length = sum(len(b) for b in buffer)
        context = np.concatenate((globals.history, *output))[-120:]
        output.append(arima_predict_next_segment(context, length))

    return np.concatenate(output)


def arima_predict_next_segment(history, length):
    """
    Predicts the next `length` signal points using ARIMA.
    This replaces the previous LinearRegression approximation of LSTM.
    """
    history = np.array(history[-120:], dtype=np.float32)
    if len(history) < 25:
        return np.zeros(length)

    try:
        model = ARIMA(history, order=(8, 1, 6))  # (p,d,q) can be tuned
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=length)
        return np.array(forecast)
    except Exception as e:
        print("ARIMA prediction failed:", e)
        return np.zeros(length)


def denoise_ppg(ppg_signal, fs, reference_signal):
    """Denoises PPG using LMS filtering without DTW"""
    ppg_signal = np.array(ppg_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()

    # Normalize each to zero mean
    ppg_signal -= np.mean(ppg_signal)
    reference_signal -= np.mean(reference_signal)

    # Scale both to have the same std (e.g., the average std).
    mad = np.median(np.abs(ppg_signal - np.median(ppg_signal)))
    robust_std = mad * 1.4826
    ppg_signal = (ppg_signal / robust_std) * np.std(reference_signal)

    # Step 1: Band-pass filter to remove unwanted noise
    filtered_signal = butter_bandpass_filter(ppg_signal, fs)

    # Step 2: Apply LMS filtering directly (no DTW).
    clean_signal = pattern_filter(fs, filtered_signal, reference_signal)
    globals.last_chunk = clean_signal[-fs:]

    return clean_signal.flatten(), filtered_signal.flatten(), False
