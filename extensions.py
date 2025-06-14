from flask_login import LoginManager
from google.cloud import firestore
import os
from dotenv import load_dotenv
from pymongo import MongoClient # Added missing import

load_dotenv()

# Initialize Firestore client
db = firestore.Client(project=os.getenv('GOOGLE_CLOUD_PROJECT'))

# Initialize Flask-Login
login_manager = LoginManager()

# Initialize MongoDB client
mongo_uri = os.getenv("MONGODB_ATLAS_URI")
if not mongo_uri:
    print("❌ MONGODB_ATLAS_URI not found in environment variables. MongoDB connection will likely fail or default to localhost.")
    mongo_client = None
    mongo_db = None
    mongo_col = None
else:
    print(f"ℹ️ Attempting to connect to MongoDB with URI: {mongo_uri[:20]}...{mongo_uri[-20:] if len(mongo_uri) > 40 else ''}") # Print a truncated URI for security
    try:
        mongo_client = MongoClient(mongo_uri)
        # Attempt a simple operation to confirm connection earlier
        mongo_client.admin.command('ping') 
        mongo_db = mongo_client["whatscooking"] # Or your specific database name
        mongo_col = mongo_db["restaurants"] # Or your specific collection name
        print("✅ Successfully connected to MongoDB and got collection")
    except Exception as e:
        print(f"❌ Error connecting to MongoDB or pinging the server: {e}")
        mongo_client = None
        mongo_db = None
        mongo_col = None