"""
Migration script to add llm_provider column to app_settings table.
Run this script once to update your database schema.
"""
from __future__ import annotations

import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from app.db.session import engine

def migrate():
    """Add llm_provider column to app_settings table if it doesn't exist."""
    with engine.connect() as conn:
        # Check if column exists (PostgreSQL specific)
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='app_settings' AND column_name='llm_provider'
        """)
        result = conn.execute(check_query)
        column_exists = result.fetchone() is not None
        
        if column_exists:
            print("[OK] Column 'llm_provider' already exists in 'app_settings' table.")
            return
        
        # Add the column
        print("Adding 'llm_provider' column to 'app_settings' table...")
        alter_query = text("""
            ALTER TABLE app_settings 
            ADD COLUMN llm_provider VARCHAR(20) NOT NULL DEFAULT 'gemini'
        """)
        conn.execute(alter_query)
        conn.commit()
        print("[OK] Successfully added 'llm_provider' column with default value 'gemini'.")
        
        # Update any existing rows to have the default value (shouldn't be needed but safe)
        update_query = text("""
            UPDATE app_settings 
            SET llm_provider = 'gemini' 
            WHERE llm_provider IS NULL
        """)
        conn.execute(update_query)
        conn.commit()
        print("[OK] Migration completed successfully!")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

