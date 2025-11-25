"""
Migration script to add password_hash column to users table.
Run this once to update existing database schema.
"""
from __future__ import annotations

from sqlalchemy import text
from app.db.session import SessionLocal, engine


def migrate_add_password_hash():
    """Add password_hash column to users table if it doesn't exist."""
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='password_hash'
        """))
        
        if result.fetchone():
            print("SUCCESS: password_hash column already exists. Migration not needed.")
            return
        
        # Add the column
        print("Adding password_hash column to users table...")
        db.execute(text("""
            ALTER TABLE users 
            ADD COLUMN password_hash VARCHAR(255)
        """))
        db.commit()
        print("SUCCESS: Added password_hash column to users table.")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_add_password_hash()

