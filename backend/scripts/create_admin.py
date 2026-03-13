#!/usr/bin/env python3
"""Create or promote an admin user for local setup and testing."""

import argparse
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select  # noqa: E402
from core.database import AsyncSessionLocal  # noqa: E402
from core.security import hash_password  # noqa: E402
from models.user import User  # noqa: E402


async def create_or_promote_admin(email: str, password: str | None, name: str | None) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            if not password:
                raise ValueError("Password is required when creating a new admin user")
            user = User(
                email=email,
                name=name,
                password_hash=hash_password(password),
                role="admin",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Created admin user {email} with id={user.id}")
            return

        user.role = "admin"
        if password:
            user.password_hash = hash_password(password)
        if name:
            user.name = name
        await db.commit()
        await db.refresh(user)
        print(f"Promoted existing user {email} to admin (id={user.id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or promote an admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", help="Password for new admin or password reset")
    parser.add_argument("--name", help="Optional display name")
    args = parser.parse_args()
    asyncio.run(create_or_promote_admin(args.email, args.password, args.name))
