"""
Script to create the default user if it doesn't exist.
"""
from app.db.session import SessionLocal
from app.db import models
from app.auth.utils import hash_password

def create_default_user():
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.email == 'admin@askcache.ai').first()
        
        if user:
            if user.password_hash:
                print(f"User '{user.email}' already exists with password set.")
            else:
                # User exists but no password - set it
                user.password_hash = hash_password('admin123')
                db.commit()
                print(f"SUCCESS: Set password for existing user '{user.email}'")
        else:
            # Create new user
            password_hash = hash_password('admin123')
            user = models.User(
                email='admin@askcache.ai',
                name='Admin User',
                password_hash=password_hash,
            )
            db.add(user)
            db.commit()
            print(f"SUCCESS: Created default user 'admin@askcache.ai' with password 'admin123'")
            
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_default_user()

