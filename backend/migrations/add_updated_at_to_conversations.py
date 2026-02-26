"""
Migration: Add updated_at column to conversations table
Run this script to add the updated_at column to existing conversations table
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
            # Check if column already exists
            result = conn.execute(text(
                """
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='conversations' AND column_name='updated_at'
                """
            ))
            
            if result.fetchone():
                print("✓ Column updated_at already exists in conversations table")
                return
            
            # Add updated_at column with default value as current timestamp
            conn.execute(text(
                "ALTER TABLE conversations ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ))
            conn.commit()
            print("✓ Successfully added updated_at column to conversations table")
            
        except Exception as e:
            print(f"✗ Error adding updated_at column: {str(e)}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
