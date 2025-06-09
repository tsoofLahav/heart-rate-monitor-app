import torch
import torch.nn as nn
import globals

# ---------- Constants ----------
SAMPLE_RATE = 24
FULL_LENGTH = 10 * SAMPLE_RATE  # 240
MISSING_LENGTH = 2 * SAMPLE_RATE  # 48

# ---------- MLP Reconstruction Model ----------
class MLP(nn.Module):
    def __init__(self, input_size=FULL_LENGTH, output_size=MISSING_LENGTH):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(input_size, 512), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(512, 256), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(256, 128), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(128, output_size)
        )

    def forward(self, x):
        return self.model(x)

# ---------- Load Model Once (e.g., in start_session) ----------
def load_reconstruction_model():
    model = MLP()
    model.load_state_dict(torch.load("model_reconstruction.pt", map_location="cpu"))
    model.eval()
    globals.reconstruction_model = model
    print("✅ Reconstruction model loaded.")

# ---------- Use Model in Inference ----------
def reconstruct_missing(signal_segment):
    """
    Args:
        signal_segment (list or np.array): Full 10s signal (zeroed 2s region).

    Returns:
        reconstructed_signal (np.array): Reconstructed 2s segment.
    """
    model = globals.reconstruction_model
    if model is None:
        raise RuntimeError("Model not loaded. Call load_reconstruction_model() first.")

    input_tensor = torch.tensor(signal_segment, dtype=torch.float32).unsqueeze(0)  # shape: [1, 240]
    with torch.no_grad():
        output = model(input_tensor).squeeze(0).numpy()
    return output
