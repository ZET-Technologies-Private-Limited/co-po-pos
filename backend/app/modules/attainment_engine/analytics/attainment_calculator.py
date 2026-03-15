"""
Production-grade attainment calculator with database integration,
real academic formulas, and comprehensive calculations
"""
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from app.core.database.models import (
    CourseOutcome, ProgramOutcome, ProgramSpecificOutcome,
    StudentMarks, ExamQuestion, COAttainment, POAttainment,
    Exam, Course, co_po_mapping_table, co_pso_mapping_table,
    question_co_mapping_table
)
from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger
import numpy as np
import uuid

logger = SystemLogger("attainment_calculator")
settings = get_settings()


class AttainmentCalculator:
    """
    Production-grade attainment calculation engine with real academic formulas,
    database integration, and comprehensive statistics.
    
    Formulas:
    - CO Attainment = Sum(marks for CO questions) / Sum(total marks for CO)
    - PO Attainment = Average of mapped CO attainments
    - PSO Attainment = Average of mapped CO attainments
    """
    
    LEVEL_3_THRESHOLD = settings.attainment_level_3_threshold
    LEVEL_2_THRESHOLD = settings.attainment_level_2_threshold
    LEVEL_1_THRESHOLD = settings.attainment_level_1_threshold
    
    @staticmethod
    def determine_attainment_level(percentage: float) -> str:
        """Determine attainment level from percentage"""
        if percentage >= AttainmentCalculator.LEVEL_3_THRESHOLD * 100:
            return "Level 3"
        elif percentage >= AttainmentCalculator.LEVEL_2_THRESHOLD * 100:
            return "Level 2"
        else:
            return "Level 1"
    
    @staticmethod
    async def calculate_co_attainment_db(
        session: AsyncSession,
        course_outcome_id: str,
        exam_id: str,
        course_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate CO attainment from database with real formula:
        CO Attainment = Sum(marks for CO questions) / Sum(total marks for CO) * 100
        CO Attainment = Sum(marks obtained in CO questions) / Sum(total marks for CO)
        """
        try:
            # Verify CO exists
            co_result = await session.execute(
                select(CourseOutcome).where(CourseOutcome.id == course_outcome_id)
            )
            course_outcome = co_result.scalar_one_or_none()
            
            if not course_outcome:
                logger.error(f"CO not found: {course_outcome_id}")
                return None
            
            # Get questions mapped to this CO in this exam
            questions_result = await session.execute(
                select(ExamQuestion.id, ExamQuestion.marks)
                .join(question_co_mapping_table,
                      ExamQuestion.id == question_co_mapping_table.c.question_id)
                .where(and_(
                    ExamQuestion.exam_id == exam_id,
                    question_co_mapping_table.c.course_outcome_id == course_outcome_id
                ))
            )
            
            questions_data = questions_result.all()
            if not questions_data:
                return {
                    "course_outcome_id": course_outcome_id,
                    "exam_id": exam_id,
                    "total_students": 0,
                    "total_marks": 0,
                    "marks_obtained": 0.0,
                    "attainment_percentage": 0.0,
                    "attainment_level": "Level 1"
                }
            
            question_ids = [q[0] for q in questions_data]
            total_question_marks = sum(q[1] for q in questions_data)
            
            # Get student marks for these questions
            marks_result = await session.execute(
                select(
                    func.count(func.distinct(StudentMarks.student_id)).label("student_count"),
                    func.sum(StudentMarks.marks_obtained).label("total_obtained")
                )
                .where(and_(
                    StudentMarks.exam_id == exam_id,
                    StudentMarks.question_id.in_(question_ids)
                ))
            )
            
            row = marks_result.first()
            total_students = row.student_count or 0
            total_marks_obtained = float(row.total_obtained or 0)
            
            # Calculate attainment percentage
            if total_question_marks > 0 and total_students > 0:
                total_possible = total_question_marks * total_students
                attainment_percentage = (total_marks_obtained / total_possible) * 100
            else:
                attainment_percentage = 0.0
            
            attainment_level = AttainmentCalculator.determine_attainment_level(attainment_percentage)
            
            logger.info(f"CO attainment calculated: {course_outcome_id}, "
                       f"Percentage: {attainment_percentage:.2f}%, Level: {attainment_level}")
            
            return {
                "course_outcome_id": course_outcome_id,
                "exam_id": exam_id,
                "total_students": total_students,
                "total_marks": total_question_marks,
                "marks_obtained": total_marks_obtained,
                "attainment_percentage": round(attainment_percentage, 2),
                "attainment_level": attainment_level
            }
        
        except SQLAlchemyError as e:
            logger.error(f"Database error in CO attainment: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error calculating CO attainment: {str(e)}")
            return None
    
    @staticmethod
    async def calculate_po_attainment_db(
        session: AsyncSession,
        program_outcome_id: str,
        course_id: str,
        program_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate PO attainment as average of mapped CO attainments.
        PO Attainment = Average of mapped CO attainments
        """
        try:
            # Get mapped COs
            cos_result = await session.execute(
                select(CourseOutcome.id)
                .join(co_po_mapping_table,
                      CourseOutcome.id == co_po_mapping_table.c.course_outcome_id)
                .where(and_(
                    CourseOutcome.course_id == course_id,
                    co_po_mapping_table.c.program_outcome_id == program_outcome_id
                ))
            )
            
            co_ids = [row[0] for row in cos_result.all()]
            
            if not co_ids:
                logger.warning(f"No COs mapped to PO {program_outcome_id}")
                return {
                    "program_outcome_id": program_outcome_id,
                    "course_id": course_id,
                    "program_id": program_id,
                    "mapped_co_count": 0,
                    "avg_co_attainment": 0.0,
                    "attainment_percentage": 0.0,
                    "attainment_level": "Level 1"
                }
            
            # Get CO attainments
            attainments_result = await session.execute(
                select(COAttainment.attainment_percentage)
                .where(COAttainment.course_outcome_id.in_(co_ids))
            )
            
            attainments = [row[0] for row in attainments_result.all()]
            
            if attainments:
                avg_attainment = sum(attainments) / len(attainments)
            else:
                avg_attainment = 0.0
            
            attainment_level = AttainmentCalculator.determine_attainment_level(avg_attainment)
            
            logger.info(f"PO attainment calculated: {program_outcome_id}, "
                       f"Percentage: {avg_attainment:.2f}%, Level: {attainment_level}")
            
            return {
                "program_outcome_id": program_outcome_id,
                "course_id": course_id,
                "program_id": program_id,
                "mapped_co_count": len(co_ids),
                "avg_co_attainment": round(avg_attainment, 2),
                "attainment_percentage": round(avg_attainment, 2),
                "attainment_level": attainment_level
            }
        
        except SQLAlchemyError as e:
            logger.error(f"Database error in PO attainment: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error calculating PO attainment: {str(e)}")
            return None
    
    @staticmethod
    async def calculate_pso_attainment_db(
        session: AsyncSession,
        pso_id: str,
        course_id: str,
        program_id: str
    ) -> Optional[Dict[str, Any]]:
        """Calculate PSO attainment using same logic as PO"""
        try:
            # Get mapped COs
            cos_result = await session.execute(
                select(CourseOutcome.id)
                .join(co_pso_mapping_table,
                      CourseOutcome.id == co_pso_mapping_table.c.course_outcome_id)
                .where(and_(
                    CourseOutcome.course_id == course_id,
                    co_pso_mapping_table.c.program_specific_outcome_id == pso_id
                ))
            )
            
            co_ids = [row[0] for row in cos_result.all()]
            
            if not co_ids:
                return {
                    "pso_id": pso_id,
                    "course_id": course_id,
                    "program_id": program_id,
                    "mapped_co_count": 0,
                    "attainment_percentage": 0.0,
                    "attainment_level": "Level 1"
                }
            
            # Get CO attainments
            attainments_result = await session.execute(
                select(COAttainment.attainment_percentage)
                .where(COAttainment.course_outcome_id.in_(co_ids))
            )
            
            attainments = [row[0] for row in attainments_result.all()]
            avg_attainment = sum(attainments) / len(attainments) if attainments else 0.0
            attainment_level = AttainmentCalculator.determine_attainment_level(avg_attainment)
            
            return {
                "pso_id": pso_id,
                "course_id": course_id,
                "program_id": program_id,
                "mapped_co_count": len(co_ids),
                "attainment_percentage": round(avg_attainment, 2),
                "attainment_level": attainment_level
            }
        
        except Exception as e:
            logger.error(f"Error calculating PSO attainment: {str(e)}")
            return None
    
    @staticmethod
    async def save_co_attainment(
        session: AsyncSession,
        attainment_data: Dict[str, Any]
    ) -> Optional[COAttainment]:
        """Save or update CO attainment in database"""
        try:
            existing = await session.execute(
                select(COAttainment).where(and_(
                    COAttainment.course_outcome_id == attainment_data['course_outcome_id'],
                    COAttainment.exam_id == attainment_data['exam_id']
                ))
            )
            
            co_attainment = existing.scalar_one_or_none()
            
            if co_attainment:
                co_attainment.total_students = attainment_data['total_students']
                co_attainment.total_marks = attainment_data['total_marks']
                co_attainment.marks_obtained = Decimal(str(attainment_data['marks_obtained']))
                co_attainment.attainment_percentage = attainment_data['attainment_percentage']
                co_attainment.attainment_level = attainment_data['attainment_level']
                co_attainment.calculated_at = datetime.utcnow()
            else:
                co_attainment = COAttainment(
                    id=str(uuid.uuid4()),
                    course_outcome_id=attainment_data['course_outcome_id'],
                    exam_id=attainment_data['exam_id'],
                    total_students=attainment_data['total_students'],
                    total_marks=attainment_data['total_marks'],
                    marks_obtained=Decimal(str(attainment_data['marks_obtained'])),
                    attainment_percentage=attainment_data['attainment_percentage'],
                    attainment_level=attainment_data['attainment_level'],
                    calculated_at=datetime.utcnow()
                )
                session.add(co_attainment)
            
            await session.flush()
            logger.info(f"CO attainment saved: {attainment_data['course_outcome_id']}")
            return co_attainment
        
        except SQLAlchemyError as e:
            logger.error(f"Error saving CO attainment: {str(e)}")
            await session.rollback()
            return None
    
    @staticmethod
    def calculate_class_statistics(student_marks: List[float]) -> Dict[str, Any]:
        """Calculate class-level statistics from marks"""
        if not student_marks:
            return {
                "total_students": 0,
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0
            }
        
        try:
            marks_array = np.array(student_marks)
            return {
                "total_students": len(student_marks),
                "mean": round(float(np.mean(marks_array)), 2),
                "median": round(float(np.median(marks_array)), 2),
                "std_dev": round(float(np.std(marks_array)), 2),
                "min": round(float(np.min(marks_array)), 2),
                "max": round(float(np.max(marks_array)), 2),
                "q1": round(float(np.percentile(marks_array, 25)), 2),
                "q3": round(float(np.percentile(marks_array, 75)), 2)
            }
        except Exception as e:
            logger.error(f"Error calculating statistics: {str(e)}")
            return {"total_students": len(student_marks), "error": str(e)}
    
    @staticmethod
    async def generate_comprehensive_report(
        session: AsyncSession,
        course_id: str
    ) -> Dict[str, Any]:
        """Generate comprehensive attainment report for a course"""
        try:
            # Get course
            course_result = await session.execute(
                select(Course).where(Course.id == course_id)
            )
            course = course_result.scalar_one_or_none()
            if not course:
                return None
            
            # Get all CO attainments
            cos_result = await session.execute(
                select(COAttainment)
                .join(CourseOutcome, COAttainment.course_outcome_id == CourseOutcome.id)
                .where(CourseOutcome.course_id == course_id)
            )
            co_attainments = cos_result.scalars().all()
            
            # Get all PO attainments
            pos_result = await session.execute(
                select(POAttainment)
                .where(POAttainment.course_id == course_id)
            )
            po_attainments = pos_result.scalars().all()
            
            report = {
                "course_id": course_id,
                "course_code": course.course_code,
                "course_name": course.course_name,
                "report_generated_at": datetime.utcnow().isoformat(),
                "co_attainments": [
                    {
                        "id": co.id,
                        "percentage": co.attainment_percentage,
                        "level": co.attainment_level,
                        "students": co.total_students
                    }
                    for co in co_attainments
                ],
                "po_attainments": [
                    {
                        "id": po.id,
                        "percentage": po.attainment_percentage,
                        "level": po.attainment_level
                    }
                    for po in po_attainments
                ],
                "summary": {
                    "total_cos": len(co_attainments),
                    "total_pos": len(po_attainments),
                    "avg_co_attainment": round(
                        sum(c.attainment_percentage for c in co_attainments) / len(co_attainments)
                        if co_attainments else 0, 2
                    )
                }
            }
            
            logger.info(f"Comprehensive report generated for course {course_id}")
            return report
        
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return None
