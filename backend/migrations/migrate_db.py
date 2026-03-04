#!/usr/bin/env python3
"""
Direct database migration - add missing columns to documents table
"""
import os
import sys
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Get database URL
db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

# Parse the database URL
parsed = urlparse(db_url)
password = unquote(parsed.password) if parsed.password else ''

try:
    import psycopg2
    
    conn = psycopg2.connect(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username or 'postgres',
        password=password
    )
    
    cursor = conn.cursor()
    
    print("Adding index_status column...")
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN index_status VARCHAR(50) DEFAULT 'pending'")
        print("✓ index_status column added")
    except psycopg2.Error as e:
        if "already exists" in str(e):
            print("✓ index_status column already exists")
            conn.rollback()
        else:
            print(f"✗ Error: {e}")
    
    print("Adding chunk_count column...")
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0")
        print("✓ chunk_count column added")
    except psycopg2.Error as e:
        if "already exists" in str(e):
            print("✓ chunk_count column already exists")
            conn.rollback()
        else:
            print(f"✗ Error: {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n✓ Migration completed successfully!")
    
except ImportError:
    print("psycopg2 not installed, trying SQLAlchemy...")
    try:
        from sqlalchemy import text, create_engine
        
        # Convert psycopg2 URL to standard format for SQLAlchemy
        engine = create_engine(db_url)
        
        with engine.begin() as connection:
            try:
                connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS index_status VARCHAR(50) DEFAULT 'pending'"))
                print("✓ index_status column added")
            except Exception as e:
                print(f"✗ Error: {e}")
            
            try:
                connection.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS chunk_count INTEGER DEFAULT 0"))
                print("✓ chunk_count column added")
            except Exception as e:
                print(f"✗ Error: {e}")
        
        print("\n✓ Migration completed successfully!")
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)
    
except Exception as e:
    print(f"✗ Failed to connect to database: {e}")
    sys.exit(1)

