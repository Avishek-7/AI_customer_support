#!/usr/bin/env python3
"""
Migration using SQLAlchemy to add missing columns
"""
import sys
import os

# Add parent directory to path so we can import core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import engine

try:
    with engine.begin() as connection:
        print("Adding index_status column...")
        try:
            connection.execute(text("ALTER TABLE documents ADD COLUMN index_status VARCHAR DEFAULT 'pending'"))
            print("✓ index_status column added")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ index_status column already exists")
            else:
                raise
        
        print("Adding chunk_count column...")
        try:
            connection.execute(text("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0"))
            print("✓ chunk_count column added")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("✓ chunk_count column already exists")
            else:
                raise
    
    print("\n✓ Migration completed successfully!")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ Migration failed: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
