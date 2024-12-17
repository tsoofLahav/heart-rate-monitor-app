from flask import Flask
from routes.video_route import setup_video_route

# from routes.status_route import setup_status_routes

app = Flask(__name__)

setup_video_route(app)
# setup_status_routes(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
