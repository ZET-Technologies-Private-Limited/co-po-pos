"""
Complete API routes for CO-PO-PSO mapping system
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.core.database.connection_manager import get_session
from app.core.security.jwt_auth import get_current_user
from app.core.database.models import User, Course, CourseOutcome, Exam, ExamQuestion, StudentMarks
from app.modules.repositories.course_repository import CourseRepository
from app.modules.repositories.co_repository import CourseOutcomeRepository
from app.modules.repositories.exam_repository import ExamRepository, ExamQuestionRepository, StudentMarksRepository
from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
from app.modules.attainment_engine.analytics.attainment_calculator import AttainmentCalculator
from app.agents.multi_agent_orchestrator import (
    MultiAgentOrchestrator, ConversationState, COGenerationAgent
)
from app.core.logging.system_logger import SystemLogger
from app.api.v1.auth_routes import router as auth_router

router = APIRouter(prefix="/api/v1", tags=["academic"])
logger = SystemLogger("api_endpoints")

# Repositories
course_repo = CourseRepository()
co_repo = CourseOutcomeRepository()
exam_repo = ExamRepository()
question_repo = ExamQuestionRepository()
marks_repo = StudentMarksRepository()
mapping_service = SemanticMappingService()
orchestrator = MultiAgentOrchestrator()


# ======================== COURSE ENDPOINTS ========================

@router.post("/courses")
async def create_course(
    course_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Create a new course"""
    try:
        logger.info(f"Creating course {course_data.get('course_code')}")
        
        course = await course_repo.create(
            session,
            id=str(uuid.uuid4()),
            course_code=course_data['course_code'],
            course_name=course_data['course_name'],
            description=course_data.get('description'),
            credits=course_data.get('credits', 3),
            semester=course_data.get('semester'),
            department=course_data.get('department'),
            syllabus=course_data.get('syllabus'),
            created_by=current_user.id
        )
        
        await session.commit()
        
        return {
            "success": True,
            "course_id": course.id,
            "course_code": course.course_code,
            "message": "Course created successfully"
        }
    
    except Exception as e:
        logger.error(f"Course creation failed: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}")
async def get_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get course details"""
    try:
        course = await course_repo.get_with_outcomes(session, course_id)
        
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        stats = await course_repo.get_course_statistics(session, course_id)
        
        return {
            "success": True,
            "course": {
                "id": course.id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "credits": course.credits,
                "semester": course.semester,
                "department": course.department,
                "outcomes_count": stats.get('co_count', 0),
                "exams_count": stats.get('exam_count', 0)
            },
            "statistics": stats
        }
    
    except Exception as e:
        logger.error(f"Get course failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/generate-cos")
async def generate_course_outcomes(
    course_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Generate course outcomes from syllabus using AI"""
    try:
        logger.info(f"Generating COs for course {course_id}")
        
        course = await course_repo.get_by_id(session, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        if not course.syllabus:
            raise HTTPException(status_code=400, detail="Course syllabus not provided")
        
        agent = COGenerationAgent()
        result = await agent.execute(
            session,
            course.syllabus,
            course.course_code,
            course.course_name
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # Save generated COs to database
        saved_cos = []
        for i, co_data in enumerate(result['course_outcomes'], 1):
            co = await co_repo.create(
                session,
                id=str(uuid.uuid4()),
                course_id=course_id,
                code=co_data.get('code', f"CO{i}"),
                statement=co_data['statement'],
                bloom_level=co_data.get('bloom_level', 'understand'),
                description=co_data.get('description', '')
            )
            saved_cos.append({
                "id": co.id,
                "code": co.code,
                "statement": co.statement,
                "bloom_level": co.bloom_level
            })
        
        await session.commit()
        
        return {
            "success": True,
            "course_id": course_id,
            "generated_cos": saved_cos,
            "count": len(saved_cos)
        }
    
    except Exception as e:
        logger.error(f"CO generation failed: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ======================== COURSE OUTCOME ENDPOINTS ========================

@router.get("/courses/{course_id}/outcomes")
async def get_course_outcomes(
    course_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get all course outcomes"""
    try:
        cos = await co_repo.get_by_course(session, course_id)
        
        outcomes = []
        for co in cos:
            stats = await co_repo.get_co_statistics(session, co.id)
            outcomes.append({
                "id": co.id,
                "code": co.code,
                "statement": co.statement,
                "bloom_level": co.bloom_level,
                "statistics": stats
            })
        
        return {
            "success": True,
            "course_id": course_id,
            "outcomes": outcomes,
            "count": len(outcomes)
        }
    
    except Exception as e:
        logger.error(f"Get COs failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/courses/{course_id}/outcomes/{co_id}/map-to-pos")
async def map_co_to_pos(
    course_id: str,
    co_id: str,
    program_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Map course outcome to program outcomes"""
    try:
        logger.info(f"Mapping CO {co_id} to POs for program {program_id}")
        
        result = await mapping_service.map_cos_to_pos(session, course_id, program_id)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return result
    
    except Exception as e:
        logger.error(f"CO-PO mapping failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================== EXAM ENDPOINTS ========================

@router.post("/courses/{course_id}/exams")
async def create_exam(
    course_id: str,
    exam_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Create exam"""
    try:
        logger.info(f"Creating exam for course {course_id}")
        
        exam = await exam_repo.create(
            session,
            id=str(uuid.uuid4()),
            course_id=course_id,
            exam_name=exam_data['exam_name'],
            exam_type=exam_data.get('exam_type', 'mid_term'),
            total_marks=exam_data['total_marks'],
            duration_minutes=exam_data.get('duration_minutes'),
            exam_date=exam_data.get('exam_date'),
            created_by=current_user.id
        )
        
        await session.commit()
        
        return {
            "success": True,
            "exam_id": exam.id,
            "exam_name": exam.exam_name,
            "message": "Exam created successfully"
        }
    
    except Exception as e:
        logger.error(f"Exam creation failed: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exams/{exam_id}/questions")
async def add_exam_question(
    exam_id: str,
    question_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Add question to exam"""
    try:
        logger.info(f"Adding question to exam {exam_id}")
        
        question = await question_repo.create(
            session,
            id=str(uuid.uuid4()),
            exam_id=exam_id,
            question_number=question_data.get('question_number'),
            question_text=question_data['question_text'],
            marks=question_data['marks'],
            question_type=question_data.get('question_type', 'mcq'),
            bloom_level=question_data.get('bloom_level')
        )
        
        await session.commit()
        
        return {
            "success": True,
            "question_id": question.id,
            "message": "Question added successfully"
        }
    
    except Exception as e:
        logger.error(f"Add question failed: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ======================== MARKS ENDPOINTS ========================

@router.post("/exams/{exam_id}/marks")
async def submit_student_marks(
    exam_id: str,
    marks_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Submit student marks"""
    try:
        logger.info(f"Submitting marks for exam {exam_id}")
        
        student_id = marks_data.get('student_id')
        question_marks = marks_data.get('marks', [])
        
        saved_marks = []
        for mark_entry in question_marks:
            mark = await marks_repo.create(
                session,
                id=str(uuid.uuid4()),
                exam_id=exam_id,
                student_id=student_id,
                question_id=mark_entry.get('question_id'),
                marks_obtained=mark_entry['marks']
            )
            saved_marks.append({
                "question_id": mark.question_id,
                "marks": float(mark.marks_obtained)
            })
        
        await session.commit()
        
        return {
            "success": True,
            "exam_id": exam_id,
            "student_id": student_id,
            "marks_submitted": len(saved_marks),
            "marks": saved_marks
        }
    
    except Exception as e:
        logger.error(f"Submit marks failed: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ======================== ATTAINMENT ENDPOINTS ========================

@router.post("/exams/{exam_id}/calculate-attainments")
async def calculate_attainments(
    exam_id: str,
    course_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Calculate CO attainments for exam"""
    try:
        logger.info(f"Calculating attainments for exam {exam_id}")
        
        # Get COs for course
        cos = await co_repo.get_by_course(session, course_id)
        
        attainments = []
        for co in cos:
            result = await AttainmentCalculator.calculate_co_attainment_db(
                session, co.id, exam_id, course_id
            )
            
            if result:
                saved = await AttainmentCalculator.save_co_attainment(session, result)
                attainments.append({
                    "co_id": result['course_outcome_id'],
                    "co_code": co.code,
                    "attainment_percentage": result['attainment_percentage'],
                    "attainment_level": result['attainment_level'],
                    "students": result['total_students']
                })
        
        await session.commit()
        
        return {
            "success": True,
            "exam_id": exam_id,
            "course_id": course_id,
            "attainments_calculated": len(attainments),
            "attainments": attainments
        }
    
    except Exception as e:
        logger.error(f"Attainment calculation failed: {str(e)}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/courses/{course_id}/attainment-report")
async def get_attainment_report(
    course_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get comprehensive attainment report"""
    try:
        logger.info(f"Generating attainment report for course {course_id}")
        
        report = await AttainmentCalculator.generate_comprehensive_report(
            session, course_id
        )
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {
            "success": True,
            "report": report
        }
    
    except Exception as e:
        logger.error(f"Report generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================== CONVERSATION/AGENT ENDPOINTS ========================

@router.post("/conversations")
async def start_conversation(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Start new conversation with multi-agent system"""
    try:
        conversation_id = str(uuid.uuid4())
        
        state = ConversationState(
            conversation_id=conversation_id,
            user_id=current_user.id,
            current_agent="general",
            messages=[],
            context={},
            last_updated=datetime.utcnow()
        )
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": "Conversation started. Ready to assist with CO-PO-PSO mapping."
        }
    
    except Exception as e:
        logger.error(f"Conversation start failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/message")
async def send_message_to_agent(
    conversation_id: str,
    message_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Send message to multi-agent system"""
    try:
        user_query = message_data.get('message')
        context = message_data.get('context', {})
        
        logger.info(f"Processing query in conversation {conversation_id}")
        
        # Create state
        state = ConversationState(
            conversation_id=conversation_id,
            user_id=current_user.id,
            current_agent="orchestrator",
            messages=[{"role": "user", "content": user_query}],
            context=context,
            last_updated=datetime.utcnow()
        )
        
        # Process through orchestrator
        result = await orchestrator.process_conversation(session, user_query, state)
        
        return {
            "success": result.get('success', False),
            "conversation_id": conversation_id,
            "agent_response": result.get('agent_response'),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Message processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CO-PO-PSO Mapping API",
        "timestamp": datetime.utcnow().isoformat()
    }
