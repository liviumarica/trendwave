import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-for-testing')

# Initialize Firestore
try:
    # Get project ID from environment variables
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set")
    
    print(f"Connecting to Firestore in project: {project_id}")
    
    # Initialize Firestore client with explicit project ID (use default database)
    db = firestore.Client(project=project_id)
    
    # Test the connection by trying to list collections
    try:
        collections = db.collections()
        print("Successfully connected to Firestore!")
        print(f"Available collections: {[col.id for col in collections]}")
    except Exception as e:
        print(f"Warning: Could not list collections - {str(e)}")
        print("This might be normal if the database is newly created.")
    
    print(f"Firestore client initialized for project: {project_id}")
    
except Exception as e:
    print(f"\nError initializing Firestore: {str(e)}")
    print("\nPlease make sure you have set up your Google Cloud project and credentials correctly:")
    print("1. Go to https://console.cloud.google.com/firestore and create a new Firestore database")
    print("2. Select 'Native' mode and choose a location")
    print("3. Make sure your service account has the 'Cloud Datastore User' role")
    print("4. Set GOOGLE_CLOUD_PROJECT to your Google Cloud project ID")
    print("5. Set GOOGLE_APPLICATION_CREDENTIALS to point to your service account key file")
    print("\nExample .env file content:")
    print("GOOGLE_CLOUD_PROJECT=your-project-id")
    print("GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json")
    print("\nFor more help, visit: https://cloud.google.com/firestore/docs/quickstart-servers")
    raise

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self._id = user_data.get('id')  # Document ID
        self._email = user_data.get('email')
        self._domain = user_data.get('domain', '')
        self._is_active = user_data.get('is_active', True)
        self._is_authenticated = True
        
    @property
    def id(self):
        return self._id
        
    @property
    def email(self):
        return self._email
        
    @property
    def domain(self):
        return self._domain
        
    @domain.setter
    def domain(self, value):
        self._domain = value
        
    @property
    def is_active(self):
        return self._is_active
        
    @is_active.setter
    def is_active(self, value):
        self._is_active = value
        
    @property
    def is_authenticated(self):
        return self._is_authenticated
        
    @is_authenticated.setter
    def is_authenticated(self, value):
        self._is_authenticated = value

    def get_id(self):
        return str(self._id) if self._id else None

@login_manager.user_loader
def load_user(user_id):
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            print(f"User not found: {user_id}")
            return None
            
        user_data = user_doc.to_dict()
        if not user_data.get('is_active', True):
            print(f"User account is disabled: {user_id}")
            return None
            
        user_data['id'] = user_id
        return User(user_data)
        
    except Exception as e:
        print(f"Error loading user {user_id}: {str(e)}")
        return None

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('select_domain'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        # Input validation
        if not email or '@' not in email:
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('register'))
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return redirect(url_for('register'))
        
        try:
            users_ref = db.collection('users')
            
            # Check if email already exists (case-insensitive)
            query = users_ref.where('email', '==', email).limit(1).stream()
            if any(1 for _ in query):
                flash('This email is already registered. Please log in or use a different email.', 'error')
                return redirect(url_for('login'))
            
            # Create new user document
            user_data = {
                'email': email,
                'password': generate_password_hash(password, method='pbkdf2:sha256'),
                'domain': '',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'is_active': True,
                'last_login': None
            }
            
            # Add user to Firestore in a transaction
            @firestore.transactional
            def create_user_transaction(transaction, users_ref, user_data):
                # Check again in transaction to prevent race condition
                existing = users_ref.where('email', '==', user_data['email']).limit(1).get(transaction=transaction)
                if existing:
                    return None
                
                # Create new user
                user_ref = users_ref.document()
                transaction.set(user_ref, user_data)
                return user_ref
            
            # Run the transaction
            user_ref = create_user_transaction(db.transaction(), users_ref, user_data)
            
            if not user_ref:
                flash('This email was just registered. Please try logging in.', 'error')
                return redirect(url_for('login'))
            
            # Log the user in
            user_data['id'] = user_ref.id
            user = User(user_data)
            login_user(user)
            
            flash('Registration successful! Please select your preferred domain.', 'success')
            return redirect(url_for('select_domain'))
            
        except Exception as e:
            print(f"Error during registration: {e}")
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('register'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('select_domain'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return redirect(url_for('login'))
        
        try:
            users_ref = db.collection('users')
            
            # Find user by email (case-insensitive)
            query = users_ref.where('email', '==', email).limit(1).stream()
            user_doc = next(query, None)
            
            if not user_doc:
                # Simulate password check to prevent timing attacks
                generate_password_hash('dummy_password')
                flash('Invalid email or password', 'error')
                return redirect(url_for('login'))
            
            user_data = user_doc.to_dict()
            
            # Check if account is active
            if not user_data.get('is_active', True):
                flash('This account has been deactivated', 'error')
                return redirect(url_for('login'))
            
            # Verify password
            if not check_password_hash(user_data['password'], password):
                flash('Invalid email or password', 'error')
                return redirect(url_for('login'))
            
            # Update last login time
            user_ref = users_ref.document(user_doc.id)
            user_ref.update({
                'last_login': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            # Log the user in
            user_data['id'] = user_doc.id
            user = User(user_data)
            login_user(user)
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('select_domain')
                
            flash('You have been logged in successfully!', 'success')
            return redirect(next_page)
            
        except Exception as e:
            print(f"Error during login: {e}")
            flash('An error occurred during login. Please try again.', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Log out the current user and clear their session."""
    try:
        # Update last activity before logging out
        user_ref = db.collection('users').document(current_user.id)
        user_ref.update({
            'last_activity': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Error updating last activity during logout: {e}")
    
    # Log the user out
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/select-domain', methods=['GET', 'POST'])
@login_required
def select_domain():
    """Handle domain selection for the current user."""
    ALLOWED_DOMAINS = ['AI', 'Sports', 'Finance']
    
    if request.method == 'POST':
        domain = request.form.get('domain')
        
        # Validate domain
        if not domain or domain not in ALLOWED_DOMAINS:
            flash('Please select a valid domain', 'error')
            return redirect(url_for('select_domain'))
        
        try:
            # Update user's domain in Firestore
            user_ref = db.collection('users').document(current_user.id)
            
            # Use a transaction to ensure data consistency
            @firestore.transactional
            def update_domain(transaction, user_ref, domain):
                user_doc = user_ref.get(transaction=transaction)
                if not user_doc.exists:
                    raise ValueError("User not found")
                
                transaction.update(user_ref, {
                    'domain': domain,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            # Execute the transaction
            update_domain(db.transaction(), user_ref, domain)
            
            # Update current_user object
            current_user.domain = domain
            
            flash(f'Successfully updated your domain to {domain}!', 'success')
            
        except Exception as e:
            print(f"Error updating domain: {e}")
            flash('An error occurred while updating your domain. Please try again.', 'error')
        
        return redirect(url_for('select_domain'))
    
    # For GET request, show the domain selection form
    try:
        # Get the latest user data from Firestore
        user_doc = db.collection('users').document(current_user.id).get()
        current_domain = user_doc.get('domain', '') if user_doc.exists else ''
    except Exception as e:
        print(f"Error fetching user data: {e}")
        current_domain = getattr(current_user, 'domain', '')
    
    return render_template('select_domain.html', 
                         current_domain=current_domain,
                         available_domains=ALLOWED_DOMAINS)

if __name__ == '__main__':
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
