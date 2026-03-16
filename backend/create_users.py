#!/usr/bin/env python3
"""
Quick user creation script
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.database.models import User, Base
from app.core.config.constants import UserRole
from app.core.security.password_hashing import hash_password
from app.core.config.settings import get_settings

async def create_users():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if users already exist
        from sqlalchemy import select
        existing_users = await session.execute(select(User).where(User.username.in_(["admin", "dr_smith", "hod_cs", "dr_johnson"])))
        if existing_users.scalar_one_or_none():
            print("Users already exist!")
            return
        
        # Create users with demo credentials
        users = [
            User(
                username="admin",
                email="admin@university.edu",
                hashed_password=hash_password("admin123456"),
                full_name="System Administrator",
                role=UserRole.ADMIN
            ),
            User(
                username="dr_smith", 
                email="dr.smith@university.edu",
                hashed_password=hash_password("faculty123456"),
                full_name="Dr. Smith",
                role=UserRole.FACULTY
            ),
            User(
                username="hod_cs",
                email="hod.cs@university.edu", 
                hashed_password=hash_password("hod123456"),
                full_name="HOD Computer Science",
                role=UserRole.HOD
            ),
            User(
                username="dr_johnson",
                email="dr.johnson@university.edu",
                hashed_password=hash_password("faculty123456"), 
                full_name="Dr. Johnson",
                role=UserRole.COURSE_LEAD
            )
        ]
        
        for user in users:
            session.add(user)
        
        await session.commit()
        print("✅ Users created successfully!")
        print("Demo Credentials:")
        print("- Admin: admin / admin123456")
        print("- Faculty: dr_smith / faculty123456") 
        print("- HOD: hod_cs / hod123456")
        print("- Course Lead: dr_johnson / faculty123456")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_users())
