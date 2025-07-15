"""
Simple authentication system for portfolio management.
"""
import hashlib
import secrets
import sqlite3
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from contextlib import contextmanager

from config import config
from exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)


class AuthManager:
    """Simple authentication manager with session support."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database.path
        self.sessions: Dict[str, Dict] = {}  # session_token -> user_info
        self.session_timeout = timedelta(hours=24)  # 24 hour sessions
        
        # Initialize auth tables
        self._initialize_auth_tables()
    
    @contextmanager
    def _get_cursor(self):
        """Context manager for database cursor."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
    
    def _initialize_auth_tables(self) -> None:
        """Initialize authentication tables."""
        with self._get_cursor() as cursor:
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Create default demo user
            self._create_default_user()
    
    def _create_default_user(self) -> None:
        """Create a default user for demonstration."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("SELECT 1 FROM users WHERE username = 'demo'")
                if not cursor.fetchone():
                    user_id = "demo_user"
                    username = "demo"
                    email = "demo@example.com"
                    password_hash = self._hash_password("demo123")
                    
                    cursor.execute('''
                        INSERT INTO users (user_id, username, email, password_hash)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, username, email, password_hash))
                    
                    logger.info("Created default demo user (username: demo, password: demo123)")
        except Exception as e:
            logger.error(f"Failed to create default user: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against stored hash."""
        try:
            salt, password_hash = stored_hash.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
        except ValueError:
            return False
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate a user and create a session.
        
        Returns:
            Dict with user info and session token, or None if authentication fails
        """
        if not username or not password:
            return None
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute('''
                    SELECT user_id, username, email, password_hash 
                    FROM users 
                    WHERE username = ?
                ''', (username,))
                
                user_row = cursor.fetchone()
                if not user_row:
                    logger.warning(f"Authentication failed: user '{username}' not found")
                    return None
                
                if not self._verify_password(password, user_row['password_hash']):
                    logger.warning(f"Authentication failed: invalid password for user '{username}'")
                    return None
                
                # Create session
                session_token = self._create_session(user_row['user_id'])
                
                user_info = {
                    'user_id': user_row['user_id'],
                    'username': user_row['username'],
                    'email': user_row['email'],
                    'session_token': session_token
                }
                
                logger.info(f"User '{username}' authenticated successfully")
                return user_info
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def _create_session(self, user_id: str) -> str:
        """Create a new session for the user."""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + self.session_timeout
        
        with self._get_cursor() as cursor:
            # Clean up old sessions
            cursor.execute('''
                DELETE FROM sessions 
                WHERE user_id = ? OR expires_at < datetime('now')
            ''', (user_id,))
            
            # Create new session
            cursor.execute('''
                INSERT INTO sessions (session_token, user_id, expires_at)
                VALUES (?, ?, ?)
            ''', (session_token, user_id, expires_at))
        
        # Store in memory for quick access
        self.sessions[session_token] = {
            'user_id': user_id,
            'expires_at': expires_at
        }
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """
        Validate a session token and return user_id.
        
        Returns:
            user_id if session is valid, None otherwise
        """
        if not session_token:
            return None
        
        # Check in-memory sessions first
        if session_token in self.sessions:
            session_info = self.sessions[session_token]
            if datetime.now() < session_info['expires_at']:
                return session_info['user_id']
            else:
                del self.sessions[session_token]
        
        # Check database
        try:
            with self._get_cursor() as cursor:
                cursor.execute('''
                    SELECT user_id FROM sessions 
                    WHERE session_token = ? AND expires_at > datetime('now')
                ''', (session_token,))
                
                session_row = cursor.fetchone()
                if session_row:
                    return session_row['user_id']
                else:
                    # Clean up expired session
                    cursor.execute('''
                        DELETE FROM sessions 
                        WHERE session_token = ?
                    ''', (session_token,))
                    return None
                    
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def register_user(self, username: str, email: str, password: str) -> bool:
        """
        Register a new user.
        
        Returns:
            True if successful, False otherwise
        """
        if not username or not email or not password:
            return False
        
        if len(password) < 6:
            return False
        
        try:
            with self._get_cursor() as cursor:
                user_id = f"user_{secrets.token_hex(8)}"
                password_hash = self._hash_password(password)
                
                cursor.execute('''
                    INSERT INTO users (user_id, username, email, password_hash)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, email, password_hash))
                
                logger.info(f"Registered new user: {username}")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"Registration failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user information by user_id."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute('''
                    SELECT user_id, username, email, created_at 
                    FROM users 
                    WHERE user_id = ?
                ''', (user_id,))
                
                user_row = cursor.fetchone()
                if user_row:
                    return {
                        'user_id': user_row['user_id'],
                        'username': user_row['username'],
                        'email': user_row['email'],
                        'created_at': user_row['created_at']
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    def logout(self, session_token: str) -> bool:
        """Logout a user by invalidating their session."""
        if not session_token:
            return False
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute('''
                    DELETE FROM sessions 
                    WHERE session_token = ?
                ''', (session_token,))
            
            # Remove from memory
            if session_token in self.sessions:
                del self.sessions[session_token]
            
            return True
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False


# Global auth manager instance
auth_manager = AuthManager()