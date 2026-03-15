"""
Attainment calculation API endpoints
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database.connection_manager import db_manager
from app.core.logging.system_logger import SystemLogger
from app.modules.attainment_engine.analytics.attainment_calculator import attainment_calculator

router = APIRouter(prefix="/attainment", tags=["Attainment"])
logger = SystemLogger("attainment_routes")


class AttainmentResponse(BaseModel):
    attainment_percentage: float
    attainment_level: str
    total_marks: int = None
    marks_obtained: float = None
    student_count: int = None


async def get_session():
    """Get database session dependency"""
    async for session in db_manager.get_session():
        yield session


@router.get("/co/{co_id}", response_model=AttainmentResponse)
async def get_co_attainment(
    co_id: str,
    exam_id: str = Query(None, description="Optional exam filter"),
    session: AsyncSession = Depends(get_session)
):
    """Get Course Outcome attainment"""
    try:
        from app.core.database.models import COAttainment, CourseOutcome
        
        logger.info(
            "Retrieving CO attainment",
            co_id=co_id,
            exam_id=exam_id
        )
        
        # Verify CO exists
        stmt = select(CourseOutcome).where(CourseOutcome.id == co_id)
        result = await session.execute(stmt)
        co = result.scalars().first()
        
        if not co:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course Outcome not found"
            )
        
        # Get attainment record
        if exam_id:
            stmt = select(COAttainment).where(
                (COAttainment.course_outcome_id == co_id) &
                (COAttainment.exam_id == exam_id)
            )
        else:
            stmt = select(COAttainment).where(
                COAttainment.course_outcome_id == co_id
            ).order_by(COAttainment.calculated_at.desc()).limit(1)
        
        result = await session.execute(stmt)
        attainment = result.scalars().first()
        
        if not attainment:
            return AttainmentResponse(
                attainment_percentage=0.0,
                attainment_level="Not Attained",
                total_marks=0,
                marks_obtained=0.0,
                student_count=0
            )
        
        return AttainmentResponse(
            attainment_percentage=float(attainment.attainment_percentage),
            attainment_level=attainment.attainment_level,
            total_marks=attainment.total_marks,
            marks_obtained=float(attainment.marks_obtained) if attainment.marks_obtained else 0,
            student_count=attainment.total_students
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve CO attainment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve attainment data"
        )


@router.get("/po/{po_id}", response_model=AttainmentResponse)
async def get_po_attainment(
    po_id: str,
    course_id: str = Query(None, description="Optional course filter"),
    session: AsyncSession = Depends(get_session)
):
    """Get Program Outcome attainment"""
    try:
        from app.core.database.models import POAttainment, ProgramOutcome
        
        logger.info(
            "Retrieving PO attainment",
            po_id=po_id,
            course_id=course_id
        )
        
        # Verify PO exists
        stmt = select(ProgramOutcome).where(ProgramOutcome.id == po_id)
        result = await session.execute(stmt)
        po = result.scalars().first()
        
        if not po:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Program Outcome not found"
            )
        
        # Get attainment record
        if course_id:
            stmt = select(POAttainment).where(
                (POAttainment.program_outcome_id == po_id) &
                (POAttainment.course_id == course_id)
            )
        else:
            stmt = select(POAttainment).where(
                POAttainment.program_outcome_id == po_id
            ).order_by(POAttainment.calculated_at.desc()).limit(1)
        
        result = await session.execute(stmt)
        attainment = result.scalars().first()
        
        if not attainment:
            return AttainmentResponse(
                attainment_percentage=0.0,
                attainment_level="Not Attained"
            )
        
        return AttainmentResponse(
            attainment_percentage=float(attainment.attainment_percentage),
            attainment_level=attainment.attainment_level
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve PO attainment", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve attainment data"
        )


@router.get("/report/summary")
async def get_attainment_summary(
    course_id: str = Query(None),
    session: AsyncSession = Depends(get_session)
):
    """Get comprehensive attainment summary"""
    try:
        from app.core.database.models import COAttainment, POAttainment
        
        logger.info(
            "Generating attainment summary",
            course_id=course_id
        )
        
        # Get CO attainments
        if course_id:
            stmt = select(COAttainment).where(
                COAttainment.course_outcome_id.in_(
                    select(COAttainment.course_outcome_id).where(
                        COAttainment.course_outcome_id.isnot(None)
                    )
                )
            )
        else:
            stmt = select(COAttainment)
        
        result = await session.execute(stmt)
        co_attainments = result.scalars().all()
        
        # Get PO attainments
        stmt = select(POAttainment)
        result = await session.execute(stmt)
        po_attainments = result.scalars().all()
        
        # Generate report
        report = {
            "summary": {
                "total_cos": len(co_attainments),
                "total_pos": len(po_attainments),
            },
            "co_details": [
                {
                    "id": ca.course_outcome_id,
                    "attainment": float(ca.attainment_percentage),
                    "level": ca.attainment_level
                }
                for ca in co_attainments
            ],
            "po_details": [
                {
                    "id": pa.program_outcome_id,
                    "attainment": float(pa.attainment_percentage),
                    "level": pa.attainment_level
                }
                for pa in po_attainments
            ],
            "statistics": {
                "mean_co_attainment": sum(
                    float(ca.attainment_percentage) for ca in co_attainments
                ) / len(co_attainments) if co_attainments else 0,
                "mean_po_attainment": sum(
                    float(pa.attainment_percentage) for pa in po_attainments
                ) / len(po_attainments) if po_attainments else 0,
            }
        }
        
        logger.info(
            "Attainment summary generated",
            co_count=len(co_attainments),
            po_count=len(po_attainments)
        )
        
        return report
    
    except Exception as e:
        logger.error("Failed to generate attainment summary", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary"
        )
