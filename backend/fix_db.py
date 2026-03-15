import asyncio
import asyncpg
import sys

async def fix_enum():
    conn = await asyncpg.connect(user='postgres', password='server', host='localhost', port=5432, database='co_po_pso_db')
    try:
        await conn.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'course_lead'")
        print("Added course_lead")
    except Exception as e: print(e)
    try:
        await conn.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'accreditation_officer'")
        print("Added accreditation_officer")
    except Exception as e: print(e)
    try:
        await conn.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'viewer'")
        print("Added viewer")
    except Exception as e: print(e)
    
    await conn.close()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_enum())
