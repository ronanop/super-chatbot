"""
Authentication utilities for password hashing and JWT token generation.
"""
from __future__ import annotations

import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional

# JWT secret key (should be in environment variable)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

# Bcrypt rounds (higher = more secure but slower, 12 is a good balance)
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (secure password hashing algorithm)."""
    if not password:
        raise ValueError("Password cannot be empty")
    # Generate salt and hash password
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    # Return as string (bcrypt includes salt in the hash)
    return password_hash.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    if not password or not password_hash:
        return False
    try:
        # bcrypt automatically handles salt extraction and comparison
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except (ValueError, TypeError, AttributeError):
        # Handle legacy SHA-256 hashes during migration
        # This allows gradual migration from old to new password hashing
        try:
            import hashlib
            if ":" in password_hash:
                salt, stored_hash = password_hash.split(":", 1)
                computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                if secrets.compare_digest(computed_hash, stored_hash):
                    # Password verified with old method - should be rehashed on next login
                    return True
        except Exception:
            pass
        return False


def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token for a user."""
    expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expiration,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

