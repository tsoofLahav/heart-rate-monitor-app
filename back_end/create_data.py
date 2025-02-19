import numpy as np

last_interval = -1
ave_gap = 1  # Default average gap


def process_peaks(peaks, fps, total_duration):
    """ Process detected peaks to calculate time gaps, bpm, and generate estimated intervals. """
    global last_interval, ave_gap

    print("\n--- Processing Peaks ---")
    print(f"Peaks: {peaks}")
    print(f"FPS: {fps}, Total Duration: {total_duration}")
    print(f"Previous Last Interval: {last_interval}, Previous Ave Gap: {ave_gap}")

    # Convert peaks to time gaps
    if len(peaks) == 0:
        time_gaps = np.array([total_duration])
    else:
        time_gaps = np.diff(np.insert(peaks, 0, 0)) / fps  # Gaps between peaks
        time_gaps = np.append(time_gaps, (total_duration - peaks[-1]) / fps)  # Last gap

    print(f"Initial Time Gaps: {time_gaps}")

    # Adjust for the gap at the video boundary
    if last_interval != -1:
        if last_interval + time_gaps[0] > 1.5 * ave_gap:
            print("Detected possible missing beat at boundary!")
            time_gaps = np.insert(time_gaps, 0, last_interval)  # Assume a missed beat
        else:
            time_gaps[0] += last_interval  # Merge previous interval

    print(f"Adjusted Time Gaps: {time_gaps}")

    # Store last gap for next interval
    last_interval = time_gaps[-1]
    print(f"Updated Last Interval: {last_interval}")

    # Compute average gap (ignore first and last, since they can be artifacts)
    valid_gaps = time_gaps[1:-1] if last_interval == -1 else time_gaps[:-1]
    if len(valid_gaps) > 0:
        ave_gap = np.mean(valid_gaps)
    bpm = 60 / ave_gap if ave_gap > 0 else 0

    print(f"Computed Average Gap: {ave_gap}, BPM: {bpm}")

    # Generate new beat prediction list
    new_start = False
    new_list = []
    first_interval = ave_gap - last_interval
    if first_interval <= 0:
        new_start = True
        print("Immediate beat needed (new_start=True)")
    else:
        new_list.append(first_interval)
        total_duration -= first_interval

    while total_duration >= ave_gap:
        new_list.append(ave_gap)
        total_duration -= ave_gap

    if total_duration > 0:
        new_list.append(total_duration)

    print(f"Generated Beat List: {new_list}, New Start: {new_start}\n")

    return new_start, new_list, bpm
