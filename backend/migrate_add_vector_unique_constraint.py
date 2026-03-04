"""
Migration script to add unique constraint on vector_metadata(document_id, chunk_index).
"""

from sqlalchemy import text

from core.database import engine


async def migrate():
    async with engine.begin() as connection:
        dialect = connection.dialect.name

        if dialect == "postgresql":
            await connection.execute(
                text(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_constraint
                            WHERE conname = 'uq_vector_document_chunk'
                        ) THEN
                            ALTER TABLE vector_metadata
                            ADD CONSTRAINT uq_vector_document_chunk UNIQUE (document_id, chunk_index);
                        END IF;
                    END
                    $$;
                    """
                )
            )
            print("✅ PostgreSQL unique constraint ensured")
            return

        if dialect == "sqlite":
            await connection.execute(
                text(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_vector_document_chunk
                    ON vector_metadata(document_id, chunk_index)
                    """
                )
            )
            print("✅ SQLite unique index ensured")
            return

        print(f"⚠️ Unsupported dialect for automated constraint migration: {dialect}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(migrate())
