import numpy as np


class BPMAndHRVCalculator:
    def __init__(self):
        self.interval_list = []  # Stores the intervals for computation
        self.round_counter = 0  # Tracks the number of input rounds

    def reset(self):
        self.interval_list = []
        self.round_counter = 0

    def calculate(self, intervals_list, new_start, not_reading):
        if not_reading:
            self.reset()
            return -1, -1, -1

        if not new_start:
            # Combine the last interval of the current list with the first of the new input
            self.interval_list[-1] += intervals_list[0]
            self.interval_list.extend(intervals_list[1:])
        else:
            # Add the new intervals as-is
            self.interval_list.extend(intervals_list)

        self.round_counter += 1

        # Every 5 rounds, calculate BPM, HRV, and average gap
        if self.round_counter == 5:
            # Compute average gap
            ave_gap = sum(self.interval_list) / len(self.interval_list) if self.interval_list else 0

            # Compute BPM
            bpm = 60 / ave_gap if ave_gap > 0 else 0

            # Compute HRV (Standard deviation of intervals)
            hrv = np.std(self.interval_list) if self.interval_list else 0

            # Start a new list for the next rounds
            self.interval_list = [intervals_list[-1]]
            self.round_counter = 0

            return bpm, hrv, ave_gap

        # If not a computation round, return -1 to indicate no new values
        return -1, -1, -1
