"""
Migration: Add timestamp column to chat_history table
Run this script to add the timestamp column to existing chat_history table
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
                WHERE table_name='chat_history' AND column_name='timestamp'
                """
            ))
            
            if result.fetchone():
                print("✓ Column timestamp already exists in chat_history table")
                return
            
            # Add timestamp column with default value as current timestamp
            conn.execute(text(
                "ALTER TABLE chat_history ADD COLUMN timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL"
            ))
            conn.commit()
            print("✓ Successfully added timestamp column to chat_history table")
            
        except Exception as e:
            print(f"✗ Error adding timestamp column: {str(e)}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
