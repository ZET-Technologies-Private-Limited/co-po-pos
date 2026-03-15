"""
Attainment analytics data access repository
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.core.database.models import COAttainment, POAttainment, PSO_Attainment
from app.modules.repositories.base_repository import BaseRepository


class COAttainmentRepository(BaseRepository):
    """Repository for CO attainment data"""
    
    async def get_by_co_exam(self, session: AsyncSession, co_id: str, exam_id: str) -> Optional[COAttainment]:
        """Get CO attainment for specific CO and exam"""
        query = select(COAttainment).where(
            and_(
                COAttainment.course_outcome_id == co_id,
                COAttainment.exam_id == exam_id
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_course_outcome(self, session: AsyncSession, co_id: str) -> List[COAttainment]:
        """Get all attainments for a CO"""
        query = select(COAttainment).where(COAttainment.course_outcome_id == co_id)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_by_exam(self, session: AsyncSession, exam_id: str) -> List[COAttainment]:
        """Get all CO attainments for an exam"""
        query = select(COAttainment).where(COAttainment.exam_id == exam_id)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_by_attainment_level(self, session: AsyncSession, level: str) -> List[COAttainment]:
        """Get all attainments at a specific level"""
        query = select(COAttainment).where(COAttainment.attainment_level == level)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def create(self, session: AsyncSession, **kwargs) -> COAttainment:
        """Create a new CO attainment record"""
        attainment = COAttainment(**kwargs)
        session.add(attainment)
        await session.flush()
        return attainment
    
    async def update(self, session: AsyncSession, attainment_id: str, **kwargs) -> Optional[COAttainment]:
        """Update CO attainment"""
        attainment = await self.get_by_id(session, attainment_id, COAttainment)
        if attainment:
            for key, value in kwargs.items():
                setattr(attainment, key, value)
            await session.flush()
        return attainment
    
    async def get_average_attainment(self, session: AsyncSession, co_id: str) -> Optional[float]:
        """Get average attainment percentage for a CO"""
        query = select(func.avg(COAttainment.attainment_percentage)).where(
            COAttainment.course_outcome_id == co_id
        )
        result = await session.execute(query)
        return result.scalar()


class POAttainmentRepository(BaseRepository):
    """Repository for PO attainment data"""
    
    async def get_by_po_course(self, session: AsyncSession, po_id: str, course_id: str) -> Optional[POAttainment]:
        """Get PO attainment for specific PO and course"""
        query = select(POAttainment).where(
            and_(
                POAttainment.program_outcome_id == po_id,
                POAttainment.course_id == course_id
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_program_outcome(self, session: AsyncSession, po_id: str) -> List[POAttainment]:
        """Get all attainments for a PO across courses"""
        query = select(POAttainment).where(POAttainment.program_outcome_id == po_id)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_by_course(self, session: AsyncSession, course_id: str) -> List[POAttainment]:
        """Get all PO attainments for a course"""
        query = select(POAttainment).where(POAttainment.course_id == course_id)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def create(self, session: AsyncSession, **kwargs) -> POAttainment:
        """Create a new PO attainment record"""
        attainment = POAttainment(**kwargs)
        session.add(attainment)
        await session.flush()
        return attainment
    
    async def update(self, session: AsyncSession, attainment_id: str, **kwargs) -> Optional[POAttainment]:
        """Update PO attainment"""
        attainment = await self.get_by_id(session, attainment_id, POAttainment)
        if attainment:
            for key, value in kwargs.items():
                setattr(attainment, key, value)
            await session.flush()
        return attainment
    
    async def get_program_po_attainments(self, session: AsyncSession, program_id: str) -> List[POAttainment]:
        """Get all PO attainments for courses in a program"""
        # This would require joining through courses and program
        query = select(POAttainment)
        result = await session.execute(query)
        return result.scalars().all()


class PSOAttainmentRepository(BaseRepository):
    """Repository for PSO attainment data"""
    
    async def get_by_pso_course(self, session: AsyncSession, pso_id: str, course_id: str) -> Optional[PSO_Attainment]:
        """Get PSO attainment for specific PSO and course"""
        query = select(PSO_Attainment).where(
            and_(
                PSO_Attainment.pso_id == pso_id,
                PSO_Attainment.course_id == course_id
            )
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_program_specific_outcome(self, session: AsyncSession, pso_id: str) -> List[PSO_Attainment]:
        """Get all attainments for a PSO across courses"""
        query = select(PSO_Attainment).where(PSO_Attainment.pso_id == pso_id)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_by_course(self, session: AsyncSession, course_id: str) -> List[PSO_Attainment]:
        """Get all PSO attainments for a course"""
        query = select(PSO_Attainment).where(PSO_Attainment.course_id == course_id)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def create(self, session: AsyncSession, **kwargs) -> PSO_Attainment:
        """Create a new PSO attainment record"""
        attainment = PSO_Attainment(**kwargs)
        session.add(attainment)
        await session.flush()
        return attainment
    
    async def update(self, session: AsyncSession, attainment_id: str, **kwargs) -> Optional[PSO_Attainment]:
        """Update PSO attainment"""
        attainment = await self.get_by_id(session, attainment_id, PSO_Attainment)
        if attainment:
            for key, value in kwargs.items():
                setattr(attainment, key, value)
            await session.flush()
        return attainment
