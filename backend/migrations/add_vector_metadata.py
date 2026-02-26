"""
Migration script to create vector_metadata table for hybrid vector storage.

This enables storing vector metadata in PostgreSQL while keeping vectors in FAISS:
- PostgreSQL: metadata, relationships, SQL queries
- FAISS: fast similarity search

Run this script:
    python -m backend.migrations.add_vector_metadata
"""

from sqlalchemy import create_engine, text
from core.config import settings
from utils.logger import get_logger

logger = get_logger("migration.add_vector_metadata")


def migrate():
    """Create vector_metadata table"""
    
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        logger.info("Creating vector_metadata table...")
        
        # Check if table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'vector_metadata'
            );
        """))
        exists = result.scalar()
        
        if exists:
            logger.info("vector_metadata table already exists")
            return
        
        # Create table
        conn.execute(text("""
            CREATE TABLE vector_metadata (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                faiss_index INTEGER NOT NULL,
                embedding_model TEXT DEFAULT 'all-MiniLM-L6-v2',
                chunk_length INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Create indexes
        conn.execute(text("""
            CREATE INDEX idx_vector_document_id ON vector_metadata(document_id);
        """))
        
        conn.execute(text("""
            CREATE INDEX idx_vector_document_chunk ON vector_metadata(document_id, chunk_index);
        """))
        
        conn.execute(text("""
            CREATE INDEX idx_vector_faiss_index ON vector_metadata(faiss_index);
        """))
        
        conn.commit()
        
        logger.info("✅ vector_metadata table created successfully with indexes")
        logger.info("Hybrid vector storage is now enabled!")


if __name__ == "__main__":
    try:
        migrate()
        print("✅ Migration completed successfully")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
