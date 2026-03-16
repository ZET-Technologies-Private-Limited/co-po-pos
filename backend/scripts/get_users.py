import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database.connection_manager import db_manager
from app.core.database.models import User

async def main():
    await db_manager.initialize()
    session = await db_manager.get_session()
    try:
        result = await session.execute(select(User.username, User.email, User.department))
        for row in result.all():
            print(f"User: {row.username}, Email: {row.email}, Dept: {row.department}")
    finally:
        await session.close()
        await db_manager.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
