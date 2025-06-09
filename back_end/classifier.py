import torch
import torch.nn as nn
import os
import globals

# ---------- Define the model class ----------
class SimpleMLP(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.model(x)

# ---------- Load model (call once when session starts) ----------
def load_mlp_model():
    model_path = os.path.join(os.path.dirname(__file__), 'model2_classifier.pt')
    globals.mlp_model = SimpleMLP(globals.input_size)
    globals.mlp_model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    globals.mlp_model.eval()
    print("✅ MLP model loaded successfully")

# ---------- Use model to classify one segment ----------
def classify_signal_segment(segment):
    global mlp_model
    if globals.mlp_model is None:
        raise ValueError("Model not loaded. Call load_mlp_model() first.")

    with torch.no_grad():
        x = torch.tensor(segment, dtype=torch.float32).unsqueeze(0)  # shape: (1, input_size)
        y_pred = globals.mlp_model(x).item()
        return 1 if y_pred >= 0.5 else 0
