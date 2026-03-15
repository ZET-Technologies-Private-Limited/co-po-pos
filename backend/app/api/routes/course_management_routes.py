"""
Course management API routes for CRUD operations and course outcome generation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.core.database.connection_manager import get_db_session
from app.core.logging.system_logger import SystemLogger
from app.modules.courses.repositories.course_repository import (
    CourseRepository, CourseOutcomeRepository, ExamRepository
)

logger = SystemLogger("course_routes")

router = APIRouter(prefix="/courses", tags=["Courses"])


class CourseCreateRequest(BaseModel):
    """Course creation request"""
    course_code: str = Field(..., max_length=50)
    course_name: str = Field(..., max_length=255)
    credits: int = Field(default=3, ge=1, le=6)
    semester: Optional[int] = Field(None, ge=1, le=8)
    department_id: Optional[str] = None
    syllabus: Optional[str] = None
    description: Optional[str] = None


class CourseResponse(BaseModel):
    """Course response"""
    id: str
    course_code: str
    course_name: str
    credits: int
    semester: Optional[int]
    description: Optional[str]
    created_at: str


class CourseOutcomeCreateRequest(BaseModel):
    """Course outcome creation request"""
    co_code: str = Field(..., max_length=50)
    co_statement: str
    bloom_level: str
    description: Optional[str] = None


class CourseOutcomeResponse(BaseModel):
    """Course outcome response"""
    id: str
    code: str
    statement: str
    bloom_level: str
    description: Optional[str]
    is_active: bool


class CourseDetailResponse(BaseModel):
    """Detailed course response with outcomes"""
    id: str
    course_code: str
    course_name: str
    credits: int
    semester: Optional[int]
    description: Optional[str]
    course_outcomes: List[CourseOutcomeResponse] = []
    created_at: str


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    request: CourseCreateRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Create a new course"""
    try:
        # Check if course already exists
        existing = await CourseRepository.get_course_by_code(session, request.course_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Course with code {request.course_code} already exists"
            )
        
        course = await CourseRepository.create_course(
            session=session,
            course_code=request.course_code,
            course_name=request.course_name,
            credits=request.credits,
            semester=request.semester,
            department_id=request.department_id,
            syllabus=request.syllabus,
            description=request.description
        )
        
        await session.commit()
        
        return CourseResponse(
            id=course.id,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            semester=course.semester,
            description=course.description,
            created_at=course.created_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course"
        )


@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_course(
    course_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get course details with outcomes"""
    try:
        course = await CourseRepository.get_course_by_id(session, course_id)
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        outcomes = await CourseOutcomeRepository.get_course_outcomes(
            session, course_id, active_only=True
        )
        
        return CourseDetailResponse(
            id=course.id,
            course_code=course.course_code,
            course_name=course.course_name,
            credits=course.credits,
            semester=course.semester,
            description=course.description,
            course_outcomes=[
                CourseOutcomeResponse(
                    id=co.id,
                    code=co.code,
                    statement=co.statement,
                    bloom_level=co.bloom_level,
                    description=co.description,
                    is_active=co.is_active
                )
                for co in outcomes
            ],
            created_at=course.created_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get course"
        )


@router.get("", response_model=List[CourseResponse])
async def list_courses(
    semester: Optional[int] = Query(None),
    department_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session)
):
    """List all courses with optional filtering"""
    try:
        courses = await CourseRepository.get_all_courses(
            session=session,
            semester=semester,
            department_id=department_id,
            skip=skip,
            limit=limit
        )
        
        return [
            CourseResponse(
                id=c.id,
                course_code=c.course_code,
                course_name=c.course_name,
                credits=c.credits,
                semester=c.semester,
                description=c.description,
                created_at=c.created_at.isoformat()
            )
            for c in courses
        ]
    
    except Exception as e:
        logger.error(f"Error listing courses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list courses"
        )


@router.post("/{course_id}/outcomes", response_model=CourseOutcomeResponse, 
            status_code=status.HTTP_201_CREATED)
async def create_course_outcome(
    course_id: str,
    request: CourseOutcomeCreateRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Create a course outcome for a course"""
    try:
        # Verify course exists
        course = await CourseRepository.get_course_by_id(session, course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Create outcome
        outcome = await CourseOutcomeRepository.create_course_outcome(
            session=session,
            course_id=course_id,
            co_code=request.co_code,
            co_statement=request.co_statement,
            bloom_level=request.bloom_level,
            description=request.description
        )
        
        await session.commit()
        
        return CourseOutcomeResponse(
            id=outcome.id,
            code=outcome.code,
            statement=outcome.statement,
            bloom_level=outcome.bloom_level,
            description=outcome.description,
            is_active=outcome.is_active
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating course outcome: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course outcome"
        )


@router.get("/{course_id}/outcomes", response_model=List[CourseOutcomeResponse])
async def get_course_outcomes(
    course_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get all outcomes for a course"""
    try:
        # Verify course exists
        course = await CourseRepository.get_course_by_id(session, course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        outcomes = await CourseOutcomeRepository.get_course_outcomes(
            session, course_id, active_only=True
        )
        
        return [
            CourseOutcomeResponse(
                id=co.id,
                code=co.code,
                statement=co.statement,
                bloom_level=co.bloom_level,
                description=co.description,
                is_active=co.is_active
            )
            for co in outcomes
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course outcomes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get course outcomes"
        )


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    request: CourseCreateRequest,
    session: AsyncSession = Depends(get_db_session)
):
    """Update course information"""
    try:
        updated_course = await CourseRepository.update_course(
            session=session,
            course_id=course_id,
            course_name=request.course_name,
            credits=request.credits,
            semester=request.semester,
            description=request.description,
            syllabus=request.syllabus
        )
        
        if not updated_course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        await session.commit()
        
        return CourseResponse(
            id=updated_course.id,
            course_code=updated_course.course_code,
            course_name=updated_course.course_name,
            credits=updated_course.credits,
            semester=updated_course.semester,
            description=updated_course.description,
            created_at=updated_course.created_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update course"
        )


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a course"""
    try:
        success = await CourseRepository.delete_course(session, course_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        await session.commit()
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting course: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete course"
        )
