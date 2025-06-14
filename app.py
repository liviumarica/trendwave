"""
Main application entry point for the TrendWave Flask application.
Initializes the Flask app, loads configurations, registers blueprints,
and sets up extensions.
"""
import os
import logging
from flask import Flask, redirect, url_for, jsonify, request
from flask_login import LoginManager, current_user
from flask_cors import CORS
import vertexai
from vertexai.language_models import TextGenerationModel, TextEmbeddingModel
from dotenv import load_dotenv

# Initialize LoginManager at module level
login_manager = LoginManager()

# Load environment variables
load_dotenv()

# Import extensions and blueprints after environment variables are loaded
from extensions import db, mongo_col
from models.user import User
from routes.auth import auth_bp
from routes.chat import chat_bp

def create_app():
    """
    Create and configure the Flask application.
    """
    app = Flask(__name__)
    
    # Load configuration from environment variables
    app.config.from_prefixed_env()
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')
        ]
    )
    
    # Enable CORS if needed
    CORS(app, supports_credentials=True)
    
    # Initialize models as None - they'll be initialized on first request
    app.embed_model = None
    app.gemini_model = None
    
    def initialize_models():
        """Initialize Vertex AI models if not already initialized"""
        if app.embed_model is None or app.gemini_model is None:
            try:
                project_id = os.getenv("GCP_PROJECT_ID")
                if not project_id:
                    raise ValueError("GCP_PROJECT_ID environment variable is not set")
                    
                logging.info(f"Initializing Vertex AI with project: {project_id}")
                vertexai.init(
                    project=project_id,
                    location="europe-west1"  # Supported region for Vertex AI
                )
                
                # Initialize models
                logging.info("Loading text embedding model...")
                app.embed_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
                
                logging.info("Loading text generation model...")
                # Using text-bison-32k model for text generation
                app.gemini_model = TextGenerationModel.from_pretrained("gemini-2.0-flash-lite-001")
                
                # Test the model with a simple prompt to verify it works
                try:
                    test_response = app.gemini_model.predict("Test connection")
                    logging.info("Successfully connected to text generation model")
                except Exception as e:
                    logging.error(f"Failed to connect to text generation model: {str(e)}")
                    raise
                
                logging.info("Vertex AI models initialized successfully")
                
            except Exception as e:
                logging.error(f"Failed to initialize Vertex AI: {str(e)}", exc_info=True)
                app.embed_model = None
                app.gemini_model = None
                raise
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Set the login view
    
    # User loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    # Register chat blueprint without prefix to avoid conflicts
    app.register_blueprint(chat_bp)
    
    # Main route - redirect based on authentication status
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('chat.chat'))
        return redirect(url_for('auth.login'))
    
    # Initialize models at app startup
    with app.app_context():
        try:
            initialize_models()
        except Exception as e:
            logging.error(f"Failed to initialize models at startup: {str(e)}")
    
    # Add a before_request handler to ensure models are initialized
    @app.before_request
    def before_request():
        try:
            initialize_models()
        except Exception as e:
            logging.error(f"Failed to initialize models: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to initialize AI models',
                'details': str(e)
            }), 500
            
    return app
    
    return app

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
    
    # Create and run the app
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    
    # Log startup information
    logging.info(f"Starting TrendWave application on port {port}")
    logging.info(f"MongoDB collection: {'Available' if mongo_col is not None else 'Not available'}")
    
    app.run(host='0.0.0.0', port=port, debug=True)
