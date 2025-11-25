"""
Verify that the llm_provider column exists and can be queried.
"""
from __future__ import annotations

from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from app.db.session import engine
from app.db import models
from app.db.session import SessionLocal

def verify():
    """Verify the column exists and can be queried."""
    print("Verifying migration...")
    
    # Test 1: Raw SQL query
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns 
            WHERE table_name='app_settings' AND column_name='llm_provider'
        """))
        row = result.fetchone()
        if row:
            print(f"[OK] Column exists: {row[0]} ({row[1]}, default: {row[2]})")
        else:
            print("[ERROR] Column does not exist!")
            return False
    
    # Test 2: SQLAlchemy model query
    db = SessionLocal()
    try:
        settings = db.query(models.AppSettings).first()
        if settings:
            provider = settings.llm_provider
            print(f"[OK] SQLAlchemy query successful. Current provider: {provider}")
            return True
        else:
            print("[OK] No settings record exists yet, but column is accessible.")
            return True
    except Exception as e:
        print(f"[ERROR] SQLAlchemy query failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    if verify():
        print("\n[SUCCESS] Migration verified! Please restart your server.")
        sys.exit(0)
    else:
        print("\n[FAILED] Migration verification failed!")
        sys.exit(1)


