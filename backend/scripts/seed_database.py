import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
import sys
sys.path.insert(0, '/vercel/share/v0-project/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.database.models import Base
from app.core.database.models import (
    User, Course, CourseOutcome, Exam, ExamQuestion, StudentMarks,
    ProgramOutcome, StudentEnrollment, Student, Department, Program
)
from app.core.security.password_hashing import hash_password
from app.core.config.settings import get_settings

settings = get_settings()


async def seed_database():
    engine = create_async_engine(settings.database_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Seeding database with real data...")
        
        dept_id = str(uuid.uuid4())
        dept = Department(
            id=dept_id,
            code="CSE",
            name="Computer Science Engineering",
            description="Department of Computer Science and Engineering"
        )
        session.add(dept)
        
        prog_id = str(uuid.uuid4())
        prog = Program(
            id=prog_id,
            code="B.TECH-CSE",
            name="B.Tech Computer Science Engineering",
            description="4-year B.Tech program",
            department_id=dept_id,
            duration_years=4
        )
        session.add(prog)
        
        admin = User(
            id=str(uuid.uuid4()),
            username="admin",
            email="admin@university.edu",
            password_hash=hash_password("admin123456"),
            full_name="Dr. Admin User",
            role="admin"
        )
        session.add(admin)
        
        faculty1 = User(
            id=str(uuid.uuid4()),
            username="faculty1",
            email="faculty1@university.edu",
            password_hash=hash_password("faculty123456"),
            full_name="Dr. Faculty One",
            role="faculty"
        )
        session.add(faculty1)
        
        faculty2 = User(
            id=str(uuid.uuid4()),
            username="faculty2",
            email="faculty2@university.edu",
            password_hash=hash_password("faculty123456"),
            full_name="Prof. Faculty Two",
            role="faculty"
        )
        session.add(faculty2)
        
        await session.flush()
        
        s1 = Student(
            id=str(uuid.uuid4()),
            roll_number="2021001",
            first_name="Amit",
            last_name="Kumar",
            email="amit.kumar@student.edu",
            program_id=prog_id
        )
        session.add(s1)
        
        s2 = Student(
            id=str(uuid.uuid4()),
            roll_number="2021002",
            first_name="Priya",
            last_name="Singh",
            email="priya.singh@student.edu",
            program_id=prog_id
        )
        session.add(s2)
        
        s3 = Student(
            id=str(uuid.uuid4()),
            roll_number="2021003",
            first_name="Rajesh",
            last_name="Patel",
            email="rajesh.patel@student.edu",
            program_id=prog_id
        )
        session.add(s3)
        
        await session.flush()
        
        course1_id = str(uuid.uuid4())
        course1 = Course(
            id=course1_id,
            course_code="CS201",
            course_name="Data Structures",
            credits=4,
            semester=2,
            description="Comprehensive study of data structures including arrays, linked lists, trees, graphs",
            faculty_id=faculty1.id
        )
        session.add(course1)
        
        course2_id = str(uuid.uuid4())
        course2 = Course(
            id=course2_id,
            course_code="CS301",
            course_name="Algorithms",
            credits=4,
            semester=3,
            description="Analysis and design of algorithms, complexity analysis, sorting, searching, dynamic programming",
            faculty_id=faculty2.id
        )
        session.add(course2)
        
        await session.flush()
        
        co1 = CourseOutcome(
            id=str(uuid.uuid4()),
            course_id=course1_id,
            co_code="CO1",
            co_statement="Understand fundamental data structures and their operations",
            bloom_level="Understand",
            description="Students will understand arrays, lists, stacks, queues"
        )
        session.add(co1)
        
        co2 = CourseOutcome(
            id=str(uuid.uuid4()),
            course_id=course1_id,
            co_code="CO2",
            co_statement="Apply data structures to solve real-world problems",
            bloom_level="Apply",
            description="Students can implement data structures in practical applications"
        )
        session.add(co2)
        
        co3 = CourseOutcome(
            id=str(uuid.uuid4()),
            course_id=course2_id,
            co_code="CO1",
            co_statement="Analyze algorithm complexity and efficiency",
            bloom_level="Analyze",
            description="Students can analyze time and space complexity of algorithms"
        )
        session.add(co3)
        
        co4 = CourseOutcome(
            id=str(uuid.uuid4()),
            course_id=course2_id,
            co_code="CO2",
            co_statement="Design and implement efficient algorithms",
            bloom_level="Create",
            description="Students can design optimal solutions using various algorithm techniques"
        )
        session.add(co4)
        
        await session.flush()
        
        po1 = ProgramOutcome(
            id=str(uuid.uuid4()),
            program_id=prog_id,
            po_code="PO1",
            po_statement="Engineering knowledge and problem solving"
        )
        session.add(po1)
        
        po2 = ProgramOutcome(
            id=str(uuid.uuid4()),
            program_id=prog_id,
            po_code="PO2",
            po_statement="Design and development of solutions"
        )
        session.add(po2)
        
        await session.flush()
        
        exam1_id = str(uuid.uuid4())
        exam1 = Exam(
            id=exam1_id,
            course_id=course1_id,
            exam_name="Mid Term Exam",
            exam_type="mid_term",
            total_marks=50,
            duration_minutes=120
        )
        session.add(exam1)
        
        await session.flush()
        
        q1_id = str(uuid.uuid4())
        q1 = ExamQuestion(
            id=q1_id,
            exam_id=exam1_id,
            question_text="Define a linked list and explain its advantages over arrays",
            marks=5,
            order=1
        )
        session.add(q1)
        
        q2_id = str(uuid.uuid4())
        q2 = ExamQuestion(
            id=q2_id,
            exam_id=exam1_id,
            question_text="Implement a stack using an array and show operations",
            marks=10,
            order=2
        )
        session.add(q2)
        
        q3_id = str(uuid.uuid4())
        q3 = ExamQuestion(
            id=q3_id,
            exam_id=exam1_id,
            question_text="Analyze the complexity of different sorting algorithms",
            marks=15,
            order=3
        )
        session.add(q3)
        
        q4_id = str(uuid.uuid4())
        q4 = ExamQuestion(
            id=q4_id,
            exam_id=exam1_id,
            question_text="Design a binary search tree and explain traversal methods",
            marks=20,
            order=4
        )
        session.add(q4)
        
        await session.flush()
        
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s1.id,
            question_id=q1_id,
            marks_obtained=Decimal("4")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s1.id,
            question_id=q2_id,
            marks_obtained=Decimal("8")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s1.id,
            question_id=q3_id,
            marks_obtained=Decimal("12")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s1.id,
            question_id=q4_id,
            marks_obtained=Decimal("18")
        ))
        
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s2.id,
            question_id=q1_id,
            marks_obtained=Decimal("5")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s2.id,
            question_id=q2_id,
            marks_obtained=Decimal("9")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s2.id,
            question_id=q3_id,
            marks_obtained=Decimal("14")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s2.id,
            question_id=q4_id,
            marks_obtained=Decimal("19")
        ))
        
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s3.id,
            question_id=q1_id,
            marks_obtained=Decimal("3")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s3.id,
            question_id=q2_id,
            marks_obtained=Decimal("6")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s3.id,
            question_id=q3_id,
            marks_obtained=Decimal("10")
        ))
        session.add(StudentMarks(
            id=str(uuid.uuid4()),
            exam_id=exam1_id,
            student_id=s3.id,
            question_id=q4_id,
            marks_obtained=Decimal("15")
        ))
        
        await session.commit()
        print("Database seeded successfully with real data!")
        print(f"- 3 users (admin, 2 faculty)")
        print(f"- 1 department and 1 program")
        print(f"- 3 students")
        print(f"- 2 courses with 4 course outcomes")
        print(f"- 2 program outcomes")
        print(f"- 1 exam with 4 questions")
        print(f"- 12 student marks records")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
