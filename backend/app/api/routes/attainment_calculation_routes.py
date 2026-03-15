"""
Attainment calculation and reporting API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.core.database.connection_manager import get_db_session
from app.core.logging.system_logger import SystemLogger
from app.modules.attainment_engine.analytics.attainment_calculator import AttainmentCalculator

logger = SystemLogger("attainment_routes")

router = APIRouter(prefix="/attainment", tags=["Attainment Calculations"])


class COAttainmentRequest(BaseModel):
    """Request to calculate CO attainment"""
    course_outcome_id: str
    exam_id: str
    course_id: str


class POAttainmentRequest(BaseModel):
    """Request to calculate PO attainment"""
    program_outcome_id: str
    course_id: str
    program_id: str


class PSOAttainmentRequest(BaseModel):
    """Request to calculate PSO attainment"""
    pso_id: str
    course_id: str
    program_id: str


class AttainmentResponse(BaseModel):
    """Attainment calculation response"""
    attainment_percentage: float
    attainment_level: str
    total_students: int
    total_marks: Optional[float] = None
    marks_obtained: Optional[float] = None


class POAttainmentResponse(BaseModel):
    """PO attainment response"""
    program_outcome_id: str
    course_id: str
    program_id: str
    mapped_co_count: int
    attainment_percentage: float
    attainment_level: str


class PSOAttainmentResponse(BaseModel):
    """PSO attainment response"""
    pso_id: str
    course_id: str
    program_id: str
    mapped_co_count: int
    attainment_percentage: float
    attainment_level: str


class ClassStatisticsResponse(BaseModel):
    """Class statistics response"""
    total_students: int
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    q1: float
    q3: float


class ComprehensiveReportResponse(BaseModel):
    """Comprehensive attainment report"""
    course_id: str
    course_code: str
    course_name: str
    report_generated_at: str
    summary: Dict[str, Any]
    co_attainments: List[Dict[str, Any]]
    po_attainments: List[Dict[str, Any]]


@router.post("/calculate-co", response_model=AttainmentResponse)
async def calculate_co_attainment(
    request: COAttainmentRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Calculate CO attainment for a specific exam.
    
    Formula: Sum(marks for CO questions) / Sum(total marks for CO)
    """
    try:
        result = await AttainmentCalculator.calculate_co_attainment_db(
            session=session,
            course_outcome_id=request.course_outcome_id,
            exam_id=request.exam_id,
            course_id=request.course_id
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not calculate CO attainment"
            )
        
        # Save to database
        await AttainmentCalculator.save_co_attainment(session, result)
        await session.commit()
        
        return AttainmentResponse(
            attainment_percentage=result['attainment_percentage'],
            attainment_level=result['attainment_level'],
            total_students=result['total_students'],
            total_marks=result.get('total_question_marks'),
            marks_obtained=result.get('total_marks_obtained')
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating CO attainment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate CO attainment"
        )


@router.post("/calculate-po", response_model=POAttainmentResponse)
async def calculate_po_attainment(
    request: POAttainmentRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Calculate PO attainment for a course.
    
    Formula: Average of mapped CO attainments
    """
    try:
        result = await AttainmentCalculator.calculate_po_attainment_db(
            session=session,
            program_outcome_id=request.program_outcome_id,
            course_id=request.course_id,
            program_id=request.program_id
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not calculate PO attainment"
            )
        
        await session.commit()
        
        return POAttainmentResponse(
            program_outcome_id=result['program_outcome_id'],
            course_id=result['course_id'],
            program_id=result['program_id'],
            mapped_co_count=result['mapped_co_count'],
            attainment_percentage=result['attainment_percentage'],
            attainment_level=result['attainment_level']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating PO attainment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate PO attainment"
        )


@router.post("/calculate-pso", response_model=PSOAttainmentResponse)
async def calculate_pso_attainment(
    request: PSOAttainmentRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Calculate PSO attainment for a course.
    
    Formula: Average of mapped CO attainments
    """
    try:
        result = await AttainmentCalculator.calculate_pso_attainment_db(
            session=session,
            pso_id=request.pso_id,
            course_id=request.course_id,
            program_id=request.program_id
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not calculate PSO attainment"
            )
        
        await session.commit()
        
        return PSOAttainmentResponse(
            pso_id=result['pso_id'],
            course_id=result['course_id'],
            program_id=result['program_id'],
            mapped_co_count=result['mapped_co_count'],
            attainment_percentage=result['attainment_percentage'],
            attainment_level=result['attainment_level']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating PSO attainment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate PSO attainment"
        )


@router.post("/report/{course_id}", response_model=ComprehensiveReportResponse)
async def generate_course_report(
    course_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Generate comprehensive attainment report for a course"""
    try:
        report = await AttainmentCalculator.generate_comprehensive_report(
            session=session,
            course_id=course_id
        )
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found or no attainment data available"
            )
        
        return ComprehensiveReportResponse(
            course_id=report['course_id'],
            course_code=report['course_code'],
            course_name=report['course_name'],
            report_generated_at=report['report_generated_at'],
            summary=report['summary'],
            co_attainments=report['co_attainments'],
            po_attainments=report['po_attainments']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("/statistics/{exam_id}")
async def get_exam_statistics(
    exam_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive statistics for an exam including
    class performance metrics and attainment distribution
    """
    try:
        from sqlalchemy import select
        from app.core.database.models import StudentMarks, ExamQuestion
        
        # Get all student marks for the exam
        marks_result = await session.execute(
            select(StudentMarks.marks_obtained, ExamQuestion.marks)
            .join(ExamQuestion, StudentMarks.question_id == ExamQuestion.id)
            .where(StudentMarks.exam_id == exam_id)
        )
        
        marks_data = marks_result.all()
        if not marks_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found or no marks data available"
            )
        
        # Calculate percentages
        percentages = [
            (obtained / total * 100) if total > 0 else 0
            for obtained, total in marks_data
        ]
        
        statistics = AttainmentCalculator.calculate_class_statistics(percentages)
        
        return {
            "exam_id": exam_id,
            "statistics": statistics
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exam statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get exam statistics"
        )


@router.get("/health")
async def attainment_health_check(
    session: AsyncSession = Depends(get_db_session)
):
    """Health check for attainment service"""
    try:
        from sqlalchemy import select, text
        
        await session.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "attainment_calculator",
            "database": "connected"
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )
