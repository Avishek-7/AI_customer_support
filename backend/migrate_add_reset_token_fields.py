"""
Migration script to add reset token fields to users table.
Run this once to update your database schema.
"""
from sqlalchemy import inspect, text

from core.database import engine


async def migrate():
    async with engine.begin() as connection:
        def _get_columns(sync_conn):
            inspector = inspect(sync_conn)
            return {col["name"] for col in inspector.get_columns("users")}

        columns = await connection.run_sync(_get_columns)

        if "reset_token" not in columns:
            print("Adding reset_token column to users table...")
            await connection.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR"))
            print("✅ Added reset_token")
        else:
            print("✅ Column reset_token already exists")

        if "reset_token_used" not in columns:
            print("Adding reset_token_used column to users table...")
            await connection.execute(text("ALTER TABLE users ADD COLUMN reset_token_used BOOLEAN DEFAULT FALSE"))
            print("✅ Added reset_token_used")
        else:
            print("✅ Column reset_token_used already exists")


if __name__ == "__main__":
    import asyncio

    asyncio.run(migrate())
