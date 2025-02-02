from flask import Flask, jsonify
from video_route import setup_video_route

app = Flask(__name__)

setup_video_route(app)


# Health check route
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "OK"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
