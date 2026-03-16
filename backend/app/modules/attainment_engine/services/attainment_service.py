"""
Attainment Service – Full NBA-Compliant OBE Framework
======================================================

ALGORITHMS (NBA standard):
-----------
1. CO Attainment (per exam) – THRESHOLD-BASED:
   threshold_marks = threshold_pct × max_marks_of_CO_questions  [default 60%]
   CO_att = (students_cleared / total_students) × 100

2. CO Attainment (course-level, weighted) with Best-N-of-M FA rule:
   FA exams (T1-T5): take best N of M scores per CO before weighting
   CO_att_course = Σ(weight_i × CO_att_i) / Σ(weight_i)
   Weights: end_term=60, mid_term=20, T1-T5=5 each, assignment=5, practical=15

3. Direct/Indirect CO Attainment blend (NBA 80/20):
   Final_CO_att = (Direct_CO_att × 0.80) + (Indirect_CO_att × 0.20)
   Indirect comes from survey data stored in Redis key: survey:{course_id}:{co_id}

4. PO Attainment (weighted by mapping level):
   PO_att = Σ(CO_att × mapping_level) / Σ(mapping_level)
   mapping_level: 3(sim>=0.75), 2(sim>=0.50), 1(sim>=0.30)

5. PSO Attainment – same formula via co_pso_mapping.

6. Level thresholds (NBA standard): Level3>=60%, Level2>=50%, Level1<50%

7. Gap Analysis: achieved_level vs co_target_level (configurable, default=2)
"""
from __future__ import annotations
import re
import uuid
from datetime import datetime
from decimal import Decimal
from difflib import SequenceMatcher
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
from app.core.infrastructure.redis_client import get_json
logger = SystemLogger("attainment_service")


def _norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _text_tokens(value: str) -> Set[str]:
    return set(re.findall(r"\b[a-z]{4,}\b", _norm_text(value)))


def _level_thresholds() -> tuple:
    """NBA-standard level thresholds from settings (configurable per deployment)."""
    s = get_settings()
    return (
        getattr(s, "attainment_level_3_threshold", 0.60) * 100.0,  # default 60%
        getattr(s, "attainment_level_2_threshold", 0.50) * 100.0,  # default 50%
    )


async def _level_thresholds_live() -> tuple:
    """Level thresholds — Redis override wins over settings (admin-configurable at runtime)."""
    try:
        cached = await get_json("obe:thresholds")
        if cached:
            l3 = cached.get("level3")
            l2 = cached.get("level2")
            if l3 is not None and l2 is not None:
                return float(l3) * 100.0, float(l2) * 100.0
    except Exception:
        pass
    return _level_thresholds()


def _level(pct: float, thresholds: tuple | None = None) -> str:
    l3, l2 = thresholds if thresholds else _level_thresholds()
    if pct >= l3:
        return "Level 3"
    if pct >= l2:
        return "Level 2"
    return "Level 1"


def _target_met(achieved_level: str, target_level: int) -> bool:
    """Return True if achieved level number >= target level number."""
    level_num = {"Level 1": 1, "Level 2": 2, "Level 3": 3}
    return level_num.get(achieved_level, 1) >= target_level


_DEFAULT_THRESHOLD = 0.40  # NBA default: 40% pass threshold

# NBA-standard exam weights
_EXAM_WEIGHTS: Dict[str, float] = {
    "end_term": 60.0, "mid_term": 20.0,
    "t1": 5.0, "t2": 5.0, "t3": 5.0, "t4": 5.0, "t5": 5.0,
    "practical": 15.0, "assignment": 5.0, "quiz": 5.0,
}

# SA exam types — everything else is FA
_SA_KEYS = {"end_term", "see", "semester_end", "semester_end_exam", "semester_exam",
            "final", "final_exam", "university_exam", "ese", "sa", "summative", "external"}

# FA exam keys — all non-SA types including mid_term, t1-t5, practical, assignment
_FA_KEYS = {"t1", "t2", "t3", "t4", "t5", "mid_term", "midterm", "internal",
            "internal_exam", "sessional", "cie", "fa", "formative",
            "assignment", "quiz", "practical", "lab", "lab_exam",
            "class_test", "unit_test"}

def _is_fa_exam(etype: str) -> bool:
    return etype not in _SA_KEYS

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

    def _resolve_co_refs(self, refs: Any, co_by_id: Dict[str, str], co_by_code: Dict[str, str]) -> List[str]:
        if refs is None:
            return []
        raw_refs: List[str] = []
        if isinstance(refs, (list, tuple, set)):
            for item in refs:
                if isinstance(item, dict):
                    for key in ("co_id", "co_code", "id", "code", "co"):
                        val = item.get(key)
                        if val is not None and str(val).strip():
                            raw_refs.append(str(val).strip())
                elif str(item).strip():
                    raw_refs.append(str(item).strip())
        elif isinstance(refs, str) and refs.strip():
            raw_refs.extend(part.strip() for part in refs.split(",") if part.strip())

        resolved: List[str] = []
        seen: Set[str] = set()
        for ref in raw_refs:
            normalized_ref = ref.replace(" ", "").replace("-", "").replace("_", "")
            co_id = co_by_id.get(ref) or co_by_id.get(normalized_ref) or co_by_code.get(ref.upper()) or co_by_code.get(normalized_ref.upper())
            if co_id and co_id not in seen:
                seen.add(co_id)
                resolved.append(co_id)
        return resolved

    def _infer_best_co_id(self, question_text: str, cos: List[Dict[str, str]]) -> Optional[str]:
        q_norm = _norm_text(question_text)
        q_tokens = _text_tokens(question_text)
        if not q_norm:
            return None
        if len(cos) == 1:
            return cos[0]["id"]

        best_id: Optional[str] = None
        best_score = 0.0
        for co in cos:
            stmt = co["statement"]
            co_tokens = _text_tokens(stmt)
            union = len(q_tokens | co_tokens) or 1
            overlap_score = len(q_tokens & co_tokens) / union
            seq_score = SequenceMatcher(None, q_norm, _norm_text(stmt)).ratio()
            score = overlap_score * 0.7 + seq_score * 0.3
            if score > best_score:
                best_score = score
                best_id = co["id"]

        if best_score >= 0.05:
            return best_id
        if best_id:
            return best_id
        if cos:
            return cos[0]["id"]
        return None

    async def _build_question_to_co_map(self, course_id: str, question_rows: Dict[str, Dict[str, Any]]) -> tuple[List[Dict[str, str]], Dict[str, List[str]]]:
        cos_result = await self.session.execute(
            select(CourseOutcome.id, CourseOutcome.code, CourseOutcome.statement)
            .where(CourseOutcome.course_id == course_id)
            .order_by(CourseOutcome.code)
        )
        cos = [
            {"id": str(row[0]), "code": str(row[1]), "statement": str(row[2] or "")}
            for row in cos_result.all()
        ]
        if not cos or not question_rows:
            return cos, {}

        co_by_id = {co["id"]: co["id"] for co in cos}
        co_by_code = {co["code"].upper(): co["id"] for co in cos}
        question_ids = list(question_rows.keys())
        mapping_result = await self.session.execute(
            select(question_co_mapping_table.c.question_id, question_co_mapping_table.c.course_outcome_id)
            .where(question_co_mapping_table.c.question_id.in_(question_ids))
        )

        question_to_cos: Dict[str, List[str]] = {qid: [] for qid in question_ids}
        for question_id, course_outcome_id in mapping_result.all():
            qid = str(question_id)
            co_id = str(course_outcome_id)
            if qid in question_to_cos and co_id in co_by_id and co_id not in question_to_cos[qid]:
                question_to_cos[qid].append(co_id)

        exam_ids = sorted({str(meta.get("exam_id")) for meta in question_rows.values() if meta.get("exam_id")})
        question_meta_refs: Dict[str, List[str]] = {}
        question_meta_refs_by_number: Dict[int, List[str]] = {}
        for exam_id in exam_ids:
            payload = await get_json(f"exam_question_meta:{exam_id}")
            if not isinstance(payload, dict):
                continue
            for item in payload.get("questions", []):
                if not isinstance(item, dict):
                    continue
                qid = str(item.get("question_id") or "").strip()
                refs = self._resolve_co_refs(item.get("co_mapped"), co_by_id, co_by_code)
                if refs and qid:
                    question_meta_refs[qid] = refs
                q_num_raw = item.get("question_number")
                try:
                    q_num = int(q_num_raw)
                except Exception:
                    q_num = 0
                if refs and q_num > 0:
                    question_meta_refs_by_number[q_num] = refs

        for question_id, meta in question_rows.items():
            if question_to_cos.get(question_id):
                continue
            meta_refs = question_meta_refs.get(question_id)
            if meta_refs:
                question_to_cos[question_id] = meta_refs
                continue
            q_num_raw = meta.get("question_number")
            try:
                q_num = int(q_num_raw)
            except Exception:
                q_num = 0
            if q_num > 0 and question_meta_refs_by_number.get(q_num):
                question_to_cos[question_id] = question_meta_refs_by_number[q_num]
                continue
            text = str(meta.get("question_text") or "")
            explicit_codes = [
                token.replace(" ", "").replace("-", "").replace("_", "").upper()
                for token in re.findall(r"\bCO\s*[-_]?\s*\d{1,2}\b", text, flags=re.IGNORECASE)
            ]
            explicit_refs = self._resolve_co_refs(explicit_codes, co_by_id, co_by_code)
            if explicit_refs:
                question_to_cos[question_id] = explicit_refs
                continue
            inferred = self._infer_best_co_id(str(meta.get("question_text") or ""), cos)
            if inferred:
                question_to_cos[question_id] = [inferred]
                continue
            if q_num > 0 and cos:
                question_to_cos[question_id] = [cos[(q_num - 1) % len(cos)]["id"]]

        return cos, question_to_cos

    async def calculate_course_outcome_attainments(self, course_id: str, exam_id: str, threshold_pct: float = _DEFAULT_THRESHOLD) -> List[Dict[str, Any]]:
        thresholds = await _level_thresholds_live()
        cos_result = await self.session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course_id))
        cos = list(cos_result.scalars().all())
        if not cos: return []
        all_q_result = await self.session.execute(
            select(ExamQuestion.id, ExamQuestion.marks, ExamQuestion.question_text, ExamQuestion.exam_id, ExamQuestion.question_number)
            .where(ExamQuestion.exam_id == exam_id)
        )
        question_rows = {
            str(row[0]): {"max_marks": row[1], "question_text": row[2], "exam_id": row[3], "question_number": row[4]}
            for row in all_q_result.all()
        }
        all_questions = {qid: meta["max_marks"] for qid, meta in question_rows.items()}
        all_marks_result = await self.session.execute(select(StudentMarks.student_id, StudentMarks.question_id, StudentMarks.marks_obtained).where(StudentMarks.exam_id == exam_id))
        marks_by_student: Dict[str, Dict[str, float]] = {}
        for row in all_marks_result.all():
            marks_by_student.setdefault(row[0], {})[row[1]] = float(row[2])
        total_students = len(marks_by_student)
        _, question_to_cos = await self._build_question_to_co_map(course_id, question_rows)
        co_question_map: Dict[str, List[str]] = {str(co.id): [] for co in cos}
        for question_id, co_ids in question_to_cos.items():
            for co_id in co_ids:
                if co_id in co_question_map:
                    co_question_map[co_id].append(question_id)
        attainments: List[Dict] = []
        for co in cos:
            co_q_ids = [qid for qid in co_question_map.get(str(co.id), []) if qid in all_questions]
            if not co_q_ids:
                # CO has no question mapping for this exam — include with 0 attainment
                attainments.append({
                    "co_id": co.id, "co_code": co.code, "code": co.code,
                    "co_statement": co.statement, "statement": co.statement,
                    "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level),
                    "total_students": total_students, "students": total_students,
                    "students_cleared_threshold": 0, "students_cleared": 0,
                    "threshold_pct": int(threshold_pct * 100), "threshold_marks": 0,
                    "max_marks_co": 0, "total_obtained": 0.0, "marks_obtained": 0.0,
                    "attainment_percentage": 0.0, "percentage": 0.0, "attainment": 0.0,
                    "avg_marks_percentage": 0.0,
                    "attainment_level": _level(0.0, thresholds), "level": _level(0.0, thresholds),
                    "not_assessed": True,
                })
                continue
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
                row.attainment_percentage = round(att_pct, 2); row.attainment_level = _level(att_pct, thresholds)
                row.calculated_at = datetime.utcnow()
            else:
                row = COAttainment(id=str(uuid.uuid4()), course_outcome_id=co.id, exam_id=exam_id, total_students=total_students, total_marks=int(max_marks_co), marks_obtained=Decimal(str(round(total_obtained, 4))), attainment_percentage=round(att_pct, 2), attainment_level=_level(att_pct, thresholds), calculated_at=datetime.utcnow())
                self.session.add(row)
            attainments.append({
                "co_id": co.id,
                "co_code": co.code,
                "code": co.code,
                "co_statement": co.statement,
                "statement": co.statement,
                "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level),
                "total_students": total_students,
                "students": total_students,
                "students_cleared_threshold": students_cleared,
                "students_cleared": students_cleared,
                "threshold_pct": int(threshold_pct * 100),
                "threshold_marks": round(threshold_marks, 2),
                "max_marks_co": int(max_marks_co),
                "total_obtained": round(total_obtained, 2),
                "marks_obtained": round(total_obtained, 2),
                "attainment_percentage": round(att_pct, 2),
                "percentage": round(att_pct, 2),
                "attainment": round(att_pct, 2),
                "avg_marks_percentage": round(avg_marks_pct, 2),
                "attainment_level": _level(att_pct, thresholds),
                "level": _level(att_pct, thresholds),
            })
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
        """Weighted CO attainment with Best-N-of-M FA rule and 80/20 direct/indirect blend."""
        thresholds = await _level_thresholds_live()
        s = get_settings()
        fa_best_n: int = getattr(s, "fa_best_n", 3)
        direct_w: float = getattr(s, "co_direct_weight", 0.80)
        indirect_w: float = getattr(s, "co_indirect_weight", 0.20)
        target_level: int = getattr(s, "co_target_level", 2)

        exams_result = await self.session.execute(select(Exam).where(Exam.course_id == course_id))
        exams = list(exams_result.scalars().all())
        cos_result = await self.session.execute(select(CourseOutcome).where(CourseOutcome.course_id == course_id))
        cos = list(cos_result.scalars().all())
        results: List[Dict] = []
        for co in cos:
            fa_attainments: List[float] = []   # collect all FA scores for Best-N rule
            non_fa_weighted_sum = 0.0
            non_fa_weight_total = 0.0
            per_exam: List[Dict] = []

            for exam in exams:
                stored = await self._get_stored_co_attainment(co.id, exam.id)
                pct = stored.get("attainment_percentage") if stored else None
                found: Optional[Dict] = None
                if pct is None:
                    fresh = await self.calculate_course_outcome_attainments(course_id, exam.id, threshold_pct)
                    found = next((a for a in fresh if a["co_id"] == co.id), None)
                    if not found:
                        continue
                    pct = found["attainment_percentage"]
                etype = _exam_type_key(exam)
                w = _EXAM_WEIGHTS.get(etype, 10.0)
                per_exam.append({"exam_id": exam.id, "exam_name": exam.exam_name, "exam_type": etype, "weight": w, "attainment": round(pct, 2), "level": _level(pct, thresholds)})
                # Only include in FA/SA blend if the CO was actually assessed in this exam
                if found and found.get("not_assessed"):
                    continue
                if _is_fa_exam(etype):
                    fa_attainments.append(pct)
                else:
                    non_fa_weighted_sum += w * pct
                    non_fa_weight_total += w

            # Best-N-of-M: take top fa_best_n FA scores, each weighted equally
            if fa_attainments:
                best_fa = sorted(fa_attainments, reverse=True)[:fa_best_n]
                # FA average (simple mean of best N) then weighted by total FA weight
                fa_avg = sum(best_fa) / len(best_fa)
                fa_total_weight = len(fa_attainments) * _EXAM_WEIGHTS.get("t1", 5.0)
                fa_weighted_sum = fa_avg * fa_total_weight
                fa_weight_total = fa_total_weight
            else:
                fa_weighted_sum = fa_weight_total = 0.0

            total_weighted = non_fa_weighted_sum + fa_weighted_sum
            total_weight = non_fa_weight_total + fa_weight_total
            direct_pct = (total_weighted / total_weight) if total_weight > 0 else 0.0

            # Indirect attainment from survey (Redis key: survey:{course_id}:{co_id})
            indirect_pct = await self._get_indirect_attainment(course_id, co.id)

            # NBA 80/20 blend
            if indirect_pct is not None:
                weighted_pct = (direct_pct * direct_w) + (indirect_pct * indirect_w)
                has_indirect = True
            else:
                weighted_pct = direct_pct  # no indirect data yet — use direct only
                has_indirect = False

            achieved_level = _level(weighted_pct, thresholds)
            gap = not _target_met(achieved_level, target_level)

            results.append({
                "co_id": co.id,
                "co_code": co.code,
                "code": co.code,
                "co_statement": co.statement,
                "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level),
                "direct_attainment_percentage": round(direct_pct, 2),
                "indirect_attainment_percentage": round(indirect_pct, 2) if indirect_pct is not None else None,
                "has_indirect": has_indirect,
                # NBA final (80/20 blended)
                "weighted_attainment_percentage": round(weighted_pct, 2),
                "attainment_percentage": round(weighted_pct, 2),
                "percentage": round(weighted_pct, 2),
                "attainment_level": achieved_level,
                "level": achieved_level,
                # Gap analysis
                "target_level": target_level,
                "target_met": not gap,
                "gap_flag": gap,
                "gap_action": "Remedial action required" if gap else None,
                "per_exam": per_exam,
                "fa_scores_used": len(fa_attainments),
                "fa_best_n_applied": min(fa_best_n, len(fa_attainments)),
            })
        return results

    async def calculate_program_outcome_attainments(self, course_id: str, program_id: str) -> List[Dict[str, Any]]:
        thresholds = await _level_thresholds_live()
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
                row.attainment_percentage = po_pct; row.attainment_level = _level(po_pct, thresholds)
                row.co_count = len(co_att); row.calculated_at = datetime.utcnow()
            else:
                row = POAttainment(id=str(uuid.uuid4()), program_outcome_id=po.id, course_id=course_id, attainment_percentage=po_pct, attainment_level=_level(po_pct, thresholds), co_count=len(co_att), calculated_at=datetime.utcnow())
                self.session.add(row)
            attainments.append({
                "po_id": po.id,
                "po_code": po.code,
                "code": po.code,
                "po_statement": po.statement,
                "statement": po.statement,
                "attainment_percentage": round(po_pct, 2),
                "percentage": round(po_pct, 2),
                "attainment": round(po_pct, 2),
                "attainment_level": _level(po_pct, thresholds),
                "level": _level(po_pct, thresholds),
                "mapped_cos": len(co_att),
                "co_details": co_details,
            })
        await self.session.commit()
        return attainments

    async def calculate_pso_attainments(self, course_id: str, program_id: str) -> List[Dict[str, Any]]:
        thresholds = await _level_thresholds_live()
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
            attainments.append({
                "pso_id": pso.id,
                "pso_code": pso.code,
                "code": pso.code,
                "pso_statement": pso.statement,
                "statement": pso.statement,
                "attainment_percentage": round(pso_pct, 2),
                "percentage": round(pso_pct, 2),
                "attainment": round(pso_pct, 2),
                "attainment_level": _level(pso_pct, thresholds),
                "level": _level(pso_pct, thresholds),
                "mapped_cos": len(co_att),
            })
        return attainments

    async def run_full_attainment_pipeline(self, course_id: str, program_id: str, threshold_pct: float = _DEFAULT_THRESHOLD) -> Dict[str, Any]:
        thresholds = await _level_thresholds_live()
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
        # Gap analysis: COs below target level
        gap_cos = [c for c in weighted_cos if c.get("gap_flag")]
        gap_pos = [p for p in po_atts if _level(p["attainment_percentage"], thresholds) == "Level 1"]
        return {
            "course_id": course_id,
            "program_id": program_id,
            "threshold_pct": int(threshold_pct * 100),
            "co_per_exam": co_per_exam,
            "weighted_co_attainments": weighted_cos,
            "po_attainments": po_atts,
            "pso_attainments": pso_atts,
            "co_po_matrix": matrix,
            "gap_analysis": {
                "cos_below_target": gap_cos,
                "pos_at_level1": gap_pos,
                "total_gap_cos": len(gap_cos),
                "total_gap_pos": len(gap_pos),
                "action_required": len(gap_cos) > 0 or len(gap_pos) > 0,
            },
            "summary": {
                "average_co_attainment": round(avg_co, 2),
                "average_po_attainment": round(avg_po, 2),
                "average_pso_attainment": round(avg_pso, 2),
                "overall_level": _level(avg_co, thresholds),
                "total_cos": len(weighted_cos),
                "total_pos": len(po_atts),
                "total_psos": len(pso_atts),
                "cos_meeting_target": len(weighted_cos) - len(gap_cos),
                "cos_below_target": len(gap_cos),
            },
        }

    async def get_co_po_matrix(self, course_id: str) -> Dict[str, Any]:
        from app.core.database.models import ProgramSpecificOutcome
        cos_result = await self.session.execute(select(CourseOutcome.id, CourseOutcome.code).where(CourseOutcome.course_id == course_id))
        cos = list(cos_result.all())
        mapping_result = await self.session.execute(select(ProgramOutcome.id, ProgramOutcome.code, CourseOutcome.id.label("co_id"), co_po_mapping_table.c.similarity_score).join(co_po_mapping_table, ProgramOutcome.id == co_po_mapping_table.c.program_outcome_id).join(CourseOutcome, CourseOutcome.id == co_po_mapping_table.c.course_outcome_id).where(CourseOutcome.course_id == course_id))
        po_rows = list(mapping_result.all())
        co_id_to_code = {c[0]: c[1] for c in cos}
        # Use only actually mapped POs, sorted naturally (PO1..PO12 then others)
        mapped_po_codes = {row[1] for row in po_rows}
        def _po_sort_key(code: str):
            import re as _re
            m = _re.match(r'^([A-Za-z]+)(\d+)$', code)
            return (m.group(1).upper(), int(m.group(2))) if m else (code.upper(), 0)
        po_codes = sorted(mapped_po_codes, key=_po_sort_key)
        co_codes = [c[1] for c in cos]
        cell: Dict[str, Dict[str, int]] = {cc: {pc: 0 for pc in po_codes} for cc in co_codes}
        for row in po_rows:
            co_code = co_id_to_code.get(row[2], ""); po_code = row[1]
            sim = float(row[3] or 0.0); lvl = 3 if sim >= 0.75 else (2 if sim >= 0.50 else (1 if sim >= 0.10 else 0))
            if co_code and po_code: cell[co_code][po_code] = max(cell[co_code].get(po_code, 0), lvl)
        row_sums = {cc: sum(cell[cc].values()) for cc in co_codes}
        return {"cos": co_codes, "pos": po_codes, "data": cell, "row_sums": row_sums}

    async def get_student_performance(self, course_id: str, exam_id: Optional[str] = None) -> List[Dict[str, Any]]:
        thresholds = await _level_thresholds_live()
        if exam_id: exam_ids = [exam_id]
        else:
            exams_r = await self.session.execute(select(Exam.id).where(Exam.course_id == course_id))
            exam_ids = [r[0] for r in exams_r.all()]
        if not exam_ids: return []
        q_result = await self.session.execute(
            select(ExamQuestion.id, ExamQuestion.marks, ExamQuestion.exam_id, ExamQuestion.question_text, ExamQuestion.question_number)
            .where(ExamQuestion.exam_id.in_(exam_ids))
        )
        questions = {
            str(r[0]): {"max_marks": r[1], "exam_id": r[2], "question_text": r[3], "question_number": r[4]}
            for r in q_result.all()
        }
        total_max = sum(v["max_marks"] for v in questions.values())
        marks_result = await self.session.execute(select(StudentMarks.student_id, StudentMarks.question_id, StudentMarks.marks_obtained).where(StudentMarks.question_id.in_(list(questions.keys()))))
        student_marks: Dict[str, Dict[str, float]] = {}; student_totals: Dict[str, float] = {}
        for row in marks_result.all():
            sid, qid, m = row[0], row[1], float(row[2])
            student_marks.setdefault(sid, {})[qid] = m
            student_totals[sid] = student_totals.get(sid, 0.0) + m
        cos_catalog, question_to_cos = await self._build_question_to_co_map(course_id, questions)
        cos_list = [(co["id"], co["code"]) for co in cos_catalog]
        co_q_map: Dict[str, List[str]] = {str(co_id): [] for co_id, _ in cos_list}
        for question_id, co_ids in question_to_cos.items():
            for co_id in co_ids:
                if co_id in co_q_map:
                    co_q_map[co_id].append(question_id)
        performance: List[Dict] = []
        for sid, total in student_totals.items():
            co_details: Dict[str, Any] = {}
            for co_id, co_code in cos_list:
                q_ids = [qid for qid in co_q_map.get(co_id, []) if qid in questions]
                co_max = sum(questions[qid]["max_marks"] for qid in q_ids)
                co_obtained = sum(student_marks[sid].get(qid, 0) for qid in q_ids)
                co_pct = (co_obtained / co_max * 100) if co_max > 0 else 0.0
                co_details[co_code] = {"obtained": round(co_obtained, 2), "max": int(co_max), "percent": round(co_pct, 1), "level": _level(co_pct, thresholds)}
            overall_pct = (total / total_max * 100) if total_max > 0 else 0.0
            # FIX: append is INSIDE the for loop — was outside causing only last student to be saved
            performance.append({
                "student_id": sid,
                "total_marks": round(total, 2),
                "max_marks": total_max,
                "percentage": round(overall_pct, 2),
                "total_percentage": round(overall_pct, 2),
                "grade": _grade(overall_pct),
                "level": _level(overall_pct, thresholds),
                "co_breakdown": co_details,
            })
        performance.sort(key=lambda x: x["percentage"], reverse=True)
        return performance

    async def get_visualization_data(self, course_id: str) -> Dict[str, Any]:
        thresholds = await _level_thresholds_live()
        level3_pct, level2_pct = thresholds
        summary = await self.get_course_attainment_summary(course_id)
        co_chart = {
            "labels": [c.get("co_code", c.get("code", "")) for c in co_data],
            "values": [c.get("attainment_percentage", c.get("percentage", 0)) for c in co_data],
            "colors": [_chart_color(c.get("attainment_level", c.get("level", ""))) for c in co_data],
            "thresholds": {"level3": level3_pct, "level2": level2_pct},
        }
        po_chart = {
            "labels": [p.get("po_code", p.get("code", "")) for p in po_data],
            "values": [p.get("attainment_percentage", p.get("percentage", 0)) for p in po_data],
            "colors": [_chart_color(p.get("attainment_level", p.get("level", ""))) for p in po_data],
        }
        bloom_result = await self.session.execute(select(ExamQuestion.bloom_level, func.count().label("cnt")).join(Exam, ExamQuestion.exam_id == Exam.id).where(Exam.course_id == course_id).group_by(ExamQuestion.bloom_level))
        bloom_dist = {str(r[0].value if hasattr(r[0], "value") else r[0]): r[1] for r in bloom_result.all()}
        students = await self.get_student_performance(course_id)
        grade_dist: Dict[str, int] = {}
        for s in students: g = s["grade"]; grade_dist[g] = grade_dist.get(g, 0) + 1
        return {"course_id": course_id, "co_attainment_chart": co_chart, "po_attainment_chart": po_chart, "bloom_distribution": bloom_dist, "grade_distribution": grade_dist, "summary": {"avg_co": summary.get("average_co_attainment", 0), "avg_po": summary.get("average_po_attainment", 0), "overall_level": summary.get("overall_level", "Level 1"), "total_cos": len(co_data), "total_pos": len(po_data), "total_students": len(students)}}

    async def get_course_attainment_summary(self, course_id: str) -> Dict[str, Any]:
        thresholds = await _level_thresholds_live()
        co_result = await self.session.execute(select(COAttainment, CourseOutcome.code, CourseOutcome.statement).join(CourseOutcome, COAttainment.course_outcome_id == CourseOutcome.id).where(CourseOutcome.course_id == course_id).order_by(COAttainment.calculated_at.desc()))
        seen_co: Set[str] = set(); co_rows: List[Dict] = []
        for row in co_result.all():
            co_att, co_code, co_stmt = row
            if co_att.course_outcome_id not in seen_co:
                seen_co.add(co_att.course_outcome_id)
                pct = float(co_att.attainment_percentage or 0)
                lvl = co_att.attainment_level or _level(pct, thresholds)
                co_rows.append({
                    "id": co_att.id,
                    "co_id": co_att.course_outcome_id,
                    "co_code": co_code,
                    "code": co_code,
                    "statement": co_stmt,
                    "co_statement": co_stmt,
                    # expose under all keys the frontend may read
                    "attainment_percentage": pct,
                    "percentage": pct,
                    "attainment": pct,
                    "attainment_level": lvl,
                    "level": lvl,
                    "students_cleared": co_att.total_students,
                    "students_cleared_threshold": co_att.total_students,
                    "total_students": co_att.total_students,
                    "students": co_att.total_students,
                    "total_marks": co_att.total_marks,
                    "marks_obtained": float(co_att.marks_obtained or 0),
                })
        po_result = await self.session.execute(select(POAttainment, ProgramOutcome.code, ProgramOutcome.statement).join(ProgramOutcome, POAttainment.program_outcome_id == ProgramOutcome.id).where(POAttainment.course_id == course_id).order_by(POAttainment.calculated_at.desc()))
        seen_po: Set[str] = set(); po_rows: List[Dict] = []
        for row in po_result.all():
            po_att, po_code, po_stmt = row
            if po_att.program_outcome_id not in seen_po:
                seen_po.add(po_att.program_outcome_id)
                pct = float(po_att.attainment_percentage or 0)
                lvl = po_att.attainment_level or _level(pct, thresholds)
                po_rows.append({
                    "id": po_att.id,
                    "po_id": po_att.program_outcome_id,
                    "po_code": po_code,
                    "code": po_code,
                    "statement": po_stmt,
                    "attainment_percentage": pct,
                    "percentage": pct,
                    "attainment": pct,
                    "attainment_level": lvl,
                    "level": lvl,
                })
        avg_co = sum(r["attainment_percentage"] for r in co_rows) / max(len(co_rows), 1)
        avg_po = sum(r["attainment_percentage"] for r in po_rows) / max(len(po_rows), 1)
        return {"course_id": course_id, "co_attainments": co_rows, "po_attainments": po_rows, "average_co_attainment": round(avg_co, 2), "average_po_attainment": round(avg_po, 2), "overall_level": _level(avg_co, thresholds)}

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

    async def _get_indirect_attainment(self, course_id: str, co_id: str) -> Optional[float]:
        """Fetch indirect CO attainment from Redis survey data.
        Survey stored at key: survey:{course_id}:{co_id}
        Expected payload: {"survey_avg": 3.8, "scale": 5} or {"indirect_pct": 76.0}
        Returns percentage (0-100) or None if no survey data exists.
        """
        try:
            payload = await get_json(f"survey:{course_id}:{co_id}")
            if not payload:
                return None
            if "indirect_pct" in payload:
                return float(payload["indirect_pct"])
            if "survey_avg" in payload:
                scale = float(payload.get("scale", 5))
                return (float(payload["survey_avg"]) / scale) * 100.0
        except Exception:
            pass
        return None

    async def set_indirect_attainment(self, course_id: str, co_id: str, survey_avg: float, scale: float = 5.0) -> Dict[str, Any]:
        """Store indirect CO attainment survey data in Redis.
        survey_avg: mean Likert score (e.g. 3.8 on a 5-point scale)
        scale: max scale value (default 5)
        """
        from app.core.infrastructure.redis_client import set_json
        indirect_pct = (survey_avg / scale) * 100.0
        payload = {
            "course_id": course_id,
            "co_id": co_id,
            "survey_avg": round(survey_avg, 2),
            "scale": scale,
            "indirect_pct": round(indirect_pct, 2),
            "updated_at": datetime.utcnow().isoformat(),
        }
        await set_json(f"survey:{course_id}:{co_id}", payload, ttl_seconds=86400 * 365)
        return payload

    async def _get_stored_co_attainment(self, co_id: str, exam_id: str) -> Optional[Dict]:
        result = await self.session.execute(select(COAttainment).where(and_(COAttainment.course_outcome_id == co_id, COAttainment.exam_id == exam_id)))
        row = result.scalar_one_or_none()
        if row: return {"attainment_percentage": float(row.attainment_percentage or 0), "attainment_level": row.attainment_level}
        return None
