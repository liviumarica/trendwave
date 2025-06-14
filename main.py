"""
Main application entry point for TrendWave.
This module initializes and runs the Flask application.
"""
from flask import Flask, jsonify, redirect, url_for
from flask_login import LoginManager, current_user
from flask_cors import CORS
from extensions import login_manager, db, mongo_col
from models.user import User
from routes.auth import auth_bp
from routes.chat import chat_bp
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure app
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-please-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize extensions
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Enable CORS
CORS(app, supports_credentials=True)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(chat_bp, url_prefix='/')

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Main route - redirect based on authentication status
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat.chat'))
    return redirect(url_for('auth.login'))

# Import routes after app is created to avoid circular imports
from routes import chat, auth

# Initialize Vertex AI (moved from chat.py to avoid multiple initializations)
import vertexai
from vertexai.language_models import TextEmbeddingModel, TextGenerationModel

vertexai.init(
    project=os.getenv("GCP_PROJECT_ID"),
    location="europe-west1"
)

# Initialize models
embed_model = TextEmbeddingModel.from_pretrained("gemini-2.0-flash-lite-001")
gemini_model = TextGenerationModel.from_pretrained("gemini-2.0-flash-lite-001")
if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')
        ]
    )
    
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    
    # Log startup information
    logging.info(f"Starting TrendWave application on port {port}")
    logging.info(f"MongoDB collection: {'Available' if mongo_col is not None else 'Not available'}")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=True)
