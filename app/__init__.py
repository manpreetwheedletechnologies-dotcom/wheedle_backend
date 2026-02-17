from flask import Flask
from flask_cors import CORS
from .routes.chat_routes import chat_bp

def create_app():
    app = Flask(__name__)

    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        allow_headers=["Content-Type", "x-api-key"],
        methods=["GET", "POST", "OPTIONS"],
    )

    app.register_blueprint(chat_bp)

    return app
