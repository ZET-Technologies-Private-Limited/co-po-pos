"""
Course management API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import uuid
from datetime import datetime

from app.core.database.connection_manager import db_manager
from app.core.logging.system_logger import SystemLogger

router = APIRouter(prefix="/courses", tags=["Courses"])
logger = SystemLogger("course_routes")


class CourseCreate(BaseModel):
    course_code: str
    course_name: str
    description: str = None
    credits: int = 3
    semester: int = None
    department: str = None
    syllabus: str = None


class CourseResponse(BaseModel):
    id: str
    course_code: str
    course_name: str
    description: str = None
    credits: int
    semester: int = None
    department: str = None
    created_at: datetime


async def get_session():
    """Get database session dependency"""
    async for session in db_manager.get_session():
        yield session


@router.post("", response_model=CourseResponse)
async def create_course(
    course: CourseCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new course"""
    try:
        from app.core.database.models import Course
        
        logger.info(
            "Creating course",
            course_code=course.course_code
        )
        
        # Check if course code already exists
        from sqlalchemy import select
        stmt = select(Course).where(Course.course_code == course.course_code)
        result = await session.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Course with code {course.course_code} already exists"
            )
        
        # Create new course
        new_course = Course(
            id=str(uuid.uuid4()),
            course_code=course.course_code,
            course_name=course.course_name,
            description=course.description,
            credits=course.credits,
            semester=course.semester,
            department=course.department,
            syllabus=course.syllabus,
            created_at=datetime.utcnow()
        )
        
        session.add(new_course)
        await session.commit()
        await session.refresh(new_course)
        
        logger.info(
            "Course created successfully",
            course_id=new_course.id
        )
        
        return CourseResponse(
            id=new_course.id,
            course_code=new_course.course_code,
            course_name=new_course.course_name,
            description=new_course.description,
            credits=new_course.credits,
            semester=new_course.semester,
            department=new_course.department,
            created_at=new_course.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Course creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create course"
        )


@router.get("", response_model=List[CourseResponse])
async def list_courses(
    skip: int = 0,
    limit: int = 10,
    session: AsyncSession = Depends(get_session)
):
    """List all courses"""
    try:
        from app.core.database.models import Course
        from sqlalchemy import select
        
        stmt = select(Course).offset(skip).limit(limit)
        result = await session.execute(stmt)
        courses = result.scalars().all()
        
        return [
            CourseResponse(
                id=c.id,
                course_code=c.course_code,
                course_name=c.course_name,
                description=c.description,
                credits=c.credits,
                semester=c.semester,
                department=c.department,
                created_at=c.created_at
            )
            for c in courses
        ]
    
    except Exception as e:
        logger.error("Failed to list courses", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve courses"
        )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Get course by ID"""
    try:
        from app.core.database.models import Course
        from sqlalchemy import select
        
        stmt = select(Course).where(Course.id == course_id)
        result = await session.execute(stmt)
        course = result.scalars().first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        return CourseResponse(
            id=course.id,
            course_code=course.course_code,
            course_name=course.course_name,
            description=course.description,
            credits=course.credits,
            semester=course.semester,
            department=course.department,
            created_at=course.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get course", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve course"
        )


@router.post("/{course_id}/generate-co")
async def generate_course_outcomes(
    course_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Generate Course Outcomes from course syllabus using AI"""
    try:
        from app.core.database.models import Course
        from app.modules.co_generation.services.co_generation_service import co_generation_service
        from sqlalchemy import select
        
        logger.info(
            "Generating COs for course",
            course_id=course_id
        )
        
        # Get course with syllabus
        stmt = select(Course).where(Course.id == course_id)
        result = await session.execute(stmt)
        course = result.scalars().first()
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        if not course.syllabus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course must have a syllabus to generate outcomes"
            )
        
        # Generate COs using AI
        result = await co_generation_service.generate_course_outcomes(
            syllabus_text=course.syllabus,
            course_code=course.course_code,
            course_name=course.course_name
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "CO generation failed")
            )
        
        logger.info(
            "COs generated successfully",
            course_id=course_id,
            co_count=len(result.get("course_outcomes", []))
        )
        
        return {
            "success": True,
            "course_id": course_id,
            "generated_outcomes": result.get("course_outcomes", []),
            "coverage_analysis": result.get("coverage_validation", {})
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("CO generation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate course outcomes"
        )
