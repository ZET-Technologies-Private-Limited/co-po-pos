"""
Attainment Service – Full OBE Framework Implementation
=======================================================

ALGORITHMS:
-----------
1. CO Attainment (per exam) – THRESHOLD-BASED (OBE standard):
   Threshold = threshold_pct x (total marks of CO-linked questions)  [default 60%]
   CO_att = (students_cleared / total_students) x 100

2. CO Attainment (course-level, weighted):
   CO_att_course = sum(exam_weight_i x CO_att_i) / sum(exam_weights)
   Weights: end_term=60, mid_term=20, T1-T5=5 each, assignment=5, practical=15

3. PO Attainment:
   PO_att = sum(CO_att x mapping_level) / sum(mapping_level)
   mapping_level: 3(>=0.75), 2(>=0.50), 1(>=0.30)

4. PSO Attainment - same formula via co_pso_mapping.

5. Level thresholds: Level3>=70, Level2>=60, Level1<60
"""
from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import func, and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.models import (
    Course, CourseOutcome, ExamQuestion, StudentMarks,
    COAttainment, POAttainment, ProgramOutcome, ProgramSpecificOutcome,
    Exam, Report,
    co_po_mapping_table, co_pso_mapping_table, question_co_mapping_table,
)
from app.modules.repositories.base_repository import BaseRepository
from app.core.logging.system_logger import SystemLogger
from app.communication.events.event_bus import event_bus, EventType, SystemEvent
from app.core.config.settings import get_settings
logger = SystemLogger("attainment_service")


def _level_thresholds() -> tuple:
    """Level thresholds from settings (dynamic, configurable per deployment)."""
    s = get_settings()
    return (
        getattr(s, "attainment_level_3_threshold", 0.70) * 100.0,
        getattr(s, "attainment_level_2_threshold", 0.60) * 100.0,
    )


def _level(pct: float) -> str:
    l3, l2 = _level_thresholds()
    if pct >= l3:
        return "Level 3"
    if pct >= l2:
        return "Level 2"
    return "Level 1"


_DEFAULT_THRESHOLD = 0.60

_EXAM_WEIGHTS: Dict[str, float] = {
    "end_term": 60.0, "mid_term": 20.0,
    "t1": 5.0, "t2": 5.0, "t3": 5.0, "t4": 5.0, "t5": 5.0,
    "practical": 15.0, "assignment": 5.0, "quiz": 5.0,
}

def _grade(pct: float) -> str:
    if pct >= 90: return "O"
    if pct >= 80: return "A+"
    if pct >= 75: return "A"
    if pct >= 70: return "B+"
    if pct >= 60: return "B"
    if pct >= 50: return "C"
    if pct >= 40: return "D"
    return "F"

def _chart_color(level: str) -> str:
    return {"Level 3": "#27AE60", "Level 2": "#F39C12", "Level 1": "#E74C3C"}.get(level, "#95A5A6")

def _exam_type_key(exam: Exam) -> str:
    raw = str(exam.exam_type.value if hasattr(exam.exam_type, "value") else exam.exam_type)
    return raw.lower().replace("-", "_").replace(" ", "_")

class AttainmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.co_attainment_repo = BaseRepository(COAttainment)
        self.po_attainment_repo = BaseRepository(POAttainment)
        self.report_repo = BaseRepository(Report)

    async def calculate_course_outcome_attainments(self, course_id: str, exam_id: str, threshold_pct: float = _DEFAULT_THRESHOLD) -> List[Dict[str, Any]]:
        cos_result = await self.session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course_id))
        cos = list(cos_result.scalars().all())
        if not cos: return []
        all_q_result = await self.session.execute(select(ExamQuestion.id, ExamQuestion.marks).where(ExamQuestion.exam_id == exam_id))
        all_questions = {row[0]: row[1] for row in all_q_result.all()}
        all_marks_result = await self.session.execute(select(StudentMarks.student_id, StudentMarks.question_id, StudentMarks.marks_obtained).where(StudentMarks.exam_id == exam_id))
        marks_by_student: Dict[str, Dict[str, float]] = {}
        for row in all_marks_result.all():
            marks_by_student.setdefault(row[0], {})[row[1]] = float(row[2])
        total_students = len(marks_by_student)
        attainments: List[Dict] = []
        for co in cos:
            q_map_result = await self.session.execute(select(question_co_mapping_table.c.question_id).where(question_co_mapping_table.c.course_outcome_id == co.id))
            co_q_ids = [r[0] for r in q_map_result.all() if r[0] in all_questions]
            if not co_q_ids: continue
            max_marks_co = sum(all_questions[qid] for qid in co_q_ids)
            threshold_marks = threshold_pct * max_marks_co
            students_cleared = 0
            student_scores: List[float] = []
            for sid, q_marks in marks_by_student.items():
                obtained = sum(q_marks.get(qid, 0.0) for qid in co_q_ids)
                student_scores.append(obtained)
                if obtained >= threshold_marks: students_cleared += 1
            total_obtained = sum(student_scores)
            att_pct = (students_cleared / total_students * 100) if total_students > 0 else 0.0
            avg_marks_pct = (total_obtained / (max_marks_co * total_students) * 100) if max_marks_co > 0 and total_students > 0 else 0.0
            existing = await self.session.execute(select(COAttainment).where(and_(COAttainment.course_outcome_id == co.id, COAttainment.exam_id == exam_id)))
            row = existing.scalar_one_or_none()
            if row:
                row.total_students = total_students; row.total_marks = int(max_marks_co)
                row.marks_obtained = Decimal(str(round(total_obtained, 4)))
                row.attainment_percentage = round(att_pct, 2); row.attainment_level = _level(att_pct)
                row.calculated_at = datetime.utcnow()
            else:
                row = COAttainment(id=str(uuid.uuid4()), course_outcome_id=co.id, exam_id=exam_id, total_students=total_students, total_marks=int(max_marks_co), marks_obtained=Decimal(str(round(total_obtained, 4))), attainment_percentage=round(att_pct, 2), attainment_level=_level(att_pct), calculated_at=datetime.utcnow())
                self.session.add(row)
            attainments.append({"co_id": co.id, "co_code": co.code, "co_statement": co.statement, "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level), "total_students": total_students, "students_cleared_threshold": students_cleared, "threshold_pct": int(threshold_pct * 100), "threshold_marks": round(threshold_marks, 2), "max_marks_co": int(max_marks_co), "total_obtained": round(total_obtained, 2), "attainment_percentage": round(att_pct, 2), "avg_marks_percentage": round(avg_marks_pct, 2), "attainment_level": _level(att_pct)})
        await self.session.commit()
        await event_bus.publish(SystemEvent(
            event_type=EventType.ATTAINMENT_CALCULATED,
            timestamp=datetime.utcnow(),
            source_module="attainment_service",
            data={
                "course_id": course_id,
                "exam_id": exam_id,
                "co_attainment_count": len(attainments),
                "threshold_pct": threshold_pct,
            },
        ))
        logger.info(f"CO attainments (threshold={int(threshold_pct*100)}%): {len(attainments)} COs")
        return attainments

    async def calculate_weighted_co_attainments(self, course_id: str, threshold_pct: float = _DEFAULT_THRESHOLD) -> List[Dict[str, Any]]:
        exams_result = await self.session.execute(select(Exam).where(Exam.course_id == course_id))
        exams = list(exams_result.scalars().all())
        cos_result = await self.session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course_id))
        cos = list(cos_result.scalars().all())
        results: List[Dict] = []
        for co in cos:
            weighted_sum = weight_total = 0.0
            per_exam: List[Dict] = []
            for exam in exams:
                stored = await self._get_stored_co_attainment(co.id, exam.id)
                pct = stored.get("attainment_percentage") if stored else None
                if pct is None:
                    fresh = await self.calculate_course_outcome_attainments(course_id, exam.id, threshold_pct)
                    found = next((a for a in fresh if a["co_id"] == co.id), None)
                    if not found: continue
                    pct = found["attainment_percentage"]
                etype = _exam_type_key(exam); w = _EXAM_WEIGHTS.get(etype, 10.0)
                weighted_sum += w * pct; weight_total += w
                per_exam.append({"exam_id": exam.id, "exam_name": exam.exam_name, "exam_type": etype, "weight": w, "attainment": round(pct, 2), "level": _level(pct)})
            weighted_pct = (weighted_sum / weight_total) if weight_total > 0 else 0.0
            results.append({"co_id": co.id, "co_code": co.code, "co_statement": co.statement, "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level), "weighted_attainment_percentage": round(weighted_pct, 2), "attainment_level": _level(weighted_pct), "per_exam": per_exam})
        return results

    async def calculate_program_outcome_attainments(self, course_id: str, program_id: str) -> List[Dict[str, Any]]:
        pos_result = await self.session.execute(select(ProgramOutcome).where(ProgramOutcome.program == program_id))
        pos = list(pos_result.scalars().all())
        attainments: List[Dict] = []
        for po in pos:
            co_map_result = await self.session.execute(select(CourseOutcome.id, CourseOutcome.code, co_po_mapping_table.c.similarity_score).join(co_po_mapping_table, CourseOutcome.id == co_po_mapping_table.c.course_outcome_id).where(and_(CourseOutcome.course_id == course_id, co_po_mapping_table.c.program_outcome_id == po.id)))
            co_rows = co_map_result.all()
            if not co_rows: continue
            co_map = {row[0]: {"code": row[1], "sim": float(row[2] or 0)} for row in co_rows}
            co_att_result = await self.session.execute(select(COAttainment.course_outcome_id, COAttainment.attainment_percentage).where(COAttainment.course_outcome_id.in_(list(co_map.keys()))).order_by(COAttainment.calculated_at.desc()))
            co_att: Dict[str, float] = {}
            for att_row in co_att_result.all():
                if att_row[0] not in co_att: co_att[att_row[0]] = float(att_row[1] or 0)
            if not co_att: continue
            num = den = 0.0; co_details = []
            for co_id, co_info in co_map.items():
                if co_id not in co_att: continue
                sim = co_info["sim"]; level = 3 if sim >= 0.75 else (2 if sim >= 0.50 else (1 if sim >= 0.30 else 0))
                if level == 0: continue
                pct = co_att[co_id]; num += level * pct; den += level
                co_details.append({"co_id": co_id, "co_code": co_info["code"], "co_attainment": round(pct, 2), "mapping_level": level, "similarity_score": round(sim, 4)})
            po_pct = (num / den) if den > 0 else 0.0
            existing = await self.session.execute(select(POAttainment).where(and_(POAttainment.program_outcome_id == po.id, POAttainment.course_id == course_id)))
            row = existing.scalar_one_or_none()
            if row:
                row.attainment_percentage = po_pct; row.attainment_level = _level(po_pct)
                row.co_count = len(co_att); row.calculated_at = datetime.utcnow()
            else:
                row = POAttainment(id=str(uuid.uuid4()), program_outcome_id=po.id, course_id=course_id, attainment_percentage=po_pct, attainment_level=_level(po_pct), co_count=len(co_att), calculated_at=datetime.utcnow())
                self.session.add(row)
            attainments.append({"po_id": po.id, "po_code": po.code, "po_statement": po.statement, "attainment_percentage": round(po_pct, 2), "attainment_level": _level(po_pct), "mapped_cos": len(co_att), "co_details": co_details})
        await self.session.commit()
        return attainments

    async def calculate_pso_attainments(self, course_id: str, program_id: str) -> List[Dict[str, Any]]:
        psos_result = await self.session.execute(select(ProgramSpecificOutcome).where(ProgramSpecificOutcome.program == program_id))
        psos = list(psos_result.scalars().all())
        attainments: List[Dict] = []
        for pso in psos:
            co_map_result = await self.session.execute(select(CourseOutcome.id, CourseOutcome.code, co_pso_mapping_table.c.similarity_score).join(co_pso_mapping_table, CourseOutcome.id == co_pso_mapping_table.c.course_outcome_id).where(and_(CourseOutcome.course_id == course_id, co_pso_mapping_table.c.program_specific_outcome_id == pso.id)))
            co_rows = co_map_result.all()
            if not co_rows: continue
            co_map = {row[0]: {"code": row[1], "sim": float(row[2] or 0)} for row in co_rows}
            co_att_result = await self.session.execute(select(COAttainment.course_outcome_id, COAttainment.attainment_percentage).where(COAttainment.course_outcome_id.in_(list(co_map.keys()))).order_by(COAttainment.calculated_at.desc()))
            co_att: Dict[str, float] = {}
            for att_row in co_att_result.all():
                if att_row[0] not in co_att: co_att[att_row[0]] = float(att_row[1] or 0)
            if not co_att: continue
            num = den = 0.0
            for co_id, co_info in co_map.items():
                if co_id not in co_att: continue
                sim = co_info["sim"]; level = 3 if sim >= 0.75 else (2 if sim >= 0.50 else (1 if sim >= 0.30 else 0))
                if level == 0: continue
                num += level * co_att[co_id]; den += level
            pso_pct = (num / den) if den > 0 else 0.0
            attainments.append({"pso_id": pso.id, "pso_code": pso.code, "pso_statement": pso.statement, "attainment_percentage": round(pso_pct, 2), "attainment_level": _level(pso_pct), "mapped_cos": len(co_att)})
        return attainments

    async def run_full_attainment_pipeline(self, course_id: str, program_id: str, threshold_pct: float = _DEFAULT_THRESHOLD) -> Dict[str, Any]:
        exams_result = await self.session.execute(select(Exam).where(Exam.course_id == course_id))
        exams = list(exams_result.scalars().all())
        co_per_exam = []
        for exam in exams:
            att = await self.calculate_course_outcome_attainments(course_id, exam.id, threshold_pct)
            co_per_exam.append({"exam_id": exam.id, "exam_name": exam.exam_name, "exam_type": _exam_type_key(exam), "co_attainments": att})
        weighted_cos = await self.calculate_weighted_co_attainments(course_id, threshold_pct)
        po_atts = await self.calculate_program_outcome_attainments(course_id, program_id)
        pso_atts = await self.calculate_pso_attainments(course_id, program_id)
        matrix = await self.get_co_po_matrix(course_id)
        avg_co = sum(c["weighted_attainment_percentage"] for c in weighted_cos) / max(len(weighted_cos), 1)
        avg_po = sum(p["attainment_percentage"] for p in po_atts) / max(len(po_atts), 1)
        avg_pso = sum(p["attainment_percentage"] for p in pso_atts) / max(len(pso_atts), 1)
        return {"course_id": course_id, "program_id": program_id, "threshold_pct": int(threshold_pct * 100), "co_per_exam": co_per_exam, "weighted_co_attainments": weighted_cos, "po_attainments": po_atts, "pso_attainments": pso_atts, "co_po_matrix": matrix, "summary": {"average_co_attainment": round(avg_co, 2), "average_po_attainment": round(avg_po, 2), "average_pso_attainment": round(avg_pso, 2), "overall_level": _level(avg_co), "total_cos": len(weighted_cos), "total_pos": len(po_atts), "total_psos": len(pso_atts)}}

    async def get_co_po_matrix(self, course_id: str) -> Dict[str, Any]:
        cos_result = await self.session.execute(select(CourseOutcome.id, CourseOutcome.code).where(CourseOutcome.course_id == course_id))
        cos = list(cos_result.all())
        mapping_result = await self.session.execute(select(ProgramOutcome.id, ProgramOutcome.code, CourseOutcome.id.label("co_id"), co_po_mapping_table.c.similarity_score).join(co_po_mapping_table, ProgramOutcome.id == co_po_mapping_table.c.program_outcome_id).join(CourseOutcome, CourseOutcome.id == co_po_mapping_table.c.course_outcome_id).where(CourseOutcome.course_id == course_id))
        po_rows = list(mapping_result.all())
        co_id_to_code = {c[0]: c[1] for c in cos}
        po_order: Dict[str, str] = {}
        for row in po_rows: po_order.setdefault(row[1], row[0])
        co_codes = [c[1] for c in cos]; po_codes = list(po_order.keys())
        cell: Dict[str, Dict[str, int]] = {cc: {pc: 0 for pc in po_codes} for cc in co_codes}
        for row in po_rows:
            co_code = co_id_to_code.get(row[2], ""); po_code = row[1]
            sim = float(row[3] or 0.0); lvl = 3 if sim >= 0.75 else (2 if sim >= 0.50 else (1 if sim >= 0.30 else 0))
            if co_code and po_code: cell[co_code][po_code] = max(cell[co_code].get(po_code, 0), lvl)
        row_sums = {cc: sum(cell[cc].values()) for cc in co_codes}
        return {"cos": co_codes, "pos": po_codes, "data": cell, "row_sums": row_sums}

    async def get_student_performance(self, course_id: str, exam_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if exam_id: exam_ids = [exam_id]
        else:
            exams_r = await self.session.execute(select(Exam.id).where(Exam.course_id == course_id))
            exam_ids = [r[0] for r in exams_r.all()]
        if not exam_ids: return []
        q_result = await self.session.execute(select(ExamQuestion.id, ExamQuestion.marks, ExamQuestion.exam_id).where(ExamQuestion.exam_id.in_(exam_ids)))
        questions = {r[0]: {"max_marks": r[1], "exam_id": r[2]} for r in q_result.all()}
        total_max = sum(v["max_marks"] for v in questions.values())
        marks_result = await self.session.execute(select(StudentMarks.student_id, StudentMarks.question_id, StudentMarks.marks_obtained).where(StudentMarks.question_id.in_(list(questions.keys()))))
        student_marks: Dict[str, Dict[str, float]] = {}; student_totals: Dict[str, float] = {}
        for row in marks_result.all():
            sid, qid, m = row[0], row[1], float(row[2])
            student_marks.setdefault(sid, {})[qid] = m
            student_totals[sid] = student_totals.get(sid, 0.0) + m
        cos_result = await self.session.execute(select(CourseOutcome.id, CourseOutcome.code).where(CourseOutcome.course_id == course_id))
        cos_list = list(cos_result.all())
        co_q_map: Dict[str, List[str]] = {}
        for co_id, _ in cos_list:
            qco_r = await self.session.execute(select(question_co_mapping_table.c.question_id).where(question_co_mapping_table.c.course_outcome_id == co_id))
            co_q_map[co_id] = [r[0] for r in qco_r.all()]
        performance: List[Dict] = []
        for sid, total in student_totals.items():
            co_details: Dict[str, Any] = {}
            for co_id, co_code in cos_list:
                q_ids = [qid for qid in co_q_map.get(co_id, []) if qid in questions]
                co_max = sum(questions[qid]["max_marks"] for qid in q_ids)
                co_obtained = sum(student_marks[sid].get(qid, 0) for qid in q_ids)
                co_pct = (co_obtained / co_max * 100) if co_max > 0 else 0.0
                co_details[co_code] = {"obtained": round(co_obtained, 2), "max": int(co_max), "percent": round(co_pct, 1), "level": _level(co_pct)}
            overall_pct = (total / total_max * 100) if total_max > 0 else 0.0
            performance.append({"student_id": sid, "total_marks": round(total, 2), "max_marks": total_max, "percentage": round(overall_pct, 2), "grade": _grade(overall_pct), "co_breakdown": co_details})
        performance.sort(key=lambda x: x["percentage"], reverse=True)
        return performance

    async def get_visualization_data(self, course_id: str) -> Dict[str, Any]:
        summary = await self.get_course_attainment_summary(course_id)
        co_data = summary.get("co_attainments", []); po_data = summary.get("po_attainments", [])
        level3_pct, level2_pct = _level_thresholds()
        co_chart = {
            "labels": [c.get("co_code", "") for c in co_data],
            "values": [c.get("percentage", 0) for c in co_data],
            "colors": [_chart_color(c.get("level", "")) for c in co_data],
            "thresholds": {"level3": level3_pct, "level2": level2_pct},
        }
        po_chart = {"labels": [p.get("po_code", "") for p in po_data], "values": [p.get("percentage", 0) for p in po_data], "colors": [_chart_color(p.get("level", "")) for p in po_data]}
        bloom_result = await self.session.execute(select(ExamQuestion.bloom_level, func.count().label("cnt")).join(Exam, ExamQuestion.exam_id == Exam.id).where(Exam.course_id == course_id).group_by(ExamQuestion.bloom_level))
        bloom_dist = {str(r[0].value if hasattr(r[0], "value") else r[0]): r[1] for r in bloom_result.all()}
        students = await self.get_student_performance(course_id)
        grade_dist: Dict[str, int] = {}
        for s in students: g = s["grade"]; grade_dist[g] = grade_dist.get(g, 0) + 1
        return {"course_id": course_id, "co_attainment_chart": co_chart, "po_attainment_chart": po_chart, "bloom_distribution": bloom_dist, "grade_distribution": grade_dist, "summary": {"avg_co": summary.get("average_co_attainment", 0), "avg_po": summary.get("average_po_attainment", 0), "overall_level": summary.get("overall_level", "Level 1"), "total_cos": len(co_data), "total_pos": len(po_data), "total_students": len(students)}}

    async def get_course_attainment_summary(self, course_id: str) -> Dict[str, Any]:
        co_result = await self.session.execute(select(COAttainment, CourseOutcome.code, CourseOutcome.statement).join(CourseOutcome, COAttainment.course_outcome_id == CourseOutcome.id).where(CourseOutcome.course_id == course_id).order_by(COAttainment.calculated_at.desc()))
        seen_co: Set[str] = set(); co_rows: List[Dict] = []
        for row in co_result.all():
            co_att, co_code, co_stmt = row
            if co_att.course_outcome_id not in seen_co:
                seen_co.add(co_att.course_outcome_id)
                co_rows.append({"id": co_att.id, "co_id": co_att.course_outcome_id, "co_code": co_code, "statement": co_stmt, "percentage": float(co_att.attainment_percentage or 0), "level": co_att.attainment_level, "students": co_att.total_students, "total_marks": co_att.total_marks, "marks_obtained": float(co_att.marks_obtained or 0)})
        po_result = await self.session.execute(select(POAttainment, ProgramOutcome.code, ProgramOutcome.statement).join(ProgramOutcome, POAttainment.program_outcome_id == ProgramOutcome.id).where(POAttainment.course_id == course_id).order_by(POAttainment.calculated_at.desc()))
        seen_po: Set[str] = set(); po_rows: List[Dict] = []
        for row in po_result.all():
            po_att, po_code, po_stmt = row
            if po_att.program_outcome_id not in seen_po:
                seen_po.add(po_att.program_outcome_id)
                po_rows.append({"id": po_att.id, "po_id": po_att.program_outcome_id, "po_code": po_code, "statement": po_stmt, "percentage": float(po_att.attainment_percentage or 0), "level": po_att.attainment_level})
        avg_co = sum(r["percentage"] for r in co_rows) / max(len(co_rows), 1)
        avg_po = sum(r["percentage"] for r in po_rows) / max(len(po_rows), 1)
        return {"course_id": course_id, "co_attainments": co_rows, "po_attainments": po_rows, "average_co_attainment": round(avg_co, 2), "average_po_attainment": round(avg_po, 2), "overall_level": _level(avg_co)}

    async def generate_report(self, course_id: str, report_type: str, user_id: str) -> Report:
        summary = await self.get_course_attainment_summary(course_id)
        matrix  = await self.get_co_po_matrix(course_id)
        summary["co_po_matrix"] = matrix
        
        report_data = {
            'report_type': report_type,
            'title': f"{report_type.replace('_',' ').title()} Report - Course {course_id}",
            'course_id': course_id,
            'generated_by': user_id,
            'data': summary,
            'file_format': "json"
        }
        
        report = await self.report_repo.create(self.session, **report_data)
        await self.session.commit()
        logger.info(f"Report generated: {report.id}")
        return report
    
    # ==================== ENHANCED CRUD OPERATIONS ====================
    
    async def create_co_attainment(self, **data) -> COAttainment:
        """Create CO attainment record"""
        attainment = await self.co_attainment_repo.create(self.session, **data)
        await self.session.commit()
        logger.info(f"CO attainment created: {attainment.id}")
        return attainment
    
    async def get_co_attainment(self, attainment_id: str) -> Optional[COAttainment]:
        """Get CO attainment by ID"""
        return await self.co_attainment_repo.get_by_id(self.session, attainment_id)
    
    async def update_co_attainment(self, attainment_id: str, **data) -> Optional[COAttainment]:
        """Update CO attainment"""
        attainment = await self.co_attainment_repo.update(self.session, attainment_id, **data)
        await self.session.commit()
        logger.info(f"CO attainment updated: {attainment_id}")
        return attainment
    
    async def delete_co_attainment(self, attainment_id: str) -> bool:
        """Delete CO attainment"""
        deleted = await self.co_attainment_repo.delete(self.session, attainment_id)
        await self.session.commit()
        logger.info(f"CO attainment deleted: {attainment_id}")
        return deleted
    
    async def list_co_attainments(self, course_id: str, skip: int = 0, limit: int = 100) -> List[COAttainment]:
        """List CO attainments for a course"""
        stmt = select(COAttainment).join(CourseOutcome).where(
            CourseOutcome.course_id == course_id
        ).offset(skip).limit(limit).order_by(COAttainment.calculated_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_po_attainment(self, **data) -> POAttainment:
        """Create PO attainment record"""
        attainment = await self.po_attainment_repo.create(self.session, **data)
        await self.session.commit()
        logger.info(f"PO attainment created: {attainment.id}")
        return attainment
    
    async def get_po_attainment(self, attainment_id: str) -> Optional[POAttainment]:
        """Get PO attainment by ID"""
        return await self.po_attainment_repo.get_by_id(self.session, attainment_id)
    
    async def update_po_attainment(self, attainment_id: str, **data) -> Optional[POAttainment]:
        """Update PO attainment"""
        attainment = await self.po_attainment_repo.update(self.session, attainment_id, **data)
        await self.session.commit()
        logger.info(f"PO attainment updated: {attainment_id}")
        return attainment
    
    async def delete_po_attainment(self, attainment_id: str) -> bool:
        """Delete PO attainment"""
        deleted = await self.po_attainment_repo.delete(self.session, attainment_id)
        await self.session.commit()
        logger.info(f"PO attainment deleted: {attainment_id}")
        return deleted
    
    async def list_po_attainments(self, course_id: str, skip: int = 0, limit: int = 100) -> List[POAttainment]:
        """List PO attainments for a course"""
        stmt = select(POAttainment).where(
            POAttainment.course_id == course_id
        ).offset(skip).limit(limit).order_by(POAttainment.calculated_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_report(self, report_id: str) -> Optional[Report]:
        """Get report by ID"""
        return await self.report_repo.get_by_id(self.session, report_id)
    
    async def update_report(self, report_id: str, **data) -> Optional[Report]:
        """Update report"""
        report = await self.report_repo.update(self.session, report_id, **data)
        await self.session.commit()
        logger.info(f"Report updated: {report_id}")
        return report
    
    async def delete_report(self, report_id: str) -> bool:
        """Delete report"""
        deleted = await self.report_repo.delete(self.session, report_id)
        await self.session.commit()
        logger.info(f"Report deleted: {report_id}")
        return deleted
    
    async def list_reports(self, course_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Report]:
        """List reports with optional course filter"""
        stmt = select(Report).offset(skip).limit(limit).order_by(Report.generated_at.desc())
        
        if course_id:
            stmt = stmt.where(Report.course_id == course_id)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def count_attainments(self, course_id: str, attainment_type: str = "co") -> int:
        """Count attainments for a course"""
        if attainment_type == "co":
            stmt = select(func.count()).select_from(COAttainment).join(CourseOutcome).where(
                CourseOutcome.course_id == course_id
            )
        else:
            stmt = select(func.count()).select_from(POAttainment).where(
                POAttainment.course_id == course_id
            )
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_latest_attainments(self, course_id: str, limit: int = 10) -> Dict[str, List[Dict]]:
        """Get latest CO and PO attainments for a course"""
        # Latest CO attainments
        co_stmt = select(COAttainment, CourseOutcome.code).join(
            CourseOutcome, COAttainment.course_outcome_id == CourseOutcome.id
        ).where(
            CourseOutcome.course_id == course_id
        ).order_by(COAttainment.calculated_at.desc()).limit(limit)
        
        co_result = await self.session.execute(co_stmt)
        co_attainments = [
            {
                "id": row[0].id,
                "co_code": row[1],
                "percentage": float(row[0].attainment_percentage or 0),
                "level": row[0].attainment_level,
                "calculated_at": row[0].calculated_at
            }
            for row in co_result.all()
        ]
        
        # Latest PO attainments
        po_stmt = select(POAttainment, ProgramOutcome.code).join(
            ProgramOutcome, POAttainment.program_outcome_id == ProgramOutcome.id
        ).where(
            POAttainment.course_id == course_id
        ).order_by(POAttainment.calculated_at.desc()).limit(limit)
        
        po_result = await self.session.execute(po_stmt)
        po_attainments = [
            {
                "id": row[0].id,
                "po_code": row[1],
                "percentage": float(row[0].attainment_percentage or 0),
                "level": row[0].attainment_level,
                "calculated_at": row[0].calculated_at
            }
            for row in po_result.all()
        ]
        
        return {
            "co_attainments": co_attainments,
            "po_attainments": po_attainments
        }

    async def _get_stored_co_attainment(self, co_id: str, exam_id: str) -> Optional[Dict]:
        result = await self.session.execute(select(COAttainment).where(and_(COAttainment.course_outcome_id == co_id, COAttainment.exam_id == exam_id)))
        row = result.scalar_one_or_none()
        if row: return {"attainment_percentage": float(row.attainment_percentage or 0), "attainment_level": row.attainment_level}
        return None
