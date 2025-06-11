import os
from google.cloud import firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_firestore_connection():
    try:
        # Get project ID from environment variables
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")
        
        print(f"Connecting to Firestore in project: {project_id}")
        
        # Initialize Firestore client with default database
        db = firestore.Client(project=project_id)
        
        # Test connection by trying to list collections
        collections = db.collections()
        print("Successfully connected to Firestore!")
        print(f"Available collections: {[col.id for col in collections]}")
        
        return True
        
    except Exception as e:
        print(f"Error connecting to Firestore: {str(e)}")
        return False

if __name__ == "__main__":
    test_firestore_connection()
