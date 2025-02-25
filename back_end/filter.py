import numpy as np
import heartpy as hp

def rls_filter(intensities, fps, delta=1.0, lambda_=0.99):
    """
    Apply an RLS (Recursive Least Squares) filter to the PPG signal.

    Parameters:
    - intensities: List or array of PPG signal intensities.
    - fps: Frames per second of the video (sampling frequency).
    - delta: Initial P matrix value (higher values adapt faster, default 1.0).
    - lambda_: Forgetting factor (close to 1 for slow adaptation, default 0.99).

    Returns:
    - filtered_signal: The filtered PPG signal.
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

    return filtered_signal.tolist()
