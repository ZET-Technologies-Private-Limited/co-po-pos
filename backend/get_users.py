import asyncio
import sys
sys.path.insert(0, '.')
from sqlalchemy import text
from app.core.database.connection_manager import db_manager

async def print_users():
    async with db_manager.get_session() as session:
        result = await session.execute(text("SELECT username, email, full_name, role, department FROM users"))
        users = result.fetchall()
        for u in users:
            print(u)
            
if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(print_users())
