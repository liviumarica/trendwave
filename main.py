import os
from flask import Flask, redirect, url_for
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Configure basic logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

# Load environment variables from .env file
load_dotenv()

# Import extensions from the extensions module
from extensions import db, login_manager

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'dev-key-for-testing')
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Configure Gemini
    try:
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        print("✅ Successfully configured Gemini API")
    except Exception as e:
        print(f"❌ Error initializing Gemini: {e}")
        print("ℹ️ Please make sure you have set GEMINI_API_KEY in your environment variables")

    # Initialize Flask-Login with the app
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.login_message = 'Please log in to access this page.'

    # Import User model here to avoid circular imports
    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        """Load user from Firestore by user_id"""
        return User.get(user_id)

    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.chat import chat_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(chat_bp, url_prefix='') # Chat is at the root
    
    print("✅ Registered blueprints")

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

from routes.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

# Initialize FastAPI app
fastapi_app = FastAPI(title="Restaurant Recommendation API",
             description="RAG-based restaurant recommendation system using Gemini and MongoDB Atlas",
             version="1.0.0")

# CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize services
vector_store = VectorStore()

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

# Authentication functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# API Endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # In a real application, you would validate the username and password against a database
    # For demo purposes, we'll use a simple check
    if form_data.username != "admin" or form_data.password != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Restaurant Recommendation API"}

@app.get("/api/recommend")
async def get_recommendations(
    query: str,
    limit: int = 3,
    token: str = Depends(oauth2_scheme)
):
    try:
        # Verify JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get recommendations
        result = vector_store.get_recommendations(query, limit)
        return result
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
