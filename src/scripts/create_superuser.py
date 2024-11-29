#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent)
sys.path.append(src_path)

from db.session import AsyncSessionLocal
from db.models import User
from api.v1.auth import get_password_hash

async def create_superuser():
    """Create a superuser account if it doesn't exist."""
    async with AsyncSessionLocal() as session:
        # Check if superuser already exists
        result = await session.execute(
            "SELECT id FROM users WHERE is_superuser = true LIMIT 1"
        )
        if result.scalar_one_or_none():
            print("Superuser already exists")
            return

        # Get credentials from environment or use defaults
        username = os.getenv("SUPERUSER_USERNAME", "admin")
        email = os.getenv("SUPERUSER_EMAIL", "admin@example.com")
        password = os.getenv("SUPERUSER_PASSWORD", "admin")

        if not all([username, email, password]):
            print("Missing required environment variables for superuser creation")
            return

        # Create superuser
        superuser = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            is_superuser=True,
            is_active=True
        )

        try:
            session.add(superuser)
            await session.commit()
            print(f"Superuser '{username}' created successfully")
        except Exception as e:
            await session.rollback()
            print(f"Failed to create superuser: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(create_superuser())
