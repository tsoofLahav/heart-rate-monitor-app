import torch
import torch.nn as nn
import globals

class SimpleMLP(nn.Module):
    def __init__(self, input_size=19, output_size=30):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, output_size)
        )

    def forward(self, x):
        return self.model(x)


def load_predictor_model(path="model_predictor.pt"):
    model = SimpleMLP()
    model.load_state_dict(torch.load(path, map_location='cpu'))
    model.eval()
    globals.predictor_model = model


def predict_future_sequence(input_intervals):
    model = globals.predictor_model

    # Pad input to 19 if needed
    if len(input_intervals) < 19:
        first_val = input_intervals[0] if input_intervals else 1.0  # fallback if empty
        pad_count = 19 - len(input_intervals)
        input_intervals = [first_val] * pad_count + input_intervals

    input_tensor = torch.tensor(input_intervals[:19], dtype=torch.float32).unsqueeze(0)

    with torch.no_grad():
        output = model(input_tensor)

    return output.squeeze(0).tolist()

