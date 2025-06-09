# video_route
raw_buffer = []
peak_history = []
round_count = 0
prediction_buffer = []
testing_mode = True

# data_route
session_id = None

# models
mlp_model = None
input_size = 48
reconstruction_model = None
predictor_model = None


def reset_all():
    global raw_buffer, peak_history, round_count, prediction_buffer
    raw_buffer = []
    peak_history = []
    round_count = 0
    prediction_buffer = []
