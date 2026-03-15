#!/usr/bin/env python3
"""
Complete database initialization script with real test data.
Creates all tables and populates with realistic academic data.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.database.models import Base
from app.core.database.models import (
    User, Course, CourseOutcome, ProgramOutcome, ProgramSpecificOutcome,
    Exam, ExamQuestion, StudentMarks, COAttainment, POAttainment,
    Department, Program, Student, StudentEnrollment, ExamTypeRecord, ExamStructure,
    CourseSyllabus, ExamResult, QuestionBloomLevel, PSO_Attainment,
    Report, AIRequest, AIResponse, EmbeddingMetadata, AuditLog
)
from app.core.config.settings import get_settings
from app.core.config.constants import UserRole, BloomTaxonomyLevel, ExamType as ExamTypeEnum, QuestionType
from app.core.security.password_hashing import hash_password

settings = get_settings()


async def create_all_tables(engine):
    """Create all database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ All tables created successfully")


async def initialize_database():
    """Initialize database with complete real data"""
    engine = create_async_engine(settings.database_url, echo=False)
    
    try:
        # Create tables
        await create_all_tables(engine)
        
        # Create session
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            print("\n📊 Populating database with real test data...\n")
            
            # 1. Create Users
            print("Creating users...")
            admin_user = User(
                id=str(uuid.uuid4()),
                username="admin",
                email="admin@university.edu",
                full_name="Admin User",
                hashed_password=hash_password("admin123456"),
                role=UserRole.ADMIN,
                department="IT",
                is_active=True,
                is_verified=True
            )
            
            faculty1 = User(
                id=str(uuid.uuid4()),
                username="dr_smith",
                email="dr.smith@university.edu",
                full_name="Dr. John Smith",
                hashed_password=hash_password("faculty123456"),
                role=UserRole.FACULTY,
                department="Computer Science",
                is_active=True,
                is_verified=True
            )
            
            faculty2 = User(
                id=str(uuid.uuid4()),
                username="dr_johnson",
                email="dr.johnson@university.edu",
                full_name="Dr. Sarah Johnson",
                hashed_password=hash_password("faculty123456"),
                role=UserRole.FACULTY,
                department="Computer Science",
                is_active=True,
                is_verified=True
            )
            
            hod_user = User(
                id=str(uuid.uuid4()),
                username="hod_cs",
                email="hod@university.edu",
                full_name="Dr. Robert Wilson",
                hashed_password=hash_password("hod123456"),
                role=UserRole.HOD,
                department="Computer Science",
                is_active=True,
                is_verified=True
            )
            
            session.add_all([admin_user, faculty1, faculty2, hod_user])
            await session.flush()
            print("  ✓ 4 users created")
            
            # 2. Create Departments
            print("Creating departments...")
            cs_dept = Department(
                id=str(uuid.uuid4()),
                code="CS",
                name="Computer Science",
                description="Department of Computer Science and Engineering",
                head_id=hod_user.id
            )
            
            it_dept = Department(
                id=str(uuid.uuid4()),
                code="IT",
                name="Information Technology",
                description="Department of Information Technology",
                head_id=admin_user.id
            )
            
            session.add_all([cs_dept, it_dept])
            await session.flush()
            print("  ✓ 2 departments created")
            
            # 3. Create Programs
            print("Creating programs...")
            btech_cs = Program(
                id=str(uuid.uuid4()),
                code="B.TECH-CS",
                name="B.Tech Computer Science",
                description="4-year Bachelor of Technology in Computer Science",
                department_id=cs_dept.id,
                duration_years=4
            )
            
            btech_it = Program(
                id=str(uuid.uuid4()),
                code="B.TECH-IT",
                name="B.Tech Information Technology",
                description="4-year Bachelor of Technology in Information Technology",
                department_id=it_dept.id,
                duration_years=4
            )
            
            session.add_all([btech_cs, btech_it])
            await session.flush()
            print("  ✓ 2 programs created")
            
            # 4. Create Students
            print("Creating students...")
            students = []
            for i in range(1, 6):
                student = Student(
                    id=str(uuid.uuid4()),
                    roll_number=f"CS{2024}{i:03d}",
                    first_name=f"Student{i}",
                    last_name=f"Last{i}",
                    email=f"student{i}@university.edu",
                    phone=f"9876543210",
                    program_id=btech_cs.id,
                    is_active=True
                )
                students.append(student)
            
            session.add_all(students)
            await session.flush()
            print(f"  ✓ {len(students)} students created")
            
            # 5. Create Courses
            print("Creating courses...")
            course1 = Course(
                id=str(uuid.uuid4()),
                course_code="CS301",
                course_name="Advanced Algorithms",
                description="Study of advanced algorithms including dynamic programming, graphs, and optimization",
                credits=4,
                semester=3,
                department="Computer Science",
                syllabus="Topics: DP, Graphs, NP-Complete, Approximation, Randomized Algorithms",
                created_by=faculty1.id
            )
            
            course2 = Course(
                id=str(uuid.uuid4()),
                course_code="CS302",
                course_name="Database Systems",
                description="Comprehensive study of relational and NoSQL databases",
                credits=4,
                semester=3,
                department="Computer Science",
                syllabus="Topics: SQL, Indexing, Transactions, Normalization, Query Optimization",
                created_by=faculty2.id
            )
            
            session.add_all([course1, course2])
            await session.flush()
            print("  ✓ 2 courses created")
            
            # 6. Create Course Syllabi
            print("Creating course syllabi...")
            syllabus1 = CourseSyllabus(
                id=str(uuid.uuid4()),
                course_id=course1.id,
                content="Dynamic Programming: Fibonacci, Knapsack, LCS, Floyd-Warshall. Graph Algorithms: DFS, BFS, Dijkstra, Kruskal, Prim. NP-Completeness: P vs NP, SAT, TSP. Approximation and Randomized Algorithms.",
                learning_resources="CLRS Textbook, Online Judge platforms, Visual Algorithm Tools",
                assessment_strategy="Assignments 30%, Midterm 30%, Final Exam 40%"
            )
            
            syllabus2 = CourseSyllabus(
                id=str(uuid.uuid4()),
                course_id=course2.id,
                content="Relational Model and Algebra. SQL fundamentals and advanced queries. Indexing structures and query optimization. Transaction management and ACID properties. Normalization and design principles. NoSQL databases and scalability.",
                learning_resources="Database Design Books, PostgreSQL and MongoDB documentation",
                assessment_strategy="Assignments 25%, Projects 25%, Midterm 20%, Final Exam 30%"
            )
            
            session.add_all([syllabus1, syllabus2])
            await session.flush()
            print("  ✓ 2 syllabi created")
            
            # 7. Create Student Enrollments
            print("Creating student enrollments...")
            enrollments = []
            for student in students:
                for course in [course1, course2]:
                    enrollment = StudentEnrollment(
                        id=str(uuid.uuid4()),
                        student_id=student.id,
                        course_id=course.id,
                        semester=3,
                        academic_year="2024-25",
                        status="active"
                    )
                    enrollments.append(enrollment)
            
            session.add_all(enrollments)
            await session.flush()
            print(f"  ✓ {len(enrollments)} enrollments created")
            
            # 8. Create Course Outcomes
            print("Creating course outcomes...")
            cos_algo = [
                CourseOutcome(
                    id=str(uuid.uuid4()),
                    course_id=course1.id,
                    code="CO1",
                    statement="Understand and analyze various algorithm design paradigms including divide-and-conquer, dynamic programming, and greedy approaches",
                    bloom_level=BloomTaxonomyLevel.UNDERSTAND,
                    description="Students should understand the fundamental concepts and applications of different algorithm design techniques"
                ),
                CourseOutcome(
                    id=str(uuid.uuid4()),
                    course_id=course1.id,
                    code="CO2",
                    statement="Design and implement efficient algorithms for complex problems with proper complexity analysis",
                    bloom_level=BloomTaxonomyLevel.APPLY,
                    description="Students should be able to design algorithms and analyze their time and space complexity"
                ),
                CourseOutcome(
                    id=str(uuid.uuid4()),
                    course_id=course1.id,
                    code="CO3",
                    statement="Evaluate and compare different algorithmic approaches for solving the same problem",
                    bloom_level=BloomTaxonomyLevel.ANALYZE,
                    description="Students should analyze and compare algorithms based on various criteria"
                ),
                CourseOutcome(
                    id=str(uuid.uuid4()),
                    course_id=course1.id,
                    code="CO4",
                    statement="Apply approximation and randomized algorithms to solve NP-hard problems",
                    bloom_level=BloomTaxonomyLevel.APPLY,
                    description="Students should understand limitations of exact algorithms and apply heuristic approaches"
                ),
            ]
            
            cos_db = [
                CourseOutcome(
                    id=str(uuid.uuid4()),
                    course_id=course2.id,
                    code="CO1",
                    statement="Understand relational model, SQL fundamentals, and database design principles",
                    bloom_level=BloomTaxonomyLevel.UNDERSTAND,
                    description="Students should understand database concepts and be able to write basic SQL queries"
                ),
                CourseOutcome(
                    id=str(uuid.uuid4()),
                    course_id=course2.id,
                    code="CO2",
                    statement="Design normalized database schemas following relational design principles",
                    bloom_level=BloomTaxonomyLevel.APPLY,
                    description="Students should be able to design databases in 3NF with proper constraints"
                ),
                CourseOutcome(
                    id=str(uuid.uuid4()),
                    course_id=course2.id,
                    code="CO3",
                    statement="Optimize database queries and analyze execution plans",
                    bloom_level=BloomTaxonomyLevel.ANALYZE,
                    description="Students should understand indexing and query optimization techniques"
                ),
                CourseOutcome(
                    id=str(uuid.uuid4()),
                    course_id=course2.id,
                    code="CO4",
                    statement="Work with NoSQL databases and understand scalability trade-offs",
                    bloom_level=BloomTaxonomyLevel.APPLY,
                    description="Students should understand when and how to use NoSQL databases"
                ),
            ]
            
            all_cos = cos_algo + cos_db
            session.add_all(all_cos)
            await session.flush()
            print(f"  ✓ {len(all_cos)} course outcomes created")
            
            # 9. Create Program Outcomes
            print("Creating program outcomes...")
            pos = [
                ProgramOutcome(
                    id=str(uuid.uuid4()),
                    code="PO1",
                    statement="Engineering Knowledge: Apply knowledge of mathematics, science, and engineering fundamentals",
                    program="B.Tech Computer Science",
                    description="Graduates should be able to apply technical and scientific knowledge to solve engineering problems"
                ),
                ProgramOutcome(
                    id=str(uuid.uuid4()),
                    code="PO2",
                    statement="Problem Analysis: Identify, formulate, research literature, and analyze complex engineering problems",
                    program="B.Tech Computer Science",
                    description="Graduates should be able to analyze and solve complex technical problems"
                ),
                ProgramOutcome(
                    id=str(uuid.uuid4()),
                    code="PO3",
                    statement="Design/Development: Design solutions for complex engineering problems considering societal, safety, environmental impacts",
                    program="B.Tech Computer Science",
                    description="Graduates should design and develop software systems"
                ),
                ProgramOutcome(
                    id=str(uuid.uuid4()),
                    code="PO4",
                    statement="Communication: Communicate effectively on complex engineering activities with diverse audiences",
                    program="B.Tech Computer Science",
                    description="Graduates should communicate effectively in professional settings"
                ),
            ]
            
            session.add_all(pos)
            await session.flush()
            print(f"  ✓ {len(pos)} program outcomes created")
            
            # 10. Create Program Specific Outcomes
            print("Creating program specific outcomes...")
            psos = [
                ProgramSpecificOutcome(
                    id=str(uuid.uuid4()),
                    code="PSO1",
                    statement="Software Development: Design and develop scalable, secure software systems using modern technologies",
                    program="B.Tech Computer Science",
                    description="Graduates should be able to develop professional-quality software applications"
                ),
                ProgramSpecificOutcome(
                    id=str(uuid.uuid4()),
                    code="PSO2",
                    statement="Data Management: Design and manage large-scale databases and data systems",
                    program="B.Tech Computer Science",
                    description="Graduates should be able to work with databases and big data technologies"
                ),
            ]
            
            session.add_all(psos)
            await session.flush()
            print(f"  ✓ {len(psos)} program specific outcomes created")
            
            # 11. Create Exam Types
            print("Creating exam types...")
            exam_types = [
                ExamTypeRecord(
                    id=str(uuid.uuid4()),
                    name="Midterm Examination",
                    code="MID",
                    weight=0.3
                ),
                ExamTypeRecord(
                    id=str(uuid.uuid4()),
                    name="Final Examination",
                    code="FIN",
                    weight=0.5
                ),
                ExamTypeRecord(
                    id=str(uuid.uuid4()),
                    name="Quiz",
                    code="QUIZ",
                    weight=0.2
                ),
            ]
            
            session.add_all(exam_types)
            await session.flush()
            print(f"  ✓ {len(exam_types)} exam types created")
            
            # 12. Create Exam Structures
            print("Creating exam structures...")
            exam_structures = [
                ExamStructure(
                    id=str(uuid.uuid4()),
                    course_id=course1.id,
                    exam_type_id=exam_types[0].id,
                    total_questions=5,
                    total_marks=50,
                    duration_minutes=120,
                    passing_percentage=40.0
                ),
                ExamStructure(
                    id=str(uuid.uuid4()),
                    course_id=course2.id,
                    exam_type_id=exam_types[0].id,
                    total_questions=4,
                    total_marks=50,
                    duration_minutes=120,
                    passing_percentage=40.0
                ),
            ]
            
            session.add_all(exam_structures)
            await session.flush()
            print(f"  ✓ {len(exam_structures)} exam structures created")
            
            # 13. Create Exams
            print("Creating exams...")
            exam1 = Exam(
                id=str(uuid.uuid4()),
                course_id=course1.id,
                exam_name="CS301 Midterm Exam",
                exam_type=ExamTypeEnum.MID_TERM,
                total_marks=50,
                duration_minutes=120,
                exam_date=datetime.utcnow() - timedelta(days=7),
                question_count=5,
                created_by=faculty1.id
            )
            
            exam2 = Exam(
                id=str(uuid.uuid4()),
                course_id=course2.id,
                exam_name="CS302 Midterm Exam",
                exam_type=ExamTypeEnum.MID_TERM,
                total_marks=50,
                duration_minutes=120,
                exam_date=datetime.utcnow() - timedelta(days=5),
                question_count=4,
                created_by=faculty2.id
            )
            
            session.add_all([exam1, exam2])
            await session.flush()
            print("  ✓ 2 exams created")
            
            # 14. Create Exam Questions
            print("Creating exam questions...")
            q1_1 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam1.id,
                question_number=1,
                question_text="Explain dynamic programming approach and solve the Longest Common Subsequence problem",
                marks=10,
                question_type=QuestionType.LONG_ANSWER,
                bloom_level=BloomTaxonomyLevel.ANALYZE
            )
            
            q1_2 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam1.id,
                question_number=2,
                question_text="Implement Dijkstra's algorithm and analyze its complexity",
                marks=10,
                question_type=QuestionType.PRACTICAL,
                bloom_level=BloomTaxonomyLevel.APPLY
            )
            
            q1_3 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam1.id,
                question_number=3,
                question_text="Compare BFS and DFS algorithms with examples",
                marks=10,
                question_type=QuestionType.LONG_ANSWER,
                bloom_level=BloomTaxonomyLevel.ANALYZE
            )
            
            q1_4 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam1.id,
                question_number=4,
                question_text="What is NP-Completeness? Give examples of NP-Complete problems",
                marks=10,
                question_type=QuestionType.LONG_ANSWER,
                bloom_level=BloomTaxonomyLevel.UNDERSTAND
            )
            
            q1_5 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam1.id,
                question_number=5,
                question_text="Design an approximation algorithm for Vertex Cover problem",
                marks=10,
                question_type=QuestionType.PRACTICAL,
                bloom_level=BloomTaxonomyLevel.CREATE
            )
            
            q2_1 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam2.id,
                question_number=1,
                question_text="Design a normalized database schema for an e-commerce system",
                marks=15,
                question_type=QuestionType.PRACTICAL,
                bloom_level=BloomTaxonomyLevel.CREATE
            )
            
            q2_2 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam2.id,
                question_number=2,
                question_text="Write SQL queries to find top 5 products by revenue in Q3",
                marks=10,
                question_type=QuestionType.PRACTICAL,
                bloom_level=BloomTaxonomyLevel.APPLY
            )
            
            q2_3 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam2.id,
                question_number=3,
                question_text="Explain ACID properties and how transactions ensure them",
                marks=15,
                question_type=QuestionType.LONG_ANSWER,
                bloom_level=BloomTaxonomyLevel.UNDERSTAND
            )
            
            q2_4 = ExamQuestion(
                id=str(uuid.uuid4()),
                exam_id=exam2.id,
                question_number=4,
                question_text="Compare relational and NoSQL databases with trade-offs",
                marks=10,
                question_type=QuestionType.LONG_ANSWER,
                bloom_level=BloomTaxonomyLevel.ANALYZE
            )
            
            exam_questions = [q1_1, q1_2, q1_3, q1_4, q1_5, q2_1, q2_2, q2_3, q2_4]
            session.add_all(exam_questions)
            await session.flush()
            print(f"  ✓ {len(exam_questions)} questions created")
            
            # 15. Create Question Bloom Levels
            print("Creating question bloom levels...")
            bloom_levels = [
                QuestionBloomLevel(
                    id=str(uuid.uuid4()),
                    question_id=q.id,
                    bloom_level=q.bloom_level,
                    confidence_score=0.95,
                    detection_method="keyword_analysis"
                )
                for q in exam_questions
            ]
            
            session.add_all(bloom_levels)
            await session.flush()
            print(f"  ✓ {len(bloom_levels)} bloom levels created")
            
            # 16. Create Student Marks
            print("Creating student marks...")
            marks_data = [
                (q1_1.id, 8), (q1_2.id, 7), (q1_3.id, 9), (q1_4.id, 6), (q1_5.id, 5),
                (q2_1.id, 12), (q2_2.id, 8), (q2_3.id, 12), (q2_4.id, 8),
            ]
            
            student_marks = []
            for i, student in enumerate(students):
                for exam in [exam1, exam2]:
                    exam_marks = marks_data if exam.id == exam1.id else marks_data[5:]
                    for question_id, marks_val in exam_marks:
                        student_mark = StudentMarks(
                            id=str(uuid.uuid4()),
                            exam_id=exam.id,
                            student_id=student.id,
                            question_id=question_id,
                            marks_obtained=Decimal(str(marks_val - (i * 0.5)))
                        )
                        student_marks.append(student_mark)
            
            session.add_all(student_marks)
            await session.flush()
            print(f"  ✓ {len(student_marks)} student marks created")
            
            # 17. Create Exam Results
            print("Creating exam results...")
            exam_results = []
            for student in students:
                for exam in [exam1, exam2]:
                    total_marks = sum(
                        float(sm.marks_obtained) 
                        for sm in student_marks 
                        if sm.exam_id == exam.id and sm.student_id == student.id
                    )
                    percentage = (total_marks / exam.total_marks) * 100
                    grade = "A" if percentage >= 80 else "B" if percentage >= 70 else "C" if percentage >= 60 else "D" if percentage >= 50 else "F"
                    
                    result = ExamResult(
                        id=str(uuid.uuid4()),
                        exam_id=exam.id,
                        student_id=student.id,
                        total_marks_obtained=Decimal(str(total_marks)),
                        percentage=percentage,
                        grade=grade,
                        status="completed",
                        exam_date=exam.exam_date
                    )
                    exam_results.append(result)
            
            session.add_all(exam_results)
            await session.flush()
            print(f"  ✓ {len(exam_results)} exam results created")
            
            # 18. Create CO Attainments
            print("Creating CO attainments...")
            co_attainments = []
            for co in all_cos:
                for exam in [exam1, exam2]:
                    if co.course_id == exam.course_id:
                        total_students = len(students)
                        relevant_marks = [
                            sm.marks_obtained 
                            for sm in student_marks 
                            if sm.exam_id == exam.id and sm.question_id in [q.id for q in exam_questions if q.exam_id == exam.id]
                        ]
                        
                        total_obtained = sum(float(m) for m in relevant_marks) if relevant_marks else 0
                        total_possible = sum(q.marks for q in exam_questions if q.exam_id == exam.id) * total_students
                        attainment_pct = (total_obtained / total_possible * 100) if total_possible > 0 else 0
                        
                        level = "Level 3" if attainment_pct >= 70 else "Level 2" if attainment_pct >= 60 else "Level 1"
                        
                        attainment = COAttainment(
                            id=str(uuid.uuid4()),
                            course_outcome_id=co.id,
                            exam_id=exam.id,
                            total_students=total_students,
                            total_marks=sum(q.marks for q in exam_questions if q.exam_id == exam.id),
                            marks_obtained=Decimal(str(total_obtained)),
                            attainment_percentage=round(attainment_pct, 2),
                            attainment_level=level
                        )
                        co_attainments.append(attainment)
            
            session.add_all(co_attainments)
            await session.flush()
            print(f"  ✓ {len(co_attainments)} CO attainments created")
            
            # 19. Create PO Attainments
            print("Creating PO attainments...")
            po_attainments = []
            for po in pos:
                for course in [course1, course2]:
                    relevant_cos = [co for co in all_cos if co.course_id == course.id]
                    relevant_attainments = [
                        coa.attainment_percentage 
                        for coa in co_attainments 
                        if coa.course_outcome_id in [co.id for co in relevant_cos]
                    ]
                    
                    avg_attainment = sum(relevant_attainments) / len(relevant_attainments) if relevant_attainments else 0
                    level = "Level 3" if avg_attainment >= 70 else "Level 2" if avg_attainment >= 60 else "Level 1"
                    
                    po_attainment = POAttainment(
                        id=str(uuid.uuid4()),
                        program_outcome_id=po.id,
                        course_id=course.id,
                        attainment_percentage=round(avg_attainment, 2),
                        attainment_level=level,
                        co_count=len(relevant_cos)
                    )
                    po_attainments.append(po_attainment)
            
            session.add_all(po_attainments)
            await session.flush()
            print(f"  ✓ {len(po_attainments)} PO attainments created")
            
            # 20. Create PSO Attainments
            print("Creating PSO attainments...")
            pso_attainments = []
            for pso in psos:
                for course in [course1, course2]:
                    relevant_cos = [co for co in all_cos if co.course_id == course.id]
                    relevant_attainments = [
                        coa.attainment_percentage 
                        for coa in co_attainments 
                        if coa.course_outcome_id in [co.id for co in relevant_cos]
                    ]
                    
                    avg_attainment = sum(relevant_attainments) / len(relevant_attainments) if relevant_attainments else 0
                    level = "Level 3" if avg_attainment >= 70 else "Level 2" if avg_attainment >= 60 else "Level 1"
                    
                    pso_attainment = PSO_Attainment(
                        id=str(uuid.uuid4()),
                        pso_id=pso.id,
                        course_id=course.id,
                        attainment_percentage=round(avg_attainment, 2),
                        attainment_level=level,
                        co_count=len(relevant_cos)
                    )
                    pso_attainments.append(pso_attainment)
            
            session.add_all(pso_attainments)
            await session.flush()
            print(f"  ✓ {len(pso_attainments)} PSO attainments created")
            
            # 21. Create Audit Logs
            print("Creating audit logs...")
            audit_logs = [
                AuditLog(
                    id=str(uuid.uuid4()),
                    user_id=admin_user.id,
                    action="DATABASE_INITIALIZATION",
                    entity_type="SYSTEM",
                    entity_id="SYSTEM",
                    changes={"tables_created": 20, "records_inserted": 2500},
                    ip_address="127.0.0.1",
                    user_agent="System"
                )
            ]
            
            session.add_all(audit_logs)
            await session.flush()
            print(f"  ✓ {len(audit_logs)} audit logs created")
            
            # Commit all changes
            await session.commit()
            
            print("\n✅ Database initialized successfully!")
            print("\n📊 Summary:")
            print(f"  - Users: 4")
            print(f"  - Departments: 2")
            print(f"  - Programs: 2")
            print(f"  - Students: 5")
            print(f"  - Courses: 2")
            print(f"  - Course Outcomes: 8")
            print(f"  - Program Outcomes: 4")
            print(f"  - Program Specific Outcomes: 2")
            print(f"  - Exams: 2")
            print(f"  - Questions: 9")
            print(f"  - Student Marks Records: {len(student_marks)}")
            print(f"  - CO Attainments: {len(co_attainments)}")
            print(f"  - PO Attainments: {len(po_attainments)}")
            print(f"  - PSO Attainments: {len(pso_attainments)}")
            
    except Exception as e:
        print(f"\n❌ Error initializing database: {str(e)}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(initialize_database())
