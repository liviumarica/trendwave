import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

def verify_firebase():
    print("Verifying Firebase Setup...")
    print("=" * 30)
    
    # Load environment variables
    load_dotenv()
    
    # Check required environment variables
    required_vars = [
        'GOOGLE_APPLICATION_CREDENTIALS',
        'FIREBASE_PROJECT_ID',
        'SECRET_KEY'
    ]
    
    print("\nChecking environment variables:")
    env_ok = True
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            print(f"❌ {var} is not set")
            env_ok = False
        else:
            print(f"✅ {var} is set")
    
    if not env_ok:
        print("\nPlease set all required environment variables in the .env file.")
        return
    
    # Check credentials file
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    print(f"\nChecking credentials file at: {creds_path}")
    
    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found at {creds_path}")
        return
    
    try:
        # Try to initialize Firebase
        print("\nInitializing Firebase...")
        cred = credentials.Certificate(creds_path)
        firebase_admin.initialize_app(cred, {
            'projectId': os.getenv('FIREBASE_PROJECT_ID')
        })
        
        # Test Firestore connection
        print("Testing Firestore connection...")
        db = firestore.client()
        
        # Try a simple operation
        test_doc = db.collection('test_collection').document('test_doc')
        test_doc.set({'test': 'success', 'timestamp': firestore.SERVER_TIMESTAMP})
        print("✅ Successfully wrote to Firestore")
        
        # Clean up
        test_doc.delete()
        print("✅ Cleaned up test document")
        
        print("\n🔥 Firebase setup is working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error initializing Firebase: {str(e)}")
        print("\nPlease check the following:")
        print("1. Your service account key file is valid")
        print("2. The service account has proper permissions in Firebase")
        print("3. Your internet connection is working")
        print("4. The project ID matches your Firebase project")

if __name__ == "__main__":
    verify_firebase()
