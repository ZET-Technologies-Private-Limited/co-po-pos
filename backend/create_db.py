import asyncio
import asyncpg
import sys

async def create_db():
    try:
        # Connect to the default 'postgres' database
        conn = await asyncpg.connect(user='postgres', password='server', host='localhost', port=5432, database='postgres')
        # Check if DB exists
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='co_po_pso_db'")
        if not exists:
            print("Creating database co_po_pso_db...")
            await conn.execute('CREATE DATABASE "co_po_pso_db"')
            print("Database created.")
        else:
            print("Database co_po_pso_db already exists.")
        await conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_db())
