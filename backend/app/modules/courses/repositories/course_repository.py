"""
Course repository with CRUD operations and queries
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from app.core.database.models import Course, CourseOutcome, Exam, ExamQuestion
from app.core.logging.system_logger import SystemLogger
import uuid

logger = SystemLogger("course_repository")


class CourseRepository:
    """Repository for course data access operations"""
    
    @staticmethod
    async def create_course(
        session: AsyncSession,
        course_code: str,
        course_name: str,
        credits: int = 3,
        semester: int = None,
        department_id: str = None,
        created_by: str = None,
        syllabus: str = None,
        description: str = None
    ) -> Course:
        """Create a new course"""
        try:
            course = Course(
                id=str(uuid.uuid4()),
                course_code=course_code,
                course_name=course_name,
                credits=credits,
                semester=semester,
                department=department_id,
                syllabus=syllabus,
                description=description,
                created_by=created_by
            )
            
            session.add(course)
            await session.flush()
            
            logger.info(f"Course created: {course_code}")
            return course
        
        except SQLAlchemyError as e:
            logger.error(f"Error creating course: {str(e)}")
            await session.rollback()
            raise
    
    @staticmethod
    async def get_course_by_id(
        session: AsyncSession,
        course_id: str
    ) -> Optional[Course]:
        """Get course by ID with relationships"""
        try:
            result = await session.execute(
                select(Course)
                .where(Course.id == course_id)
                .options(
                    selectinload(Course.course_outcomes),
                    selectinload(Course.exams)
                )
            )
            return result.scalar_one_or_none()
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting course: {str(e)}")
            return None
    
    @staticmethod
    async def get_course_by_code(
        session: AsyncSession,
        course_code: str
    ) -> Optional[Course]:
        """Get course by course code"""
        try:
            result = await session.execute(
                select(Course).where(Course.course_code == course_code)
            )
            return result.scalar_one_or_none()
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting course by code: {str(e)}")
            return None
    
    @staticmethod
    async def get_all_courses(
        session: AsyncSession,
        semester: Optional[int] = None,
        department_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Course]:
        """Get all courses with optional filtering"""
        try:
            query = select(Course)
            
            # Apply filters
            filters = []
            if semester is not None:
                filters.append(Course.semester == semester)
            if department_id:
                filters.append(Course.department == department_id)
            
            if filters:
                query = query.where(and_(*filters))
            
            result = await session.execute(
                query.offset(skip).limit(limit)
            )
            return result.scalars().all()
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting courses: {str(e)}")
            return []
    
    @staticmethod
    async def update_course(
        session: AsyncSession,
        course_id: str,
        **kwargs
    ) -> Optional[Course]:
        """Update course information"""
        try:
            course = await CourseRepository.get_course_by_id(session, course_id)
            if not course:
                return None
            
            # Update allowed fields
            allowed_fields = [
                'course_name', 'description', 'credits', 
                'semester', 'department', 'syllabus', 'syllabus_embedding_id'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    setattr(course, field, value)
            
            await session.flush()
            logger.info(f"Course updated: {course_id}")
            return course
        
        except SQLAlchemyError as e:
            logger.error(f"Error updating course: {str(e)}")
            await session.rollback()
            return None
    
    @staticmethod
    async def delete_course(
        session: AsyncSession,
        course_id: str
    ) -> bool:
        """Delete a course"""
        try:
            course = await CourseRepository.get_course_by_id(session, course_id)
            if not course:
                return False
            
            await session.delete(course)
            await session.flush()
            
            logger.info(f"Course deleted: {course_id}")
            return True
        
        except SQLAlchemyError as e:
            logger.error(f"Error deleting course: {str(e)}")
            await session.rollback()
            return False


class CourseOutcomeRepository:
    """Repository for course outcome operations"""
    
    @staticmethod
    async def create_course_outcome(
        session: AsyncSession,
        course_id: str,
        co_code: str,
        co_statement: str,
        bloom_level: str,
        description: str = None
    ) -> CourseOutcome:
        """Create a new course outcome"""
        try:
            co = CourseOutcome(
                id=str(uuid.uuid4()),
                course_id=course_id,
                code=co_code,
                statement=co_statement,
                bloom_level=bloom_level,
                description=description,
                is_active=True
            )
            
            session.add(co)
            await session.flush()
            
            logger.info(f"Course outcome created: {co_code}")
            return co
        
        except SQLAlchemyError as e:
            logger.error(f"Error creating course outcome: {str(e)}")
            await session.rollback()
            raise
    
    @staticmethod
    async def get_course_outcomes(
        session: AsyncSession,
        course_id: str,
        active_only: bool = True
    ) -> List[CourseOutcome]:
        """Get all course outcomes for a course"""
        try:
            query = select(CourseOutcome).where(CourseOutcome.course_id == course_id)
            
            if active_only:
                query = query.where(CourseOutcome.is_active == True)
            
            result = await session.execute(query)
            return result.scalars().all()
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting course outcomes: {str(e)}")
            return []
    
    @staticmethod
    async def get_course_outcome_by_id(
        session: AsyncSession,
        co_id: str
    ) -> Optional[CourseOutcome]:
        """Get course outcome by ID"""
        try:
            result = await session.execute(
                select(CourseOutcome).where(CourseOutcome.id == co_id)
            )
            return result.scalar_one_or_none()
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting course outcome: {str(e)}")
            return None
    
    @staticmethod
    async def update_course_outcome(
        session: AsyncSession,
        co_id: str,
        **kwargs
    ) -> Optional[CourseOutcome]:
        """Update course outcome"""
        try:
            co = await CourseOutcomeRepository.get_course_outcome_by_id(session, co_id)
            if not co:
                return None
            
            allowed_fields = ['statement', 'description', 'bloom_level', 'is_active']
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    setattr(co, field, value)
            
            await session.flush()
            logger.info(f"Course outcome updated: {co_id}")
            return co
        
        except SQLAlchemyError as e:
            logger.error(f"Error updating course outcome: {str(e)}")
            await session.rollback()
            return None


class ExamRepository:
    """Repository for exam operations"""
    
    @staticmethod
    async def create_exam(
        session: AsyncSession,
        course_id: str,
        exam_name: str,
        exam_type: str,
        total_marks: int,
        created_by: str,
        duration_minutes: int = None,
        exam_date: str = None
    ) -> Exam:
        """Create a new exam"""
        try:
            exam = Exam(
                id=str(uuid.uuid4()),
                course_id=course_id,
                exam_name=exam_name,
                exam_type=exam_type,
                total_marks=total_marks,
                duration_minutes=duration_minutes,
                exam_date=exam_date,
                created_by=created_by,
                question_count=0
            )
            
            session.add(exam)
            await session.flush()
            
            logger.info(f"Exam created: {exam_name}")
            return exam
        
        except SQLAlchemyError as e:
            logger.error(f"Error creating exam: {str(e)}")
            await session.rollback()
            raise
    
    @staticmethod
    async def get_exams_by_course(
        session: AsyncSession,
        course_id: str
    ) -> List[Exam]:
        """Get all exams for a course"""
        try:
            result = await session.execute(
                select(Exam)
                .where(Exam.course_id == course_id)
                .options(selectinload(Exam.questions))
            )
            return result.scalars().all()
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting exams: {str(e)}")
            return []
    
    @staticmethod
    async def get_exam_by_id(
        session: AsyncSession,
        exam_id: str
    ) -> Optional[Exam]:
        """Get exam by ID with questions"""
        try:
            result = await session.execute(
                select(Exam)
                .where(Exam.id == exam_id)
                .options(selectinload(Exam.questions))
            )
            return result.scalar_one_or_none()
        
        except SQLAlchemyError as e:
            logger.error(f"Error getting exam: {str(e)}")
            return None
