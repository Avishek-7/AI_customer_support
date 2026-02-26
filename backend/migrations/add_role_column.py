"""
Migration: Add role column to users table
Run this script to add the role column to existing users table
"""
import sys
import os

# Add parent directory to path so we can import core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from core.config import settings

def migrate():
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # Add role column with default value 'user'
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"
            ))
            conn.commit()
            print("✓ Successfully added role column to users table")
            
            # Optionally set first user as admin
            result = conn.execute(text("SELECT id FROM users ORDER BY id LIMIT 1"))
            first_user = result.fetchone()
            if first_user:
                conn.execute(text(
                    f"UPDATE users SET role = 'admin' WHERE id = {first_user[0]}"
                ))
                conn.commit()
                print(f"✓ Set user ID {first_user[0]} as admin")
                
        except Exception as e:
            print(f"✗ Migration failed: {e}")
            print("Note: Column might already exist")

if __name__ == "__main__":
    migrate()
