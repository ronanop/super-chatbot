"""
Migration script to add image_url column to messages table.
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def migrate_add_image_url():
    print("Adding image_url column to messages table...")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns('messages')
        column_names = [col['name'] for col in columns]

        if 'image_url' not in column_names:
            with engine.connect() as connection:
                connection.execute(text("ALTER TABLE messages ADD COLUMN image_url VARCHAR(512)"))
                connection.commit()
            print("SUCCESS: Added image_url column to messages table.")
        else:
            print("SUCCESS: image_url column already exists. Migration not needed.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_add_image_url()

