from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.core.database.models import Course, Exam, ExamQuestion, CourseOutcome, StudentEnrollment
from app.modules.repositories.base_repository import BaseRepository
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("course_service")


class CourseService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.course_repo = BaseRepository(Course)
        self.exam_repo = BaseRepository(Exam)
        self.question_repo = BaseRepository(ExamQuestion)
        self.co_repo = BaseRepository(CourseOutcome)
    
    async def create_course(
        self, course_code: str, course_name: str, credits: int,
        semester: int, description: str, faculty_id: str, **kwargs
    ) -> Course:
        course_data = {
            'course_code': course_code,
            'course_name': course_name,
            'credits': credits,
            'semester': semester,
            'description': description,
            'created_by': faculty_id,
            **kwargs
        }
        course = await self.course_repo.create(self.session, **course_data)
        await self.session.commit()
        logger.info(f"Course created: {course.id}")
        return course
    
    async def get_course(self, course_id: str) -> Optional[Course]:
        return await self.course_repo.get_by_id(self.session, course_id)
    
    async def list_courses(self, semester: Optional[int] = None, skip: int = 0, limit: int = 100, **filters) -> List[Course]:
        stmt = select(Course).offset(skip).limit(limit)
        
        if semester:
            stmt = stmt.where(Course.semester == semester)
        if 'department' in filters:
            stmt = stmt.where(Course.department == filters['department'])
        if 'created_by' in filters:
            stmt = stmt.where(Course.created_by == filters['created_by'])
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_exam(
        self, course_id: str, exam_name: str, exam_type: str,
        total_marks: int, duration_minutes: Optional[int] = None,
        exam_date: Optional[datetime] = None,
        question_count: Optional[int] = None, **kwargs
    ) -> Exam:
        exam_data = {
            'course_id': course_id,
            'exam_name': exam_name,
            'exam_type': exam_type,
            'total_marks': total_marks,
            'duration_minutes': duration_minutes or 120,
            'exam_date': exam_date,
            'question_count': question_count or 0,
            **kwargs
        }
        exam = await self.exam_repo.create(self.session, **exam_data)
        await self.session.commit()
        logger.info(f"Exam created: {exam.id}")
        return exam
    
    async def add_question(
        self, exam_id: str, question_text: str, marks: int, question_number: int, **kwargs
    ) -> ExamQuestion:
        question_data = {
            'exam_id': exam_id,
            'question_text': question_text,
            'marks': marks,
            'question_number': question_number,
            **kwargs
        }
        question = await self.question_repo.create(self.session, **question_data)
        await self.session.commit()
        logger.info(f"Question added: {question.id}")
        return question
    
    # ==================== ENHANCED CRUD OPERATIONS ====================
    
    async def update_course(self, course_id: str, **data) -> Optional[Course]:
        """Update course with any fields"""
        course = await self.course_repo.update(self.session, course_id, **data)
        await self.session.commit()
        logger.info(f"Course updated: {course_id}")
        return course
    
    async def delete_course(self, course_id: str) -> bool:
        """Delete course"""
        deleted = await self.course_repo.delete(self.session, course_id)
        await self.session.commit()
        logger.info(f"Course deleted: {course_id}")
        return deleted
    
    async def search_courses(self, query: str, limit: int = 10) -> List[Course]:
        """Search courses by code or name"""
        stmt = select(Course).where(
            or_(
                Course.course_code.ilike(f"%{query}%"),
                Course.course_name.ilike(f"%{query}%")
            )
        ).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_courses(self, **filters) -> int:
        """Count courses with filters"""
        stmt = select(func.count()).select_from(Course)
        
        if 'semester' in filters:
            stmt = stmt.where(Course.semester == filters['semester'])
        if 'department' in filters:
            stmt = stmt.where(Course.department == filters['department'])
        if 'created_by' in filters:
            stmt = stmt.where(Course.created_by == filters['created_by'])
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    # ==================== EXAM CRUD OPERATIONS ====================
    
    async def get_exam(self, exam_id: str) -> Optional[Exam]:
        """Get exam by ID"""
        return await self.exam_repo.get_by_id(self.session, exam_id)
    
    async def update_exam(self, exam_id: str, **data) -> Optional[Exam]:
        """Update exam"""
        exam = await self.exam_repo.update(self.session, exam_id, **data)
        await self.session.commit()
        logger.info(f"Exam updated: {exam_id}")
        return exam
    
    async def delete_exam(self, exam_id: str) -> bool:
        """Delete exam"""
        deleted = await self.exam_repo.delete(self.session, exam_id)
        await self.session.commit()
        logger.info(f"Exam deleted: {exam_id}")
        return deleted
    
    async def list_exams(self, course_id: str) -> List[Exam]:
        """List exams for a course"""
        stmt = select(Exam).where(Exam.course_id == course_id).order_by(Exam.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    # ==================== QUESTION CRUD OPERATIONS ====================
    
    async def get_question(self, question_id: str) -> Optional[ExamQuestion]:
        """Get question by ID"""
        return await self.question_repo.get_by_id(self.session, question_id)
    
    async def update_question(self, question_id: str, **data) -> Optional[ExamQuestion]:
        """Update question"""
        question = await self.question_repo.update(self.session, question_id, **data)
        await self.session.commit()
        logger.info(f"Question updated: {question_id}")
        return question
    
    async def delete_question(self, question_id: str) -> bool:
        """Delete question"""
        deleted = await self.question_repo.delete(self.session, question_id)
        await self.session.commit()
        logger.info(f"Question deleted: {question_id}")
        return deleted
    
    async def list_questions(self, exam_id: str) -> List[ExamQuestion]:
        """List questions for an exam"""
        stmt = select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.question_number)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    # ==================== COURSE OUTCOME OPERATIONS ====================
    
    async def create_course_outcome(self, course_id: str, code: str, statement: str, bloom_level: str, **kwargs) -> CourseOutcome:
        """Create course outcome"""
        co_data = {
            'course_id': course_id,
            'code': code,
            'statement': statement,
            'bloom_level': bloom_level,
            **kwargs
        }
        co = await self.co_repo.create(self.session, **co_data)
        await self.session.commit()
        logger.info(f"Course outcome created: {co.id}")
        return co
    
    async def get_course_outcome(self, co_id: str) -> Optional[CourseOutcome]:
        """Get course outcome by ID"""
        return await self.co_repo.get_by_id(self.session, co_id)
    
    async def update_course_outcome(self, co_id: str, **data) -> Optional[CourseOutcome]:
        """Update course outcome"""
        co = await self.co_repo.update(self.session, co_id, **data)
        await self.session.commit()
        logger.info(f"Course outcome updated: {co_id}")
        return co
    
    async def delete_course_outcome(self, co_id: str) -> bool:
        """Delete course outcome"""
        deleted = await self.co_repo.delete(self.session, co_id)
        await self.session.commit()
        logger.info(f"Course outcome deleted: {co_id}")
        return deleted
    
    async def list_course_outcomes(self, course_id: str) -> List[CourseOutcome]:
        """List course outcomes for a course"""
        stmt = select(CourseOutcome).where(CourseOutcome.course_id == course_id).order_by(CourseOutcome.code)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    # ==================== ENROLLMENT OPERATIONS ====================
    
    async def get_course_enrollments(self, course_id: str) -> List[StudentEnrollment]:
        """Get all enrollments for a course"""
        stmt = select(StudentEnrollment).where(StudentEnrollment.course_id == course_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_enrollment_count(self, course_id: str) -> int:
        """Get enrollment count for a course"""
        stmt = select(func.count()).select_from(StudentEnrollment).where(StudentEnrollment.course_id == course_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
