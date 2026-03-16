import asyncio
import sys
sys.path.insert(0, ".")
from app.core.config.settings import get_settings
from app.core.security.password_hashing import hash_password
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, class_=AsyncSession)
    async with Session() as s:
        hashed = hash_password("Test1234!")
        await s.execute(
            text("UPDATE users SET hashed_password = :pw WHERE email = :email"),
            {"pw": hashed, "email": "sadwik1409@gmail.com"}
        )
        await s.commit()
        print("Password reset done for sadwik1409@gmail.com → Test1234!")
    await engine.dispose()

asyncio.run(main())
