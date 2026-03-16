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


class AttainmentCalculator:
    """
    Production-grade attainment calculation engine.
    NOTE: The primary calculation engine is AttainmentService.
    This class provides supplementary statistics and report utilities.

    NBA-standard level thresholds (read from settings at call time, not import time):
      Level 3 >= 60%, Level 2 >= 50%, Level 1 < 50%
    """

    @staticmethod
    def _thresholds() -> tuple:
        s = get_settings()
        return (
            getattr(s, "attainment_level_3_threshold", 0.60) * 100.0,
            getattr(s, "attainment_level_2_threshold", 0.50) * 100.0,
        )

    @staticmethod
    async def _thresholds_live() -> tuple:
        """Redis override wins over settings for runtime-configurable thresholds."""
        from app.core.infrastructure.redis_client import get_json
        try:
            cached = await get_json("obe:thresholds")
            if cached:
                l3 = cached.get("level3")
                l2 = cached.get("level2")
                if l3 is not None and l2 is not None:
                    return float(l3) * 100.0, float(l2) * 100.0
        except Exception:
            pass
        return AttainmentCalculator._thresholds()

    @staticmethod
    def determine_attainment_level(percentage: float, thresholds: tuple | None = None) -> str:
        """Determine NBA attainment level from percentage."""
        l3, l2 = thresholds if thresholds else AttainmentCalculator._thresholds()
        if percentage >= l3:
            return "Level 3"
        if percentage >= l2:
            return "Level 2"
        return "Level 1"
    
    @staticmethod
    async def calculate_co_attainment_db(
        session: AsyncSession,
        course_outcome_id: str,
        exam_id: str,
        course_id: str,
        threshold_pct: float = 0.40,
    ) -> Optional[Dict[str, Any]]:
        """
        NBA threshold-based CO attainment (matches AttainmentService primary engine).
        Formula:
          threshold_marks = threshold_pct × CO_max_marks
          pass_count = students where CO_obtained >= threshold_marks
          CO_att% = (pass_count / total_students) × 100
        """
        try:
            co_result = await session.execute(
                select(CourseOutcome).where(CourseOutcome.id == course_outcome_id)
            )
            course_outcome = co_result.scalar_one_or_none()
            if not course_outcome:
                logger.error(f"CO not found: {course_outcome_id}")
                return None

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
                    "attainment_level": "Level 1",
                    "threshold_pct": int(threshold_pct * 100),
                }

            question_ids = [q[0] for q in questions_data]
            co_max_marks = sum(float(q[1]) for q in questions_data)
            threshold_marks = threshold_pct * co_max_marks

            # Per-student CO marks
            marks_result = await session.execute(
                select(StudentMarks.student_id, StudentMarks.question_id, StudentMarks.marks_obtained)
                .where(and_(
                    StudentMarks.exam_id == exam_id,
                    StudentMarks.question_id.in_(question_ids)
                ))
            )
            marks_rows = marks_result.all()

            student_totals: Dict[str, float] = {}
            for sid, qid, m in marks_rows:
                student_totals[sid] = student_totals.get(sid, 0.0) + float(m)

            total_students = len(student_totals)
            pass_count = sum(1 for v in student_totals.values() if v >= threshold_marks)
            total_obtained = sum(student_totals.values())

            attainment_percentage = (pass_count / total_students * 100) if total_students > 0 else 0.0
            thresholds = await AttainmentCalculator._thresholds_live()
            attainment_level = AttainmentCalculator.determine_attainment_level(attainment_percentage, thresholds)

            logger.info(
                f"CO attainment (threshold={int(threshold_pct*100)}%): {course_outcome_id}, "
                f"{pass_count}/{total_students} passed → {attainment_percentage:.2f}%"
            )
            return {
                "course_outcome_id": course_outcome_id,
                "exam_id": exam_id,
                "total_students": total_students,
                "students_cleared": pass_count,
                "total_marks": int(co_max_marks),
                "threshold_marks": round(threshold_marks, 2),
                "threshold_pct": int(threshold_pct * 100),
                "marks_obtained": round(total_obtained, 2),
                "attainment_percentage": round(attainment_percentage, 2),
                "attainment_level": attainment_level,
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
        Calculate PO attainment using NBA weighted formula:
        PO_att = Σ(CO_att × mapping_level) / Σ(mapping_level)
        mapping_level: 3(sim>=0.75), 2(sim>=0.50), 1(sim>=0.30)
        """
        try:
            co_map_result = await session.execute(
                select(CourseOutcome.id, co_po_mapping_table.c.similarity_score)
                .join(co_po_mapping_table, CourseOutcome.id == co_po_mapping_table.c.course_outcome_id)
                .where(and_(
                    CourseOutcome.course_id == course_id,
                    co_po_mapping_table.c.program_outcome_id == program_outcome_id
                ))
            )
            co_rows = co_map_result.all()
            if not co_rows:
                return {
                    "program_outcome_id": program_outcome_id,
                    "course_id": course_id,
                    "program_id": program_id,
                    "mapped_co_count": 0,
                    "attainment_percentage": 0.0,
                    "attainment_level": "Level 1",
                }
            co_map = {row[0]: float(row[1] or 0) for row in co_rows}
            attainments_result = await session.execute(
                select(COAttainment.course_outcome_id, COAttainment.attainment_percentage)
                .where(COAttainment.course_outcome_id.in_(list(co_map.keys())))
                .order_by(COAttainment.calculated_at.desc())
            )
            co_att: Dict[str, float] = {}
            for row in attainments_result.all():
                if row[0] not in co_att:
                    co_att[row[0]] = float(row[1] or 0)
            num = den = 0.0
            for co_id, sim in co_map.items():
                if co_id not in co_att:
                    continue
                level = 3 if sim >= 0.75 else (2 if sim >= 0.50 else (1 if sim >= 0.30 else 0))
                if level == 0:
                    continue
                num += level * co_att[co_id]
                den += level
            po_pct = (num / den) if den > 0 else 0.0
            thresholds = await AttainmentCalculator._thresholds_live()
            attainment_level = AttainmentCalculator.determine_attainment_level(po_pct, thresholds)
            return {
                "program_outcome_id": program_outcome_id,
                "course_id": course_id,
                "program_id": program_id,
                "mapped_co_count": len(co_att),
                "attainment_percentage": round(po_pct, 2),
                "attainment_level": attainment_level,
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
        """Calculate PSO attainment using same NBA weighted formula as PO.
        PSO_att = Σ(CO_att × mapping_level) / Σ(mapping_level)
        """
        try:
            co_map_result = await session.execute(
                select(CourseOutcome.id, co_pso_mapping_table.c.similarity_score)
                .join(co_pso_mapping_table, CourseOutcome.id == co_pso_mapping_table.c.course_outcome_id)
                .where(and_(
                    CourseOutcome.course_id == course_id,
                    co_pso_mapping_table.c.program_specific_outcome_id == pso_id
                ))
            )
            co_rows = co_map_result.all()
            if not co_rows:
                return {
                    "pso_id": pso_id,
                    "course_id": course_id,
                    "program_id": program_id,
                    "mapped_co_count": 0,
                    "attainment_percentage": 0.0,
                    "attainment_level": "Level 1",
                }
            co_map = {row[0]: float(row[1] or 0) for row in co_rows}
            attainments_result = await session.execute(
                select(COAttainment.course_outcome_id, COAttainment.attainment_percentage)
                .where(COAttainment.course_outcome_id.in_(list(co_map.keys())))
                .order_by(COAttainment.calculated_at.desc())
            )
            co_att: Dict[str, float] = {}
            for row in attainments_result.all():
                if row[0] not in co_att:
                    co_att[row[0]] = float(row[1] or 0)
            num = den = 0.0
            for co_id, sim in co_map.items():
                if co_id not in co_att:
                    continue
                level = 3 if sim >= 0.75 else (2 if sim >= 0.50 else (1 if sim >= 0.30 else 0))
                if level == 0:
                    continue
                num += level * co_att[co_id]
                den += level
            pso_pct = (num / den) if den > 0 else 0.0
            thresholds = await AttainmentCalculator._thresholds_live()
            attainment_level = AttainmentCalculator.determine_attainment_level(pso_pct, thresholds)
            return {
                "pso_id": pso_id,
                "course_id": course_id,
                "program_id": program_id,
                "mapped_co_count": len(co_att),
                "attainment_percentage": round(pso_pct, 2),
                "attainment_level": attainment_level,
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
