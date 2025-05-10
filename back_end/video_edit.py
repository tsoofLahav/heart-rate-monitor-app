import cv2
import numpy as np


def process_video_frames(input_path, target_fps=24, target_duration=5):
    """Reads a video, adjusts FPS to exactly 24, extracts intensities, and returns FPS & intensities."""
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise Exception("Failed to open video file.")

    target_frames = target_fps * target_duration  # 120 frames for 5 seconds
    frames = []
    frame_width, frame_height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Define circular ROI mask
    center_x, center_y = frame_width // 2, frame_height // 2
    radius = min(center_x, center_y) // 2
    Y, X = np.ogrid[:frame_height, :frame_width]
    mask = (np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2) <= radius)

    # Read all frames
    intensities = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)

    cap.release()
    if not frames:
        raise Exception("No frames found in video.")

    # Resample frames to exactly 120 using interpolation
    frame_indices = np.linspace(0, len(frames) - 1, target_frames).astype(int)
    resampled_frames = [frames[i] for i in frame_indices]

    # Extract intensities
    for frame in resampled_frames:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi_values = gray_frame[mask]
        intensities.append(-np.mean(roi_values))  # Invert intensity

    return target_fps, intensities



