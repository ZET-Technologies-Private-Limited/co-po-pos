import asyncio
from sqlalchemy import select
from app.core.database.connection import AsyncSessionLocal
from app.core.database.models import Course

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Course))
        rows = res.scalars().all()
        print(f"total courses: {len(rows)}")
        for c in rows:
            print("---")
            print("id", c.id, type(c.id).__name__)
            print("code", repr(c.course_code), type(c.course_code).__name__)
            print("name", repr(c.course_name), type(c.course_name).__name__)
            print("credits", repr(c.credits), type(c.credits).__name__)
            print("semester", repr(c.semester), type(c.semester).__name__)
            print("fa_best_n", repr(c.fa_best_n), type(c.fa_best_n).__name__)
            print("fa_total_components", repr(c.fa_total_components), type(c.fa_total_components).__name__)
            print("fa_weight", repr(c.fa_weight), type(c.fa_weight).__name__)
            print("sa_weight", repr(c.sa_weight), type(c.sa_weight).__name__)
            print("created_by", repr(c.created_by), type(c.created_by).__name__)

asyncio.run(main())
