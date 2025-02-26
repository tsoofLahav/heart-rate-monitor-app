import numpy as np
from scipy.signal import find_peaks

# Global variables to persist state across cycles
w_prev = None
P_prev = None


def rls_filter(intensities, fps, delta=10.0, lambda_=0.9967):
    """
    Apply an RLS (Recursive Least Squares) filter to the PPG signal and detect peaks.
    It remembers past state across cycles.

    Parameters:
    - intensities: List or array of PPG signal intensities.
    - fps: Frames per second of the video (sampling frequency).
    - delta: Initial P matrix value (higher values adapt faster).
    - lambda_: Forgetting factor (set to forget after ~5 sec at given FPS).

    Returns:
    - filtered_signal: The filtered PPG signal.
    - peaks: Indices of detected peaks.
    - w: Updated filter weights (to remember across cycles).
    - P: Updated covariance matrix (to remember across cycles).
    """

    global w_prev, P_prev  # Use previous values across cycles

    # Convert intensities to numpy array
    intensities = np.array(intensities)

    # Initialize RLS filter parameters
    n = len(intensities)

    if w_prev is None or P_prev is None:  # First cycle, initialize
        w = np.zeros((1,))  # Ensure w is 1D
        P = np.eye(1) * delta  # Inverse covariance matrix
    else:  # Use previous values
        w = w_prev
        P = P_prev

    filtered_signal = np.zeros(n)

    for i in range(n):
        x = np.array([intensities[i]]).reshape(1, 1)  # Ensure x is a column vector
        K = (P @ x) / (lambda_ + x.T @ P @ x)  # Gain
        e = intensities[i] - (w.T @ x).item()  # Error signal
        w = w + K.flatten() * e  # Update weight
        P = (P - K @ x.T @ P) / lambda_  # Update covariance
        filtered_signal[i] = (w.T @ x).item()  # Store filtered value

    # Store updated values for the next cycle
    w_prev, P_prev = w, P

    # Detect peaks using SciPy's find_peaks
    peaks, _ = find_peaks(filtered_signal, distance=fps * 0.25, prominence=0.1)

    return filtered_signal.tolist(), peaks.tolist()

