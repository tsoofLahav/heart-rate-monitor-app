from flask import Flask, request, jsonify
import numpy as np
from tensorflow.keras.models import load_model

model = load_model('path_to_model_directory/model.h5')

def denoise_ppg(signal):
    signal = np.array(signal)  # Expecting a list input
    denoised_signal = model.predict(signal)
    return