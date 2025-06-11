# TrendWave - Restaurant Recommendation Chatbot

A modern, AI-powered restaurant recommendation system that helps users discover the perfect dining experience through natural language conversations. Built with Flask, Firestore, and Google's Gemini AI.

## Features

- 🔐 **User Authentication**: Secure signup and login with email/password
- 💬 **AI-Powered Chat**: Natural language processing for restaurant recommendations
- 🔍 **Smart Search**: Vector-based semantic search for finding the perfect restaurant
- 📱 **Responsive UI**: Mobile-friendly interface built with Tailwind CSS
- 🔄 **Real-time Updates**: Chat history and user preferences saved in Firestore

## Tech Stack

- **Backend**: Python, Flask, Firestore
- **AI**: Google Gemini 2.5 Flash
- **Database**: Google Cloud Firestore
- **Frontend**: HTML5, JavaScript, Tailwind CSS
- **Authentication**: Flask-Login, Werkzeug Security

## Prerequisites

- Python 3.9+
- Google Cloud Project with Firestore enabled
- Gemini API Key
- Node.js and npm (for Tailwind CSS)

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/trendwave.git
   cd trendwave
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```env
   # Flask
   FLASK_APP=main.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   
   # Google Cloud
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
   
   # Gemini
   GEMINI_API_KEY=your-gemini-api-key
   
   # MongoDB (if using)
   MONGODB_URI=your-mongodb-uri
   ```

5. **Initialize the database**
   Run the following command to initialize the Firestore database:
   ```bash
   python -c "from main import db; print('Firestore initialized successfully')"
   ```

## Running the Application

1. **Start the development server**
   ```bash
   flask run --debug
   ```

2. **Access the application**
   Open your browser and go to `http://localhost:5000`

## Project Structure

```
trendwave/
├── .env                    # Environment variables
├── .gitignore
├── README.md
├── requirements.txt        # Python dependencies
├── main.py                # Application entry point
│
├── models/               # Data models
│   └── user.py           # User model and authentication
│
├── routes/               # Application routes
│   ├── __init__.py
│   ├── auth.py           # Authentication routes
│   └── chat.py           # Chat API routes
│
├── services/             # Business logic
│   └── vector_store.py   # Vector search functionality
│
├── static/               # Static files (CSS, JS, images)
│   ├── css/
│   └── js/
│
└── templates/            # HTML templates
    ├── auth/
    │   ├── login.html
    │   └── register.html
    └── chat.html
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FLASK_APP` | Flask application entry point | No | `main.py` |
| `FLASK_ENV` | Flask environment (development/production) | No | `development` |
| `SECRET_KEY` | Secret key for session management | Yes | - |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud project ID | Yes | - |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account key file | Yes | - |
| `GEMINI_API_KEY` | Google Gemini API key | Yes | - |
| `MONGODB_URI` | MongoDB connection string | No | - |

## API Endpoints

### Authentication

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login user
- `GET /auth/logout` - Logout user

### Chat

- `GET /chat` - Chat interface
- `POST /api/chat` - Send a message to the chatbot

## Contributing

1. Fork the repository
2. Create a new branch: `git checkout -b feature/your-feature`
3. Make your changes and commit: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/)
- [Firestore](https://firebase.google.com/docs/firestore)
- [Google Gemini](https://ai.google.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
