import os
import json

def create_firebase_credentials():
    print("Firebase Service Account Key Creator")
    print("=" * 40)
    
    print("\nPlease follow these steps to get your Firebase service account key:")
    print("1. Go to Firebase Console: https://console.firebase.google.com/")
    print("2. Select your project")
    print("3. Click on the gear icon ⚙️ next to 'Project Overview'")
    print("4. Select 'Project settings'")
    print("5. Go to the 'Service accounts' tab")
    print("6. Click 'Generate new private key'")
    print("7. Save the JSON file when prompted")
    
    print("\nOnce you have the JSON file, please enter the following information:")
    
    try:
        # Get the path to save the credentials
        save_path = os.path.join(os.getcwd(), 'firebase-credentials.json')
        
        # Get service account details
        print("\nPaste the content of your service account JSON file below (press Enter, then Ctrl+Z, then Enter when done):")
        content = []
        print("Paste your JSON content:")
        while True:
            try:
                line = input()
            except EOFError:
                break
            content.append(line)
        
        # Parse the JSON content
        json_content = '\n'.join(content)
        service_account = json.loads(json_content)
        
        # Verify required fields
        required_fields = [
            'type', 'project_id', 'private_key_id',
            'private_key', 'client_email', 'client_id',
            'auth_uri', 'token_uri', 'auth_provider_x509_cert_url',
            'client_x509_cert_url'
        ]
        
        for field in required_fields:
            if field not in service_account:
                print(f"❌ Missing required field: {field}")
                return
        
        # Save the service account file
        with open(save_path, 'w') as f:
            json.dump(service_account, f, indent=2)
        
        # Update .env file
        with open('.env', 'a') as f:
            f.write(f'\nGOOGLE_APPLICATION_CREDENTIALS={save_path}\n')
            f.write(f'FIREBASE_PROJECT_ID={service_account["project_id"]}\n')
        
        print(f"\n✅ Service account key saved to: {save_path}")
        print("✅ .env file has been updated with the correct paths")
        print("\nYou can now run the application with: python main.py")
        
    except json.JSONDecodeError:
        print("\n❌ Invalid JSON content. Please try again with valid JSON.")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    create_firebase_credentials()
