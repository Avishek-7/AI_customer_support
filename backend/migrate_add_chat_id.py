"""
Migration script to add chat_id column to documents table
Run this once to update your database schema
"""
from core.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as connection:
        # Check if column exists
        result = connection.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='documents' AND column_name='chat_id'
        """))
        
        if result.fetchone() is None:
            print("Adding chat_id column to documents table...")
            connection.execute(text("""
                ALTER TABLE documents 
                ADD COLUMN chat_id INTEGER REFERENCES chats(id)
            """))
            connection.commit()
            print("✅ Migration completed successfully!")
        else:
            print("✅ Column chat_id already exists, no migration needed.")

if __name__ == "__main__":
    migrate()
