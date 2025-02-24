from flask import Flask, jsonify
import os
import video_route  # Ensure this module contains the process_video route

app = Flask(__name__)


# Import the module to register the route
# No need to call process_video(app)

# Health check route
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
