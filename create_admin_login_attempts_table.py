"""
Create admin_login_attempts table for security tracking.
Run this script to add the security table to your database.
"""
from app.db.session import SessionLocal
from app.db import models
from sqlalchemy import inspect

def create_admin_login_attempts_table():
    """Create admin_login_attempts table if it doesn't exist."""
    db = SessionLocal()
    try:
        # Check if table already exists
        inspector = inspect(db.bind)
        existing_tables = inspector.get_table_names()
        
        if "admin_login_attempts" in existing_tables:
            print("[OK] Table 'admin_login_attempts' already exists.")
            return
        
        # Create the table
        models.AdminLoginAttempt.__table__.create(bind=db.bind, checkfirst=True)
        db.commit()
        print("[OK] Successfully created 'admin_login_attempts' table.")
        print("\nSecurity features enabled:")
        print("  - Login attempt tracking")
        print("  - IP-based brute force protection")
        print("  - Rate limiting")
        print("  - Account lockout after 5 failed attempts")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error creating table: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_login_attempts_table()

