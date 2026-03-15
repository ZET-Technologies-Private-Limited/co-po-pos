"""
Database initialization and seeding script
Initializes all tables and creates sample data for testing
"""
import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config.settings import get_settings
from app.core.database.models import Base
from app.core.database.models import (
    User, Course, CourseOutcome, ProgramOutcome, ProgramSpecificOutcome,
    Exam, ExamQuestion, StudentMarks
)
from app.core.security.password_hashing import PasswordHasher


async def init_database():
    """Initialize database with tables"""
    settings = get_settings()
    
    print("[*] Initializing database...")
    print(f"[*] Database URL: {settings.database_url}")
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("[✓] Database tables created successfully")
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        await seed_database(session)
    
    await engine.dispose()
    print("[✓] Database initialization complete")


async def seed_database(session: AsyncSession):
    """Seed database with sample data"""
    print("\n[*] Seeding database with sample data...")
    
    password_hasher = PasswordHasher()
    
    # Create admin user
    admin_user = User(
        id=str(uuid4()),
        username="admin",
        email="admin@university.edu",
        full_name="Admin User",
        hashed_password=password_hasher.hash_password("admin123456"),
        role="admin",
        department="Administration",
        is_active=True,
        is_verified=True
    )
    
    # Create faculty users
    faculty1 = User(
        id=str(uuid4()),
        username="faculty1",
        email="faculty1@university.edu",
        full_name="Dr. John Smith",
        hashed_password=password_hasher.hash_password("faculty123456"),
        role="faculty",
        department="Computer Science",
        is_active=True,
        is_verified=True
    )
    
    faculty2 = User(
        id=str(uuid4()),
        username="faculty2",
        email="faculty2@university.edu",
        full_name="Dr. Jane Doe",
        hashed_password=password_hasher.hash_password("faculty123456"),
        role="faculty",
        department="Computer Science",
        is_active=True,
        is_verified=True
    )
    
    session.add_all([admin_user, faculty1, faculty2])
    await session.flush()
    
    print("[✓] Created 3 users (1 admin, 2 faculty)")
    
    # Create program outcomes
    po1 = ProgramOutcome(
        id=str(uuid4()),
        code="PO1",
        statement="Demonstrate knowledge of computer science fundamentals",
        description="Students will understand core CS concepts",
        program="B.Tech Computer Science"
    )
    
    po2 = ProgramOutcome(
        id=str(uuid4()),
        code="PO2",
        statement="Design and implement software solutions",
        description="Students will design and develop applications",
        program="B.Tech Computer Science"
    )
    
    po3 = ProgramOutcome(
        id=str(uuid4()),
        code="PO3",
        statement="Analyze and debug software systems",
        description="Students will troubleshoot and optimize code",
        program="B.Tech Computer Science"
    )
    
    session.add_all([po1, po2, po3])
    await session.flush()
    
    print("[✓] Created 3 program outcomes")
    
    # Create program specific outcomes
    pso1 = ProgramSpecificOutcome(
        id=str(uuid4()),
        code="PSO1",
        statement="Apply AI and machine learning techniques",
        description="Students will use AI/ML for problem solving",
        program="B.Tech Computer Science"
    )
    
    pso2 = ProgramSpecificOutcome(
        id=str(uuid4()),
        code="PSO2",
        statement="Develop web and mobile applications",
        description="Students will create modern applications",
        program="B.Tech Computer Science"
    )
    
    session.add_all([pso1, pso2])
    await session.flush()
    
    print("[✓] Created 2 program specific outcomes")
    
    # Create courses
    course1 = Course(
        id=str(uuid4()),
        course_code="CS101",
        course_name="Introduction to Programming",
        description="Fundamentals of programming using Python",
        credits=4,
        semester=1,
        department="Computer Science",
        syllabus="""
        Topics covered:
        1. Variables and data types
        2. Control flow statements
        3. Functions and modules
        4. File handling
        5. Object-oriented programming basics
        """,
        created_by=faculty1.id
    )
    
    course2 = Course(
        id=str(uuid4()),
        course_code="CS201",
        course_name="Data Structures and Algorithms",
        description="Study of efficient data structures and algorithms",
        credits=4,
        semester=2,
        department="Computer Science",
        syllabus="""
        Topics covered:
        1. Arrays and linked lists
        2. Stacks and queues
        3. Trees and graphs
        4. Sorting and searching algorithms
        5. Algorithm analysis and complexity
        """,
        created_by=faculty2.id
    )
    
    session.add_all([course1, course2])
    await session.flush()
    
    print("[✓] Created 2 courses")
    
    # Create course outcomes
    co1 = CourseOutcome(
        id=str(uuid4()),
        course_id=course1.id,
        code="CO1",
        statement="Students will understand programming concepts and write basic programs",
        bloom_level="understand",
        description="Basic programming skills"
    )
    
    co2 = CourseOutcome(
        id=str(uuid4()),
        course_id=course1.id,
        code="CO2",
        statement="Students will apply object-oriented programming principles",
        bloom_level="apply",
        description="OOP implementation"
    )
    
    co3 = CourseOutcome(
        id=str(uuid4()),
        course_id=course1.id,
        code="CO3",
        statement="Students will analyze and design efficient algorithms",
        bloom_level="analyze",
        description="Algorithm design"
    )
    
    co4 = CourseOutcome(
        id=str(uuid4()),
        course_id=course2.id,
        code="CO1",
        statement="Students will understand various data structures",
        bloom_level="understand",
        description="Data structure knowledge"
    )
    
    co5 = CourseOutcome(
        id=str(uuid4()),
        course_id=course2.id,
        code="CO2",
        statement="Students will implement and apply algorithms",
        bloom_level="apply",
        description="Algorithm implementation"
    )
    
    session.add_all([co1, co2, co3, co4, co5])
    await session.flush()
    
    print("[✓] Created 5 course outcomes")
    
    # Create exams
    exam1 = Exam(
        id=str(uuid4()),
        course_id=course1.id,
        exam_name="Mid Term Exam - CS101",
        exam_type="mid_term",
        total_marks=50,
        duration_minutes=120,
        exam_date=datetime.utcnow(),
        created_by=faculty1.id
    )
    
    exam2 = Exam(
        id=str(uuid4()),
        course_id=course1.id,
        exam_name="End Term Exam - CS101",
        exam_type="end_term",
        total_marks=100,
        duration_minutes=180,
        exam_date=datetime.utcnow(),
        created_by=faculty1.id
    )
    
    session.add_all([exam1, exam2])
    await session.flush()
    
    print("[✓] Created 2 exams")
    
    # Create exam questions
    q1 = ExamQuestion(
        id=str(uuid4()),
        exam_id=exam1.id,
        question_number=1,
        question_text="Define variables and data types in Python",
        marks=5,
        question_type="short_answer",
        bloom_level="remember"
    )
    
    q2 = ExamQuestion(
        id=str(uuid4()),
        exam_id=exam1.id,
        question_number=2,
        question_text="Explain the difference between lists and tuples",
        marks=5,
        question_type="short_answer",
        bloom_level="understand"
    )
    
    q3 = ExamQuestion(
        id=str(uuid4()),
        exam_id=exam1.id,
        question_number=3,
        question_text="Write a program to find the Fibonacci series",
        marks=10,
        question_type="long_answer",
        bloom_level="apply"
    )
    
    q4 = ExamQuestion(
        id=str(uuid4()),
        exam_id=exam1.id,
        question_number=4,
        question_text="Analyze the time complexity of the given algorithm",
        marks=10,
        question_type="long_answer",
        bloom_level="analyze"
    )
    
    session.add_all([q1, q2, q3, q4])
    await session.flush()
    
    print("[✓] Created 4 exam questions")
    
    # Create student marks
    students = ["STU001", "STU002", "STU003", "STU004", "STU005"]
    
    for student_id in students:
        # Student 1: 45 (90%)
        marks_q1 = StudentMarks(
            id=str(uuid4()),
            exam_id=exam1.id,
            student_id=student_id,
            question_id=q1.id,
            marks_obtained=4.5
        )
        
        marks_q2 = StudentMarks(
            id=str(uuid4()),
            exam_id=exam1.id,
            student_id=student_id,
            question_id=q2.id,
            marks_obtained=4.5
        )
        
        marks_q3 = StudentMarks(
            id=str(uuid4()),
            exam_id=exam1.id,
            student_id=student_id,
            question_id=q3.id,
            marks_obtained=9
        )
        
        marks_q4 = StudentMarks(
            id=str(uuid4()),
            exam_id=exam1.id,
            student_id=student_id,
            question_id=q4.id,
            marks_obtained=9
        )
        
        session.add_all([marks_q1, marks_q2, marks_q3, marks_q4])
    
    await session.flush()
    
    print("[✓] Created student marks for 5 students")
    
    # Commit all changes
    await session.commit()
    print("\n[✓] Database seeding complete!")
    print("\nSample login credentials:")
    print("  Admin: admin@university.edu / admin123456")
    print("  Faculty: faculty1@university.edu / faculty123456")


async def main():
    """Main function"""
    try:
        await init_database()
        print("\n[✓] Database setup completed successfully!")
        return 0
    except Exception as e:
        print(f"\n[✗] Database setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
