"""
Course repository for database operations
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.core.database.models import Course, CourseOutcome, Exam, StudentMarks
from app.modules.repositories.base_repository import BaseRepository


class CourseRepository(BaseRepository[Course]):
    """Repository for Course operations"""
    
    def __init__(self):
        super().__init__(Course)
    
    async def get_by_code(self, session: AsyncSession, course_code: str) -> Optional[Course]:
        """Get course by course code"""
        stmt = select(self.model).where(self.model.course_code == course_code)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_with_outcomes(self, session: AsyncSession, course_id: str) -> Optional[Course]:
        """Get course with course outcomes loaded"""
        stmt = select(self.model).where(self.model.id == course_id).options(
            selectinload(self.model.course_outcomes)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_with_exams(self, session: AsyncSession, course_id: str) -> Optional[Course]:
        """Get course with exams loaded"""
        stmt = select(self.model).where(self.model.id == course_id).options(
            selectinload(self.model.exams)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_department(
        self, 
        session: AsyncSession, 
        department: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Course]:
        """Get courses by department"""
        stmt = select(self.model).where(
            self.model.department == department
        ).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_semester(
        self, 
        session: AsyncSession, 
        semester: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Course]:
        """Get courses by semester"""
        stmt = select(self.model).where(
            self.model.semester == semester
        ).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_course_statistics(
        self, 
        session: AsyncSession, 
        course_id: str
    ) -> Dict[str, Any]:
        """Get statistics for a course"""
        course = await self.get_with_outcomes(session, course_id)
        if not course:
            return {}
        
        co_count = len(course.course_outcomes) if course.course_outcomes else 0
        
        exam_stmt = select(func.count()).select_from(Exam).where(Exam.course_id == course_id)
        exam_result = await session.execute(exam_stmt)
        exam_count = exam_result.scalar() or 0
        
        return {
            "course_id": course_id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "co_count": co_count,
            "exam_count": exam_count,
            "credits": course.credits,
            "semester": course.semester,
            "department": course.department
        }
