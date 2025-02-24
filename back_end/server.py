from flask import Flask, jsonify
from video_route import process_video
import os

app = Flask(__name__)

process_video(app)


# Health check route
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

