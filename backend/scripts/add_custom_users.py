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

async def add_custom_users():
    password_hasher = PasswordManager()
    
    users_data = [
        {
            "username": "dr_smith",
            "email": "dr_smith@university.edu",
            "full_name": "Dr. Smith",
            "password": "faculty123456",
            "role": "faculty",
            "department": "CSE"
        },
        {
            "username": "dr_johnson",
            "email": "dr_johnson@university.edu",
            "full_name": "Dr. Johnson",
            "password": "faculty123456",
            "role": "faculty",
            "department": "CSE"
        },
        {
            "username": "hod_cs",
            "email": "hod_cs@university.edu",
            "full_name": "Head of Department CS",
            "password": "hod123456",
            "role": "hod",
            "department": "CSE"
        },
        {
            "username": "admin",
            "email": "admin2@university.edu",
            "full_name": "System Administrator",
            "password": "admin123456",
            "role": "admin",
            "department": "Administration"
        }
    ]
    
    await db_manager.initialize()
    session = await db_manager.get_session()
    try:
        for user_data in users_data:
            result = await session.execute(
                select(User).where(User.username == user_data["username"])
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"Updating password for existing user: {user_data['username']}")
                existing_user.hashed_password = password_hasher.hash_password(user_data["password"])
                existing_user.role = user_data["role"]
                existing_user.department = user_data["department"]
            else:
                print(f"Creating new user: {user_data['username']}")
                user = User(
                    id=str(uuid4()),
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    hashed_password=password_hasher.hash_password(user_data["password"]),
                    role=user_data["role"],
                    department=user_data["department"],
                    is_active=True,
                    is_verified=True
                )
                session.add(user)
                
        await session.commit()
        print("Done adding custom users!")
    finally:
        await session.close()
        await db_manager.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(add_custom_users())
