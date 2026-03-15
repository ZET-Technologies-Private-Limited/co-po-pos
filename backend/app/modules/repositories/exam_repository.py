"""
Exam repository for database operations
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.core.database.models import Exam, ExamQuestion, StudentMarks
from app.modules.repositories.base_repository import BaseRepository


class ExamRepository(BaseRepository[Exam]):
    """Repository for Exam operations"""
    
    def __init__(self):
        super().__init__(Exam)
    
    async def get_by_course(
        self, 
        session: AsyncSession, 
        course_id: str
    ) -> List[Exam]:
        """Get all exams for a course"""
        stmt = select(self.model).where(
            self.model.course_id == course_id
        ).options(selectinload(self.model.questions))
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_with_questions(
        self, 
        session: AsyncSession, 
        exam_id: str
    ) -> Optional[Exam]:
        """Get exam with questions loaded"""
        stmt = select(self.model).where(self.model.id == exam_id).options(
            selectinload(self.model.questions)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_type(
        self, 
        session: AsyncSession, 
        course_id: str, 
        exam_type: str
    ) -> List[Exam]:
        """Get exams by type"""
        stmt = select(self.model).where(
            and_(self.model.course_id == course_id, self.model.exam_type == exam_type)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_exam_statistics(
        self, 
        session: AsyncSession, 
        exam_id: str
    ) -> Dict[str, Any]:
        """Get statistics for an exam"""
        exam = await self.get_with_questions(session, exam_id)
        if not exam:
            return {}
        
        # Get marks statistics
        marks_stmt = select(
            func.count().label('student_count'),
            func.avg(StudentMarks.marks_obtained).label('avg_marks'),
            func.max(StudentMarks.marks_obtained).label('max_marks'),
            func.min(StudentMarks.marks_obtained).label('min_marks')
        ).select_from(StudentMarks).where(StudentMarks.exam_id == exam_id)
        
        marks_result = await session.execute(marks_stmt)
        marks_stats = marks_result.first()
        
        question_count = len(exam.questions) if exam.questions else 0
        
        return {
            "exam_id": exam_id,
            "exam_name": exam.exam_name,
            "exam_type": exam.exam_type,
            "total_marks": exam.total_marks,
            "duration_minutes": exam.duration_minutes,
            "exam_date": exam.exam_date,
            "question_count": question_count,
            "student_count": marks_stats.student_count or 0,
            "avg_marks": float(marks_stats.avg_marks) if marks_stats.avg_marks else 0,
            "max_marks": float(marks_stats.max_marks) if marks_stats.max_marks else 0,
            "min_marks": float(marks_stats.min_marks) if marks_stats.min_marks else 0
        }


class ExamQuestionRepository(BaseRepository[ExamQuestion]):
    """Repository for Exam Question operations"""
    
    def __init__(self):
        super().__init__(ExamQuestion)
    
    async def get_by_exam(
        self, 
        session: AsyncSession, 
        exam_id: str
    ) -> List[ExamQuestion]:
        """Get all questions for an exam"""
        stmt = select(self.model).where(self.model.exam_id == exam_id)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_with_cos(
        self, 
        session: AsyncSession, 
        question_id: str
    ) -> Optional[ExamQuestion]:
        """Get question with mapped course outcomes"""
        stmt = select(self.model).where(self.model.id == question_id).options(
            selectinload(self.model.course_outcomes)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_bloom_level(
        self, 
        session: AsyncSession, 
        exam_id: str, 
        bloom_level: str
    ) -> List[ExamQuestion]:
        """Get questions by Bloom's level"""
        stmt = select(self.model).where(
            and_(self.model.exam_id == exam_id, self.model.bloom_level == bloom_level)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_questions_by_co(
        self, 
        session: AsyncSession, 
        exam_id: str, 
        course_outcome_id: str
    ) -> List[ExamQuestion]:
        """Get all questions mapped to a CO in an exam"""
        from app.core.database.models import question_co_mapping_table
        
        stmt = select(self.model).join(
            question_co_mapping_table,
            and_(
                question_co_mapping_table.c.question_id == self.model.id,
                question_co_mapping_table.c.course_outcome_id == course_outcome_id
            )
        ).where(self.model.exam_id == exam_id)
        
        result = await session.execute(stmt)
        return result.scalars().all()


class StudentMarksRepository(BaseRepository[StudentMarks]):
    """Repository for Student Marks operations"""
    
    def __init__(self):
        super().__init__(StudentMarks)
    
    async def get_by_exam_and_student(
        self, 
        session: AsyncSession, 
        exam_id: str, 
        student_id: str
    ) -> List[StudentMarks]:
        """Get all marks for a student in an exam"""
        stmt = select(self.model).where(
            and_(self.model.exam_id == exam_id, self.model.student_id == student_id)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_total_marks_for_student(
        self, 
        session: AsyncSession, 
        exam_id: str, 
        student_id: str
    ) -> float:
        """Get total marks for a student in an exam"""
        stmt = select(func.sum(StudentMarks.marks_obtained)).where(
            and_(self.model.exam_id == exam_id, self.model.student_id == student_id)
        )
        result = await session.execute(stmt)
        total = result.scalar()
        return float(total) if total else 0.0
    
    async def get_marks_by_question(
        self, 
        session: AsyncSession, 
        question_id: str
    ) -> List[StudentMarks]:
        """Get all marks for a question"""
        stmt = select(self.model).where(self.model.question_id == question_id)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_question_marks_statistics(
        self, 
        session: AsyncSession, 
        question_id: str
    ) -> Dict[str, Any]:
        """Get statistics for a question's marks"""
        stmt = select(
            func.count().label('total_students'),
            func.avg(StudentMarks.marks_obtained).label('avg_marks'),
            func.max(StudentMarks.marks_obtained).label('max_marks'),
            func.min(StudentMarks.marks_obtained).label('min_marks'),
            func.stddev(StudentMarks.marks_obtained).label('std_dev')
        ).where(self.model.question_id == question_id)
        
        result = await session.execute(stmt)
        stats = result.first()
        
        return {
            "question_id": question_id,
            "total_students": stats.total_students or 0,
            "avg_marks": float(stats.avg_marks) if stats.avg_marks else 0,
            "max_marks": float(stats.max_marks) if stats.max_marks else 0,
            "min_marks": float(stats.min_marks) if stats.min_marks else 0,
            "std_dev": float(stats.std_dev) if stats.std_dev else 0
        }
