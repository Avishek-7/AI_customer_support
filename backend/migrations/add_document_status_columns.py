"""
Migration script to add index_status and chunk_count columns to documents table.
Run this from the backend directory: python migrations/add_document_status_columns.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import engine

def migrate():
    try:
        with engine.begin() as connection:
            # Add index_status column if it doesn't exist
            try:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN index_status VARCHAR(50) DEFAULT 'pending'")
                )
                print("✓ index_status column added")
            except Exception as e:
                if "already exists" in str(e):
                    print("✓ index_status column already exists")
                else:
                    raise
            
            # Add chunk_count column if it doesn't exist
            try:
                connection.execute(
                    text("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0")
                )
                print("✓ chunk_count column added")
            except Exception as e:
                if "already exists" in str(e):
                    print("✓ chunk_count column already exists")
                else:
                    raise
        
        print("\n✓ Migration completed successfully!")
        return True
    except Exception as e:
        print(f"✗ Migration failed: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
