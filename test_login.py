"""Test login credentials."""
from app.db.session import SessionLocal
from app.db import models
from app.auth.utils import verify_password

db = SessionLocal()
try:
    user = db.query(models.User).filter(models.User.email == 'admin@askcache.ai').first()
    if user:
        print(f"SUCCESS: User found: {user.email}")
        print(f"SUCCESS: Password hash exists: {user.password_hash is not None}")
        if user.password_hash:
            is_valid = verify_password('admin123', user.password_hash)
            print(f"SUCCESS: Password 'admin123' is valid: {is_valid}")
    else:
        print("ERROR: User not found")
finally:
    db.close()

