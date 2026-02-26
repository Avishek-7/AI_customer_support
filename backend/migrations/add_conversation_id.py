#!/usr/bin/env python3
"""
Migration: Add conversation_id to chat_history table

This migration adds the conversation_id column to link chat messages to conversations.
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
    
    print("Adding conversation_id column to chat_history...")
    try:
        cursor.execute("""
            ALTER TABLE chat_history 
            ADD COLUMN conversation_id INTEGER 
            REFERENCES conversations(id) ON DELETE CASCADE
        """)
        conn.commit()
        print("✓ conversation_id column added successfully")
    except psycopg2.Error as e:
        if "already exists" in str(e):
            print("✓ conversation_id column already exists")
            conn.rollback()
        else:
            print(f"✗ Error: {e}")
            conn.rollback()
            sys.exit(1)
    
    cursor.close()
    conn.close()
    print("\n✓ Migration completed successfully!")
    
except ImportError:
    print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
