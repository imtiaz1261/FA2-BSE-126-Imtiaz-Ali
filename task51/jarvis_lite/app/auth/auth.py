"""
JWT-based authentication for Jarvis-Lite.

Simple login/signup with token generation.
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

logger = logging.getLogger(__name__)


class AuthManager:
    """JWT-based authentication manager."""

    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256") -> None:
        """
        Initialize authentication manager.
        
        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm (default: HS256)
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = algorithm

    def create_token(self, user_id: str, email: str, expires_in: int = 24) -> Optional[str]:
        """
        Create JWT token.
        
        Args:
            user_id: User ID
            email: User email
            expires_in: Token expiration in hours
            
        Returns:
            JWT token or None if failed
        """
        if not JWT_AVAILABLE:
            logger.warning("JWT not available, returning mock token")
            return f"mock_token_{user_id}"

        try:
            payload = {
                "user_id": user_id,
                "email": email,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(hours=expires_in),
                "type": "access"
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Token created for {email}")
            return token
        
        except Exception as e:
            logger.exception(f"Token creation failed: {e}")
            return None

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Token payload or None if invalid
        """
        if not JWT_AVAILABLE:
            logger.warning("JWT not available, accepting mock token")
            return {"user_id": "mock_user", "email": "mock@example.com"}

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            logger.info(f"Token verified for {payload.get('email')}")
            return payload
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
        except Exception as e:
            logger.exception(f"Token verification failed: {e}")
            return None

    def is_token_valid(self, token: str) -> bool:
        """Check if token is valid."""
        return self.verify_token(token) is not None

    def refresh_token(self, token: str, expires_in: int = 24) -> Optional[str]:
        """
        Refresh an existing token.
        
        Args:
            token: Current token
            expires_in: New expiration in hours
            
        Returns:
            New token or None if current token invalid
        """
        payload = self.verify_token(token)
        if not payload:
            return None
        
        return self.create_token(
            payload["user_id"],
            payload["email"],
            expires_in=expires_in
        )


class PasswordManager:
    """Password hashing and verification."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password securely.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        try:
            import bcrypt
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except ImportError:
            logger.warning("bcrypt not available, using simple hash")
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hashed: Hashed password
            
        Returns:
            True if password matches
        """
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except ImportError:
            logger.warning("bcrypt not available, using simple verification")
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest() == hashed
