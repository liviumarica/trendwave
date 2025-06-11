from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import firestore
from extensions import db

class User(UserMixin):
    """User model for authentication and user data management."""
    
    def __init__(self, id, email, password_hash, _is_active=True):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self._is_active = _is_active

    @property
    def is_active(self):
        """Required by Flask-Login. Returns True if the user is active."""
        return self._is_active

    def get_id(self):
        """Required by Flask-Login. Returns the user ID as a string."""
        return str(self.id)

    def verify_password(self, password):
        """Verify the provided password against the stored hashed password."""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get(user_id):
        """Loads a user from the database."""
        try:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                return User(
                    id=user_doc.id,
                    email=user_data.get('email'),
                    password_hash=user_data.get('password'),
                    _is_active=user_data.get('is_active', True)
                )
            return None
        except Exception as e:
            print(f"Error loading user {user_id}: {e}")
            return None

    @staticmethod
    def get_by_email(email):
        """Loads a user from the database by email."""
        try:
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email.lower()).limit(1).stream()
            user_doc = next(query, None)
            
            if user_doc:
                user_data = user_doc.to_dict()
                return User(
                    id=user_doc.id,
                    email=user_data.get('email'),
                    password_hash=user_data.get('password'),
                    _is_active=user_data.get('is_active', True)
                )
            return None
        except Exception as e:
            print(f"Error getting user by email {email}: {e}")
            return None
            
    @staticmethod
    def create(email, password):
        """Creates a new user in the database.""" 
        try:
            hashed_password = generate_password_hash(password)
            user_ref = db.collection('users').document()
            user_ref.set({
                'email': email.lower(),
                'password': hashed_password,
                'is_active': True,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            return User.get(user_ref.id)
        except Exception as e:
            print(f"Error creating user {email}: {e}")
            return None

    def update_last_login(self):
        """Updates the last login timestamp for the user."""
        try:
            user_ref = db.collection('users').document(self.id)
            user_ref.update({
                'last_login': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Error updating last login for user {self.id}: {e}")

    def __repr__(self):
        """
        String representation of the User object.
        
        Returns:
            str: A string representation of the user
        """
        return f"<User {self.email}>"

# Add type hints for better IDE support
if False:  # This block is only for type checking
    from typing import Optional, Dict, Any
    
    class IUser(UserMixin):
        id: str
        email: str
        _password: str
        is_active: bool
        created_at: datetime
        last_login: Optional[datetime]
        role: str
        
        def __init__(self, user_data: Dict[str, Any]) -> None: ...
        @property
        def password(self) -> str: ...
        @password.setter
        def password(self, password: str) -> None: ...
        def verify_password(self, password: str) -> bool: ...
        def get_id(self) -> str: ...
        def to_dict(self) -> Dict[str, Any]: ...
        def update_last_login(self) -> None: ...
        @classmethod
        def create_new_user(cls, email: str, password: str, **kwargs: Any) -> 'IUser': ...
