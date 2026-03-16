"""Diagnostic: Check if ExamQuestion and StudentMarks rows exist for test courses."""
import asyncio, sys, os
sys.path.insert(0, r'F:\co\CO-PO-POS\backend')
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://postgres:kranthi@localhost:5432/co_po_pso_db')
os.environ.setdefault('SECRET_KEY','7f9c1a4d2b8e6f0c3a5d9e1b4c7f2a6d8e3b0c5f1a9d7e4c6b2f8a3d0e5c1b9f6a2d4e7c8f1b3a0d5e6c9f2a7b4d8c1')
os.environ.setdefault('ENVIRONMENT','development')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text, func

DB_URL = os.environ['DATABASE_URL']

async def main():
    engine = create_async_engine(DB_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Count courses, exams, questions, marks
        for tbl in ('courses', 'exams', 'exam_questions', 'student_marks', 'course_outcomes', 'enrollments'):
            try:
                r = await session.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                print(f"  {tbl}: {r.scalar()}")
            except Exception as e:
                print(f"  {tbl}: ERROR {e}")

        # 2. Show first 3 courses with their exam/question/marks counts
        print("\n--- Per-course breakdown ---")
        courses_r = await session.execute(text("SELECT id, course_code FROM courses LIMIT 5"))
        for cid, code in courses_r.all():
            exams_r = await session.execute(text(f"SELECT id, exam_name, exam_type FROM exams WHERE course_id='{cid}'"))
            exams = exams_r.all()
            print(f"\nCourse {code} (id={cid}):")
            for eid, ename, etype in exams:
                q_count = (await session.execute(text(f"SELECT COUNT(*) FROM exam_questions WHERE exam_id='{eid}'"))).scalar()
                m_count = (await session.execute(text(f"SELECT COUNT(*) FROM student_marks WHERE exam_id='{eid}'"))).scalar()
                # Check question_co_mapping
                qmap_count = (await session.execute(text(f"""
                    SELECT COUNT(*) FROM question_co_mapping qcm
                    JOIN exam_questions eq ON qcm.question_id=eq.id
                    WHERE eq.exam_id='{eid}'
                """))).scalar()
                print(f"  Exam '{ename}' ({etype}): questions={q_count}, marks={m_count}, q_co_mappings={qmap_count}")

        # 3. Show one exam's questions
        print("\n--- Sample exam questions ---")
        sample_exam = await session.execute(text("SELECT id, exam_name FROM exams LIMIT 1"))
        for eid, ename in sample_exam.all():
            qs = await session.execute(text(f"SELECT id, question_number, question_text, marks FROM exam_questions WHERE exam_id='{eid}' LIMIT 5"))
            print(f"Exam: {ename} (id={eid})")
            rows = qs.all()
            if rows:
                for qid, qnum, qtxt, qmarks in rows:
                    print(f"  Q{qnum}: marks={qmarks} text={str(qtxt)[:60]!r}")
                    # check mappings
                    mc = (await session.execute(text(f"SELECT COUNT(*) FROM question_co_mapping WHERE question_id='{qid}'"))).scalar()
                    print(f"    -> CO mappings: {mc}")
            else:
                print("  (no questions)")

        # 4. Check student marks sample
        print("\n--- Sample student marks ---")
        sm = await session.execute(text("SELECT student_id, question_id, marks_obtained, exam_id FROM student_marks LIMIT 5"))
        for sid, qid, mks, eid in sm.all():
            print(f"  student={sid[:8]}, q={qid[:8]}, marks={mks}, exam={eid[:8]}")

    await engine.dispose()

asyncio.run(main())
