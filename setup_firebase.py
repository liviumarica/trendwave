import os
import json
from dotenv import load_dotenv

def setup_firebase():
    """
    Helper script to set up Firebase credentials.
    This will create a firebase-credentials.json file in the project root.
    """
    print("Firebase Setup Helper")
    print("=" * 20)
    
    # Check if credentials already exist
    if os.path.exists('firebase-credentials.json'):
        print("\nA firebase-credentials.json file already exists.")
        overwrite = input("Do you want to overwrite it? (y/n): ").lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    print("\nPlease enter your Firebase service account credentials:")
    print("You can get these from the Firebase Console > Project Settings > Service Accounts")
    
    try:
        project_id = input("Project ID: ")
        private_key_id = input("Private Key ID: ")
        private_key = input("Private Key (starts with '-----BEGIN PRIVATE KEY-----'): ")
        client_email = input("Client Email: ")
        client_id = input("Client ID: ")
        client_x509_cert_url = input("Client x509 Cert URL: ")
        
        # Create the credentials dictionary
        credentials = {
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": private_key_id,
            "private_key": private_key.replace('\\n', '\n'),
            "client_email": client_email,
            "client_id": client_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": client_x509_cert_url,
            "universe_domain": "googleapis.com"
        }
        
        # Save to file
        with open('firebase-credentials.json', 'w') as f:
            json.dump(credentials, f, indent=2)
        
        # Update .env file
        load_dotenv()
        with open('.env', 'a') as f:
            f.write(f'\nFIREBASE_PROJECT_ID={project_id}\n')
        
        print("\n✅ Firebase credentials have been set up successfully!")
        print("You can now run the application with: python main.py")
        
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("Please make sure you entered all the information correctly.")

if __name__ == "__main__":
    setup_firebase()
