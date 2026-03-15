#!/usr/bin/env python3
"""
Simple database initialization script
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.database.models import Base
from app.core.config.settings import get_settings

async def init_database():
    """Initialize database tables"""
    settings = get_settings()
    print(f"Connecting to database: {settings.database_url}")
    
    engine = create_async_engine(settings.database_url, echo=True)
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_database())