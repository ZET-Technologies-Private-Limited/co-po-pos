"""
Course Outcome repository for database operations
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.core.database.models import (
    CourseOutcome, Course, ProgramOutcome, ProgramSpecificOutcome,
    co_po_mapping_table, co_pso_mapping_table, question_co_mapping_table,
    ExamQuestion, StudentMarks
)
from app.modules.repositories.base_repository import BaseRepository


class CourseOutcomeRepository(BaseRepository[CourseOutcome]):
    """Repository for Course Outcome operations"""
    
    def __init__(self):
        super().__init__(CourseOutcome)
    
    async def get_by_course(
        self, 
        session: AsyncSession, 
        course_id: str
    ) -> List[CourseOutcome]:
        """Get all COs for a course"""
        stmt = select(self.model).where(
            self.model.course_id == course_id
        ).options(
            selectinload(self.model.program_outcomes),
            selectinload(self.model.program_specific_outcomes)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_by_code(
        self, 
        session: AsyncSession, 
        course_id: str, 
        code: str
    ) -> Optional[CourseOutcome]:
        """Get CO by course and code"""
        stmt = select(self.model).where(
            and_(self.model.course_id == course_id, self.model.code == code)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_outcomes(
        self, 
        session: AsyncSession, 
        course_id: str
    ) -> List[CourseOutcome]:
        """Get active COs for a course"""
        stmt = select(self.model).where(
            and_(self.model.course_id == course_id, self.model.is_active == True)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_with_mappings(
        self, 
        session: AsyncSession, 
        co_id: str
    ) -> Optional[CourseOutcome]:
        """Get CO with PO and PSO mappings"""
        stmt = select(self.model).where(self.model.id == co_id).options(
            selectinload(self.model.program_outcomes),
            selectinload(self.model.program_specific_outcomes)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_mapped_pos(
        self, 
        session: AsyncSession, 
        co_id: str
    ) -> List[tuple[ProgramOutcome, float]]:
        """Get program outcomes mapped to this CO with similarity scores"""
        stmt = select(ProgramOutcome, co_po_mapping_table.c.similarity_score).join(
            co_po_mapping_table,
            and_(
                co_po_mapping_table.c.course_outcome_id == co_id,
                co_po_mapping_table.c.program_outcome_id == ProgramOutcome.id
            )
        )
        result = await session.execute(stmt)
        return result.all()
    
    async def get_mapped_psos(
        self, 
        session: AsyncSession, 
        co_id: str
    ) -> List[tuple[ProgramSpecificOutcome, float]]:
        """Get program specific outcomes mapped to this CO"""
        stmt = select(ProgramSpecificOutcome, co_pso_mapping_table.c.similarity_score).join(
            co_pso_mapping_table,
            and_(
                co_pso_mapping_table.c.course_outcome_id == co_id,
                co_pso_mapping_table.c.program_specific_outcome_id == ProgramSpecificOutcome.id
            )
        )
        result = await session.execute(stmt)
        return result.all()
    
    async def get_by_bloom_level(
        self, 
        session: AsyncSession, 
        course_id: str, 
        bloom_level: str
    ) -> List[CourseOutcome]:
        """Get COs by Bloom's taxonomy level"""
        stmt = select(self.model).where(
            and_(self.model.course_id == course_id, self.model.bloom_level == bloom_level)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    async def get_co_statistics(
        self, 
        session: AsyncSession, 
        co_id: str
    ) -> Dict[str, Any]:
        """Get statistics for a course outcome"""
        co = await self.get_with_mappings(session, co_id)
        if not co:
            return {}
        
        # Get mapped POs
        pos = await self.get_mapped_pos(session, co_id)
        po_count = len(pos)
        
        # Get mapped PSOs
        psos = await self.get_mapped_psos(session, co_id)
        pso_count = len(psos)
        
        # Get mapped questions
        question_stmt = select(func.count()).select_from(ExamQuestion).join(
            question_co_mapping_table,
            question_co_mapping_table.c.question_id == ExamQuestion.id
        ).where(question_co_mapping_table.c.course_outcome_id == co_id)
        question_result = await session.execute(question_stmt)
        question_count = question_result.scalar() or 0
        
        return {
            "co_id": co_id,
            "code": co.code,
            "statement": co.statement,
            "bloom_level": co.bloom_level,
            "po_count": po_count,
            "pso_count": pso_count,
            "question_count": question_count,
            "is_active": co.is_active
        }
