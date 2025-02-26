import numpy as np
from scipy.signal import find_peaks


def rls_filter(intensities, fps, delta=10.0, lambda_=0.995):
    """
    Apply an RLS (Recursive Least Squares) filter to the PPG signal and detect peaks.

    Parameters:
    - intensities: List or array of PPG signal intensities.
    - fps: Frames per second of the video (sampling frequency).
    - delta: Initial P matrix value (higher values adapt faster, default 1.0).
    - lambda_: Forgetting factor (close to 1 for slow adaptation, default 0.99).

    Returns:
    - filtered_signal: The filtered PPG signal.
    - peaks: Indices of detected peaks.
    """

    # Convert intensities to numpy array
    intensities = np.array(intensities)

    # Initialize RLS filter parameters
    n = len(intensities)
    w = np.zeros((1,))  # Ensure w is 1D
    P = np.eye(1) * delta  # Inverse covariance matrix
    filtered_signal = np.zeros(n)

    for i in range(n):
        x = np.array([intensities[i]]).reshape(1, 1)  # Ensure x is a column vector
        K = (P @ x) / (lambda_ + x.T @ P @ x)  # Gain
        e = intensities[i] - (w.T @ x).item()  # Error signal
        w = w + K.flatten() * e  # Update weight
        P = (P - K @ x.T @ P) / lambda_  # Update covariance
        filtered_signal[i] = (w.T @ x).item()  # Store filtered value

    # Detect peaks using HeartPy
    peaks, _ = find_peaks(filtered_signal, distance=fps * 0.5, prominence=0.1)

    return filtered_signal.tolist(), peaks.tolist()
