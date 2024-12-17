from flask import Flask
from video_route import setup_video_route

# from routes.status_route import setup_status_routes

app = Flask(__name__)

setup_video_route(app)


# Health check route
@app.route('/', methods=['GET'])
def index():
    return "App is running!", 200


@app.route('/health', methods=['GET'])
def health():
    return "OK", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
