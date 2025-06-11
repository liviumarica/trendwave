# TrendWave

A Flask-based web application for exploring trends in different domains. This MVP includes user authentication and domain selection functionality using Firebase Firestore.

## Features

- User registration and authentication with email/password
- Secure password hashing with Werkzeug
- Firebase Firestore integration for data storage
- Domain selection (AI, Sports, Finance)
- Responsive UI with Tailwind CSS
- Docker containerization
- Ready for Google Cloud Run deployment

## Prerequisites

- Python 3.11+
- Firebase Project with Firestore enabled
- Firebase Admin SDK credentials (JSON)
- Docker (for containerization)
- Google Cloud SDK (for deployment)

## Firebase Setup

1. **Create a Firebase Project**
   - Go to the [Firebase Console](https://console.firebase.google.com/)
   - Click "Add project" and follow the setup wizard
   - In the project, enable Firestore Database if not already enabled

2. **Get Service Account Credentials**
   - Go to Project Settings > Service Accounts
   - Click "Generate new private key" and save the JSON file
   - Rename the downloaded file to `firebase-credentials.json` and place it in the project root

3. **Set Up Firestore Database**
   - In the Firebase Console, go to Firestore Database
   - Click "Create database" if you haven't already
   - Start in production mode (you can adjust rules later)
   - The app will automatically create the necessary collections

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TrendWave
   ```

2. **Set up environment variables**
   - Copy `.env.example` to `.env`
   - Update `FIREBASE_PROJECT_ID` with your Firebase project ID
   - Set a strong `SECRET_KEY` for Flask sessions
   - Place your `firebase-credentials.json` in the project root

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application locally**
   ```bash
   python main.py
   ```
   The app will be available at `http://localhost:8080`

## Running with Docker

1. **Build the Docker image**
   ```bash
   docker build -t trendwave .
   ```

2. **Run the container**
   ```bash
   docker run -p 8080:8080 --env-file .env trendwave
   ```

## Deployment to Google Cloud Run

1. **Install Google Cloud SDK**
   Follow the [official installation guide](https://cloud.google.com/sdk/docs/install)

2. **Authenticate with Google Cloud**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Enable necessary APIs**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   ```

4. **Build and deploy the container**
   ```bash
   # Build the container
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/trendwave

   # Deploy to Cloud Run
   gcloud run deploy trendwave \
     --image gcr.io/YOUR_PROJECT_ID/trendwave \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars=MONGODB_URI=YOUR_MONGODB_URI,SECRET_KEY=YOUR_SECRET_KEY
   ```

5. **Access your application**
   After deployment, you'll receive a URL where your application is accessible.

## Project Structure

```
TrendWave/
├── .env.example           # Environment variables template
├── Dockerfile             # Docker configuration
├── README.md             # This file
├── main.py               # Main application file
├── requirements.txt      # Python dependencies
└── templates/            # HTML templates
    ├── base.html        # Base template
    ├── login.html       # Login page
    ├── register.html    # Registration page
    └── select_domain.html # Domain selection page
```

## Next Steps

1. Implement trend analysis features
2. Add user profile management
3. Integrate with news APIs for real-time data
4. Add more domain options
5. Implement user preferences and notifications

## License

This project is licensed under the MIT License - see the LICENSE file for details.
