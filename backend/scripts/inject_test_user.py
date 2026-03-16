import asyncio
import sys
import os
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database.connection_manager import db_manager
from app.core.database.models import User
from app.core.security.password_hashing import PasswordManager

async def inject_known_user():
    await db_manager.initialize()
    session = await db_manager.get_session()
    password_hasher = PasswordManager()
    
    try:
        email = "test.faculty@university.edu"
        # Check if exists
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            print("User already exists, updating password.")
            user.hashed_password = password_hasher.hash_password("test123456")
        else:
            print("Creating new test faculty user.")
            new_user = User(
                id=str(uuid4()),
                username="test_faculty",
                email=email,
                full_name="Test Faculty User",
                hashed_password=password_hasher.hash_password("test123456"),
                role="faculty",
                department="Computer Science",
                is_active=True,
                is_verified=True
            )
            session.add(new_user)
            
        await session.commit()
        print("Test user ready:", email)
        
    finally:
        await session.close()
        await db_manager.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(inject_known_user())
