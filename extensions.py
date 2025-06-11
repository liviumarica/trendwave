from flask_login import LoginManager
from google.cloud import firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firestore client
db = firestore.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))

# Initialize Flask-Login
login_manager = LoginManager()
