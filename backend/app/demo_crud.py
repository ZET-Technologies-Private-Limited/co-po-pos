"""
CRUD Operations Demo Script
Demonstrates the enhanced CRUD functionality using existing services
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.courses.services.course_service import CourseService
from app.modules.user.services.user_service import UserService
from app.modules.attainment_engine.services.attainment_service import AttainmentService
from app.core.database.connection_manager import get_session
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("crud_demo")


async def demo_course_crud():
    """Demonstrate Course CRUD operations"""
    async with get_session() as session:
        course_service = CourseService(session)
        
        # Create course
        course = await course_service.create_course(
            course_code="CS101",
            course_name="Introduction to Programming",
            credits=4,
            semester=1,
            description="Basic programming concepts",
            faculty_id="faculty-123",
            department="Computer Science"
        )
        logger.info(f"Created course: {course.id}")
        
        # Read course
        retrieved_course = await course_service.get_course(course.id)
        logger.info(f"Retrieved course: {retrieved_course.course_name}")
        
        # Update course
        updated_course = await course_service.update_course(
            course.id,
            description="Updated: Basic programming concepts and problem solving"
        )
        logger.info(f"Updated course description: {updated_course.description}")
        
        # List courses with filters
        courses = await course_service.list_courses(
            semester=1,
            department="Computer Science"
        )
        logger.info(f"Found {len(courses)} courses in semester 1")
        
        # Search courses
        search_results = await course_service.search_courses("Programming")
        logger.info(f"Search found {len(search_results)} courses")
        
        # Count courses
        count = await course_service.count_courses(department="Computer Science")
        logger.info(f"Total courses in CS department: {count}")
        
        # Create exam for the course
        exam = await course_service.create_exam(
            course_id=course.id,
            exam_name="Midterm Exam",
            exam_type="mid_term",
            total_marks=100,
            duration_minutes=120
        )
        logger.info(f"Created exam: {exam.id}")
        
        # Create course outcome
        co = await course_service.create_course_outcome(
            course_id=course.id,
            code="CO1",
            statement="Understand basic programming concepts",
            bloom_level="understand"
        )
        logger.info(f"Created course outcome: {co.id}")
        
        return course, exam, co


async def demo_user_crud():
    """Demonstrate User CRUD operations"""
    async with get_session() as session:
        user_service = UserService()
        
        # Create user
        user = await user_service.create_user(
            session=session,
            username="john_doe",
            email="john.doe@university.edu",
            password="secure123",
            full_name="John Doe",
            role="faculty",
            department="Computer Science"
        )
        logger.info(f"Created user: {user.id}")
        
        # Read user
        retrieved_user = await user_service.get_user_by_email(session, "john.doe@university.edu")
        logger.info(f"Retrieved user: {retrieved_user.full_name}")
        
        # Update user
        updated_user = await user_service.update_user(
            session,
            user.id,
            department="Information Technology"
        )
        logger.info(f"Updated user department: {updated_user.department}")
        
        # List users with filters
        users = await user_service.list_users(
            session,
            role="faculty",
            is_active=True
        )
        logger.info(f"Found {len(users)} active faculty users")
        
        # Search users
        search_results = await user_service.search_users(session, "john")
        logger.info(f"Search found {len(search_results)} users")
        
        # Count users
        count = await user_service.count_users(session, role="faculty")
        logger.info(f"Total faculty users: {count}")
        
        # Create student
        student = await user_service.create_student(
            session=session,
            roll_number="CS2024001",
            first_name="Alice",
            last_name="Smith",
            email="alice.smith@student.edu",
            program_id="btech-cs"
        )
        logger.info(f"Created student: {student.id}")
        
        return user, student


async def demo_attainment_crud():
    """Demonstrate Attainment CRUD operations"""
    async with get_session() as session:
        attainment_service = AttainmentService(session)
        
        # Create CO attainment
        co_attainment = await attainment_service.create_co_attainment(
            course_outcome_id="co-123",
            exam_id="exam-123",
            total_students=30,
            total_marks=100,
            marks_obtained=2250.0,
            attainment_percentage=75.0,
            attainment_level="Level 3"
        )
        logger.info(f"Created CO attainment: {co_attainment.id}")
        
        # Read CO attainment
        retrieved_attainment = await attainment_service.get_co_attainment(co_attainment.id)
        logger.info(f"Retrieved CO attainment: {retrieved_attainment.attainment_percentage}%")
        
        # Update CO attainment
        updated_attainment = await attainment_service.update_co_attainment(
            co_attainment.id,
            attainment_percentage=80.0,
            attainment_level="Level 3"
        )
        logger.info(f"Updated CO attainment: {updated_attainment.attainment_percentage}%")
        
        # Create PO attainment
        po_attainment = await attainment_service.create_po_attainment(
            program_outcome_id="po-123",
            course_id="course-123",
            attainment_percentage=72.5,
            attainment_level="Level 3",
            co_count=5
        )
        logger.info(f"Created PO attainment: {po_attainment.id}")
        
        # Generate report
        report = await attainment_service.generate_report(
            course_id="course-123",
            report_type="co_attainment",
            user_id="user-123"
        )
        logger.info(f"Generated report: {report.id}")
        
        # List reports
        reports = await attainment_service.list_reports(course_id="course-123")
        logger.info(f"Found {len(reports)} reports for course")
        
        return co_attainment, po_attainment, report


async def demo_comprehensive_crud():
    """Demonstrate comprehensive CRUD operations across all services"""
    logger.info("=== Starting Comprehensive CRUD Demo ===")
    
    try:
        # Demo course operations
        logger.info("--- Course CRUD Operations ---")
        course, exam, co = await demo_course_crud()
        
        # Demo user operations
        logger.info("--- User CRUD Operations ---")
        user, student = await demo_user_crud()
        
        # Demo attainment operations
        logger.info("--- Attainment CRUD Operations ---")
        co_attainment, po_attainment, report = await demo_attainment_crud()
        
        logger.info("=== CRUD Demo Completed Successfully ===")
        
        return {
            "course": course,
            "exam": exam,
            "course_outcome": co,
            "user": user,
            "student": student,
            "co_attainment": co_attainment,
            "po_attainment": po_attainment,
            "report": report
        }
        
    except Exception as e:
        logger.error(f"CRUD Demo failed: {str(e)}")
        raise


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo_comprehensive_crud())