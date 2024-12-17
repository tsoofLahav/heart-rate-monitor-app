from flask import Flask
from routes.video_route import setup_video_route
import os

# from routes.status_route import setup_status_routes

app = Flask(__name__)

setup_video_route(app)
# setup_status_routes(app)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
