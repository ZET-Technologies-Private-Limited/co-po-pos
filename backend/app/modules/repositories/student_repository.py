"""
Student and enrollment data access repository
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from app.core.database.models import Student, StudentEnrollment, Program
from app.modules.repositories.base_repository import BaseRepository


class StudentRepository(BaseRepository):
    """Repository for student data operations"""
    
    async def get_by_roll_number(self, session: AsyncSession, roll_number: str) -> Optional[Student]:
        """Get student by roll number"""
        query = select(Student).where(Student.roll_number == roll_number)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[Student]:
        """Get student by email"""
        query = select(Student).where(Student.email == email)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_program(self, session: AsyncSession, program_id: str) -> List[Student]:
        """Get all students in a program"""
        query = select(Student).where(
            and_(Student.program_id == program_id, Student.is_active == True)
        )
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_active_students(self, session: AsyncSession) -> List[Student]:
        """Get all active students"""
        query = select(Student).where(Student.is_active == True)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def create(self, session: AsyncSession, **kwargs) -> Student:
        """Create a new student"""
        student = Student(**kwargs)
        session.add(student)
        await session.flush()
        return student
    
    async def update(self, session: AsyncSession, student_id: str, **kwargs) -> Optional[Student]:
        """Update student information"""
        student = await self.get_by_id(session, student_id, Student)
        if student:
            for key, value in kwargs.items():
                setattr(student, key, value)
            await session.flush()
        return student


class StudentEnrollmentRepository(BaseRepository):
    """Repository for student enrollments"""
    
    async def get_student_courses(self, session: AsyncSession, student_id: str) -> List[StudentEnrollment]:
        """Get all courses a student is enrolled in"""
        query = select(StudentEnrollment).where(
            StudentEnrollment.student_id == student_id
        )
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_course_students(self, session: AsyncSession, course_id: str) -> List[StudentEnrollment]:
        """Get all students enrolled in a course"""
        query = select(StudentEnrollment).where(
            StudentEnrollment.course_id == course_id
        )
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_by_student_course(self, session: AsyncSession, student_id: str, course_id: str) -> Optional[StudentEnrollment]:
        """Get enrollment record for specific student and course"""
        query = select(StudentEnrollment).where(
            and_(
                StudentEnrollment.student_id == student_id,
                StudentEnrollment.course_id == course_id
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def create(self, session: AsyncSession, **kwargs) -> StudentEnrollment:
        """Create a new enrollment"""
        enrollment = StudentEnrollment(**kwargs)
        session.add(enrollment)
        await session.flush()
        return enrollment
    
    async def get_semester_enrollments(self, session: AsyncSession, semester: int, academic_year: str) -> List[StudentEnrollment]:
        """Get all enrollments for a specific semester and year"""
        query = select(StudentEnrollment).where(
            and_(
                StudentEnrollment.semester == semester,
                StudentEnrollment.academic_year == academic_year
            )
        )
        result = await session.execute(query)
        return result.scalars().all()
