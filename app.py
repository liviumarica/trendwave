import os
import logging
from datetime import datetime

from flask import Flask, jsonify, redirect, url_for, current_app
from flask_cors import CORS
from flask_login import LoginManager, current_user
from dotenv import load_dotenv

# ▶︎ NEW Google GenAI SDK import (correct)
import google.genai as genai

# ---------------------------------------------------------------------------- #
#  Environment & constants
# ---------------------------------------------------------------------------- #
load_dotenv()

GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
PROJECT_ID    = os.getenv("GCP_PROJECT_ID")  # optional for Vertex‑hosted quotas
TEXT_MODEL    = "gemini-2.0-flash"           # fast text generation
EMBED_MODEL   = "gemini-embedding-001"       # 768‑dim embedding model
#EMBED_MODEL   = "textembedding-gecko@001"       # 768‑dim embedding model

if not GENAI_API_KEY:
    raise RuntimeError("⚠️  GEMINI_API_KEY environment variable is missing!")

# Configure the client once
client = genai.Client(
    vertexai=True, project=PROJECT_ID, location='us-central1'
)

# ---------------------------------------------------------------------------- #
#  Flask factory
# ---------------------------------------------------------------------------- #
login_manager = LoginManager()

from extensions import mongo_col
from models.user import User
from routes.auth import auth_bp
from routes.chat import chat_bp


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    # Security/session config
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me"),
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        TEXT_MODEL=TEXT_MODEL,
        EMBED_MODEL=EMBED_MODEL,
    )

    # Logging & CORS
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s — %(message)s")
    CORS(app, supports_credentials=True)

    # Flask‑Login setup
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(uid):
        return User.get(uid)

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/")

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("chat.chat"))
        return redirect(url_for("auth.login"))

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok", "ts": datetime.utcnow().isoformat()})

    app.logger.info("Mongo collection attached: %s", mongo_col is not None)
    app.logger.info("Gemini text model: %s | embed model: %s", TEXT_MODEL, EMBED_MODEL)

    return app


if __name__ == "__main__":
    flask_app = create_app()
    port = int(os.getenv("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
