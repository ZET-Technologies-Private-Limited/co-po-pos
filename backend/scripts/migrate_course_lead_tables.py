"""
Database Migration - Course Lead Dashboard Tables
===============================================

Adds the following tables:
1. approval_queue - For managing course lead approval workflows
2. remedial_actions - For tracking Level 1 CO remedial actions
3. po_targets - For PO attainment target tracking
4. pso_targets - For PSO attainment target tracking

Run this script to add the missing tables to your database.
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.database.models import Base
from app.core.config.settings import get_settings

async def migrate_database():
    """Add Course Lead Dashboard tables to existing database"""
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=True)
    
    try:
        # Create all tables (will only create missing ones)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Course Lead Dashboard tables created successfully!")
        print("Added tables:")
        print("  - approval_queue")
        print("  - remedial_actions") 
        print("  - po_targets")
        print("  - pso_targets")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_database())