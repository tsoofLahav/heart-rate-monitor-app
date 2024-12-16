round_num = 0
peaks_list = []
time_gap = 0


def calculate_bpm(peaks, gap):
    total_time = peaks[-1] - peaks[0] + gap
    if total_time > 0:
        bpm = len(peaks) * 60 / total_time
    else:
        bpm = -1
    return bpm


def calculate_hrv(peaks, gap):
    gaps = [peaks[i] - peaks[i - 1] for i in range(1, len(peaks))]
    gaps.append(gap)
    hrv = sum(gaps) / len(gaps) if gaps else -1
    return hrv


def bpm_and_hrv_calculator(peaks):
    global round_num, peaks_list, time_gap

    adjusted_peaks = [peak + round_num for peak in peaks]
    peaks_list += adjusted_peaks
    round_num += 1

    if round_num == 5:
        time_gap = 5 - peaks_list[-1]
        bpm = calculate_bpm(peaks_list, time_gap)
        hrv = calculate_hrv(peaks_list, time_gap)

        # Reset for the next cycle
        round_num = 0
        time_gap = 5 - peaks_list[-1]
        peaks_list = []

    else:
        bpm = -1
        hrv = -1

    return bpm, hrv
