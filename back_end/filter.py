from scipy.signal import butter, sosfiltfilt
from scipy.interpolate import interp1d
import numpy as np
import globals
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.ar_model import AutoReg
from sklearn.linear_model import LinearRegression


def butter_bandpass_filter(signal, fs, lowcut=0.8, highcut=3.0, order=6):
    """Applies a band-pass filter using second-order sections (SOS) for stability."""
    nyq = 0.5 * fs
    low, high = lowcut / nyq, highcut / nyq
    sos = butter(order, [low, high], btype='band', output='sos')
    return sosfiltfilt(sos, signal)


def match_reference_segment(noisy_signal, reference_signal, stretch_range=(0.6, 1.2), steps=20):
    """
    Finds the best-matching segment in a longer reference for a given noisy signal,
    allowing stretching/squeezing.
    Returns the aligned segment from the reference (same length as noisy_signal).
    """
    noisy_signal = np.array(noisy_signal).flatten()
    reference_signal = np.array(reference_signal).flatten()

    best_corr = -np.inf
    best_segment = None

    for factor in np.linspace(*stretch_range, steps):
        # Stretch the reference
        stretched_len = int(len(reference_signal) * factor)
        x_old = np.linspace(0, 1, len(reference_signal))
        x_new = np.linspace(0, 1, stretched_len)
        stretched_ref = interp1d(x_old, reference_signal, kind='cubic', fill_value="extrapolate")(x_new)

        # Slide over the stretched reference to find best matching window
        for start in range(0, len(stretched_ref) - len(noisy_signal) + 1):
            segment = stretched_ref[start:start + len(noisy_signal)]

            # Normalize both before correlation
            segment_norm = (segment - np.mean(segment)) / (np.std(segment) + 1e-8)
            noisy_norm = (noisy_signal - np.mean(noisy_signal)) / (np.std(noisy_signal) + 1e-8)
            corr = np.dot(segment_norm, noisy_norm)

            if corr > best_corr:
                best_corr = corr
                best_segment = segment

    return best_segment


def pattern_filter(noisy_signal, reference_signal,
                   fps=24, trust_threshold=0.5, match_threshold=0.8):
    batch_size = fps
    n = len(noisy_signal)
    output = np.empty((0,), dtype=np.float32)
    artifact_streak = 0
    not_reading = False

    reference_std = np.std(reference_signal) + 1e-8

    for i in range(0, n, batch_size):
        if i + batch_size > n:
            break

        signal_chunk = noisy_signal[i:i + batch_size]
        std_ratio = np.std(signal_chunk) / reference_std
        trust_factor = np.exp(-abs(np.log(std_ratio)))
        print("Trust factor: ", trust_factor)
        is_artifact = trust_factor < trust_threshold

        if not is_artifact:
            aligned_reference = match_reference_segment(signal_chunk, reference_signal)
            similarity = np.dot(signal_chunk, aligned_reference) / (
                np.linalg.norm(signal_chunk) * np.linalg.norm(aligned_reference) + 1e-8)
            print("Similarity: ", similarity)
            if similarity >= match_threshold:
                output = np.concatenate((output, signal_chunk))
                artifact_streak = 0
                continue
            else:
                is_artifact = True

        artifact_streak += 1
        if artifact_streak >= 3:
            not_reading = True

        if is_artifact:
            history_input = np.concatenate((globals.history, output))[-100:]  # Use last 100 points for context
            predicted_chunk = lstm_predict_next_segment(history_input, batch_size)
            output = np.concatenate((output, predicted_chunk))

    return output, not_reading


def lstm_predict_next_segment(history, length):
    """
    Predicts the next `length` signal points using ARIMA.
    This replaces the previous LinearRegression approximation of LSTM.
    """
    history = np.array(history[-100:], dtype=np.float32)
    if len(history) < 25:
        return np.zeros(length)

    try:
        model = ARIMA(history, order=(6, 1, 4))  # (p,d,q) can be tuned
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
    clean_signal, not_reading = pattern_filter(filtered_signal, reference_signal, fps=fs)
    globals.last_chunk = clean_signal[-fs:]
    #
    # if len(globals.history) < 300:
    #     globals.history = np.concatenate((globals.history, clean_signal[:fs * 5]))
    # else:
    #     globals.history = np.concatenate((globals.history[-180:], clean_signal[:fs * 5]))

    return clean_signal.flatten(), filtered_signal.flatten(), not_reading
