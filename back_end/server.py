from flask import Flask, jsonify
from video_route import setup_video_route
import os

app = Flask(__name__)

setup_video_route(app)


# Health check route
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port or default to 5000
    app.run(host="0.0.0.0", port=port)