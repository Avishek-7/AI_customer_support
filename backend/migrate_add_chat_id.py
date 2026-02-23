"""
Migration script to add chat_id column to documents table
Run this once to update your database schema
"""
from core.database import engine
from sqlalchemy import inspect, text

async def migrate():
    async with engine.begin() as connection:
        def _get_columns(sync_conn):
            inspector = inspect(sync_conn)
            return {col["name"] for col in inspector.get_columns("documents")}

        columns = await connection.run_sync(_get_columns)

        if "chat_id" not in columns:
            print("Adding chat_id column to documents table...")
            await connection.execute(text("""
                ALTER TABLE documents 
                ADD COLUMN chat_id INTEGER REFERENCES chats(id) ON DELETE SET NULL
            """))
            await connection.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_documents_chat_id ON documents(chat_id)
            """))
            print("✅ Migration completed successfully!")
        else:
            print("✅ Column chat_id already exists, no migration needed.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate())
