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
            if "users" not in inspector.get_table_names():
                return set()
            return {col["name"] for col in inspector.get_columns("users")}

        columns = await connection.run_sync(_get_columns)

        if not columns:
            print("⚠️ users table not found; skipping migration")
            return

        if "reset_token" not in columns:
            print("Adding reset_token column to users table...")
            await connection.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)"))
            print("✅ Added reset_token")
        else:
            print("✅ Column reset_token already exists")

        if "reset_token_expiry" not in columns:
            print("Adding reset_token_expiry column to users table...")
            await connection.execute(text("ALTER TABLE users ADD COLUMN reset_token_expiry TIMESTAMP"))
            print("✅ Added reset_token_expiry")
        else:
            print("✅ Column reset_token_expiry already exists")

        if "reset_token_expires_at" not in columns:
            print("Adding reset_token_expires_at column to users table...")
            await connection.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires_at TIMESTAMP"))
            print("✅ Added reset_token_expires_at")
        else:
            print("✅ Column reset_token_expires_at already exists")

        if "reset_token_used" not in columns:
            print("Adding reset_token_used column to users table...")
            await connection.execute(text("ALTER TABLE users ADD COLUMN reset_token_used BOOLEAN DEFAULT FALSE"))
            print("✅ Added reset_token_used")
        else:
            print("✅ Column reset_token_used already exists")

        print("Ensuring index exists for reset_token...")
        await connection.execute(
            text("CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users (reset_token)")
        )
        print("✅ Index idx_users_reset_token ready")


if __name__ == "__main__":
    import asyncio

    asyncio.run(migrate())
