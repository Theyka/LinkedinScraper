import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from models.db import init_db
from controllers.auth import auth_bp
from controllers.profile import profile_bp


def make_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY") or "MJ8hk6XR8yYtkib0Cf7YJ27BkgzeOBm"
    CORS(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    with app.app_context():
        init_db()
    return app


app = make_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
