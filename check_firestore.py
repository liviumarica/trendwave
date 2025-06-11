import os
from google.cloud import firestore
from dotenv import load_dotenv

def test_firestore_write():
    try:
        # Load environment variables
        load_dotenv()
        
        # Get project ID from environment variables
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")
        
        print(f"Connecting to Firestore in project: {project_id}")
        
        # Initialize Firestore client with default database
        db = firestore.Client(project=project_id)
        
        # Try to create a test document
        test_ref = db.collection('test_collection').document('test_doc')
        test_ref.set({
            'test_field': 'Hello Firestore!',
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        print("Successfully wrote test document to Firestore!")
        
        # Clean up
        test_ref.delete()
        print("Cleaned up test document")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_firestore_write()
