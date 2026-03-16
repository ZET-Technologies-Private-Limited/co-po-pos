"""
Question Analysis Service - Advanced OBE Implementation
"""
from __future__ import annotations
import asyncio
import csv, io, json, re, uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database.models import (
    Exam, ExamQuestion, QuestionBloomLevel, StudentMarks,
    CourseOutcome, StudentEnrollment, question_co_mapping_table,
)
from app.core.logging.system_logger import SystemLogger
from app.ai_engine.llm.llm_client import LLMClient
from app.core.config.settings import get_settings
from app.core.config.constants import BloomTaxonomyLevel, QuestionType
from app.core.infrastructure.redis_client import get_json
logger = SystemLogger("question_analysis_service")
_settings = get_settings()
_VALID_BLOOM = {"remember","understand","apply","analyze","evaluate","create"}
_BLOOM_KEYWORDS: Dict[str, List[str]] = {
    "remember":  ["define","list","recall","state","name","label","memorize"],
    "understand":["explain","describe","classify","discuss","summarize","paraphrase","interpret"],
    "apply":     ["solve","use","demonstrate","calculate","execute","implement","illustrate"],
    "analyze":   ["compare","contrast","distinguish","differentiate","examine","break down"],
    "evaluate":  ["judge","assess","justify","critique","defend","argue","appraise"],
    "create":    ["design","develop","construct","create","formulate","compose","build","invent","plan"],
}

class QuestionAnalysisService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.llm = LLMClient()

    def _resolve_requested_co_ids(self, q_data: Dict[str, Any], cos: List[tuple]) -> List[str]:
        co_ids = {str(row[0]): str(row[0]) for row in cos}
        co_codes = {str(row[1]).strip().upper(): str(row[0]) for row in cos}

        raw_refs: List[str] = []
        for key in ("co_mapped", "co_ids", "co_codes"):
            value = q_data.get(key)
            if isinstance(value, (list, tuple, set)):
                raw_refs.extend(str(item).strip() for item in value if str(item).strip())
            elif isinstance(value, str) and value.strip():
                raw_refs.extend(part.strip() for part in value.split(",") if part.strip())

        raw_code = q_data.get("co_code")
        if isinstance(raw_code, str) and raw_code.strip():
            raw_refs.extend(part.strip() for part in raw_code.split(",") if part.strip())

        resolved: List[str] = []
        seen: set[str] = set()
        for ref in raw_refs:
            resolved_id = co_ids.get(ref) or co_codes.get(ref.upper())
            if resolved_id and resolved_id not in seen:
                seen.add(resolved_id)
                resolved.append(resolved_id)
        return resolved

    async def add_questions(self, exam_id: str, questions: List[Dict[str, Any]], detect_bloom_with_llm: bool = True) -> List[ExamQuestion]:
        result = await self.session.execute(select(Exam).where(Exam.id == exam_id))
        exam = result.scalar_one_or_none()
        if not exam: raise ValueError(f"Exam {exam_id} not found")
        texts = [q.get("question_text","") for q in questions]
        if detect_bloom_with_llm and any(t.strip() for t in texts):
            bloom_levels = await self._batch_bloom_detect_llm(texts)
        else:
            bloom_levels = [self._keyword_bloom(t) for t in texts]
        cos_result = await self.session.execute(select(CourseOutcome.id, CourseOutcome.code, CourseOutcome.statement).where(CourseOutcome.course_id == exam.course_id))
        cos_list = list(cos_result.all())
        created: List[ExamQuestion] = []
        for i, (q_data, bloom_lvl) in enumerate(zip(questions, bloom_levels)):
            if q_data.get("bloom_level"):
                b = q_data["bloom_level"].strip().lower()
                bloom_lvl = b if b in _VALID_BLOOM else "understand"
            bloom_enum = BloomTaxonomyLevel(bloom_lvl if bloom_lvl in _VALID_BLOOM else "understand")
            q_type_raw = (q_data.get("question_type") or "long_answer").lower()
            q_type = QuestionType(q_type_raw) if q_type_raw in {"mcq", "short_answer", "long_answer", "practical", "essay"} else QuestionType.LONG_ANSWER
            eq = ExamQuestion(id=str(uuid.uuid4()), exam_id=exam_id, question_number=q_data.get("question_number", i+1), question_text=q_data.get("question_text",""), marks=float(q_data.get("marks",10)), question_type=q_type, bloom_level=bloom_enum, bloom_confidence=0.85 if detect_bloom_with_llm else 0.60)
            self.session.add(eq)
            await self.session.flush()
            requested_co_ids = self._resolve_requested_co_ids(q_data, cos_list)
            if requested_co_ids:
                for co_id in requested_co_ids:
                    await self.session.execute(
                        question_co_mapping_table.insert().values(
                            question_id=eq.id,
                            course_outcome_id=co_id,
                            similarity_score=1.0,
                            confidence_score=1.0,
                        )
                    )
            elif cos_list and q_data.get("question_text","").strip():
                mapped = await self._map_question_to_co_llm(q_data.get("question_text",""), bloom_enum.value, cos_list)
                co_id = mapped.get("co_id") if isinstance(mapped, dict) else None
                conf = float(mapped.get("confidence", 0.80)) if isinstance(mapped, dict) else 0.80
                if co_id:
                    await self.session.execute(
                        question_co_mapping_table.insert().values(
                            question_id=eq.id,
                            course_outcome_id=co_id,
                            similarity_score=conf,
                            confidence_score=conf,
                        )
                    )
            created.append(eq)
        exam.question_count = len(created)
        await self.session.commit()
        logger.info(f"Added {len(created)} questions to exam {exam_id}")
        return created

    async def process_marks_json(self, exam_id: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        exam_ctx = await self._load_exam_context(exam_id)
        q_map: Dict[str, str] = exam_ctx["qid_by_number"]
        q_max: Dict[str, float] = exam_ctx["qmax_by_number"]
        exam_total = exam_ctx["exam_total"]
        either_pairs = await self._load_either_or_pairs(exam_id)
        enrolled = exam_ctx["enrolled"]
        if not q_map:
            raise ValueError(f"No questions for exam {exam_id}. Add questions first.")

        normalized_rows: List[Dict[str, Any]] = []
        for row in rows:
            sid = str(row.get("student_id", "")).strip()
            marks = {}
            for q_num_str, mv in row.get("marks", {}).items():
                marks[str(q_num_str)] = mv
            normalized_rows.append({"student_id": sid, "marks": marks})

        validation_errors = self._validate_marks_rows(
            normalized_rows=normalized_rows,
            q_max_by_number=q_max,
            exam_total=exam_total,
            either_pairs=either_pairs,
            enrolled=enrolled,
        )
        if validation_errors:
            return {"rows_saved": 0, "errors": validation_errors[:50]}

        rows_saved = 0
        errors: List[str] = []
        for row in normalized_rows:
            sid = row["student_id"]
            if not sid:
                continue
            for q_num_str, mv in row.get("marks", {}).items():
                q_id = q_map.get(str(q_num_str))
                if not q_id or mv is None or str(mv).strip() == "":
                    continue
                try:
                    val = Decimal(str(float(mv)))
                    # upsert: update if exists, insert if not
                    existing = await self.session.execute(
                        select(StudentMarks).where(
                            and_(
                                StudentMarks.exam_id == exam_id,
                                StudentMarks.student_id == sid,
                                StudentMarks.question_id == q_id,
                            )
                        )
                    )
                    sm = existing.scalar_one_or_none()
                    if sm:
                        sm.marks_obtained = val
                    else:
                        self.session.add(
                            StudentMarks(
                                id=str(uuid.uuid4()),
                                exam_id=exam_id,
                                student_id=sid,
                                question_id=q_id,
                                marks_obtained=val,
                            )
                        )
                    rows_saved += 1
                except Exception as exc:
                    errors.append(f"{sid}/{q_num_str}: {exc}")
        try:
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise ValueError(f"DB commit failed: {exc}") from exc
        return {"rows_saved": rows_saved, "errors": errors[:10]}

    async def process_marks_file(self, exam_id: str, content: bytes, filename: str = "upload.csv") -> Dict[str, Any]:
        fn = (filename or "x").lower()
        if fn.endswith(".xlsx") or fn.endswith(".xls"):
            return await self._process_excel(exam_id, content)
        return await self._process_csv(exam_id, content)

    async def _process_excel(self, exam_id: str, content: bytes) -> Dict[str, Any]:
        try: import openpyxl
        except ImportError: raise ValueError("openpyxl not installed")
        wb = openpyxl.load_workbook(io.BytesIO(content))
        ws = wb.active
        rows_iter = list(ws.iter_rows(values_only=True))
        if not rows_iter: return {"rows_processed": 0}
        headers = [str(h).strip() if h is not None else "" for h in rows_iter[0]]
        dict_rows = [dict(zip(headers, row)) for row in rows_iter[1:]]
        if "question_id" in headers: return await self._save_explicit_rows(exam_id, dict_rows)
        return await self._save_spreadsheet_rows(exam_id, dict_rows, headers)

    async def _process_csv(self, exam_id: str, content: bytes) -> Dict[str, Any]:
        csv_text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(csv_text))
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
        if "question_id" in fieldnames: return await self._save_explicit_rows(exam_id, rows)
        return await self._save_spreadsheet_rows(exam_id, rows, fieldnames)

    async def _save_explicit_rows(self, exam_id: str, rows: List[Dict]) -> Dict[str, Any]:
        processed = 0
        for row in rows:
            sid = str(row.get("student_id","")).strip(); qid = str(row.get("question_id","")).strip()
            raw  = row.get("marks", row.get("marks_obtained",0))
            if not sid or not qid: continue
            try:
                mark_val = Decimal(str(float(raw or 0)))
                existing = await self.session.execute(
                    select(StudentMarks).where(
                        and_(
                            StudentMarks.exam_id == exam_id,
                            StudentMarks.student_id == sid,
                            StudentMarks.question_id == qid,
                        )
                    )
                )
                sm = existing.scalar_one_or_none()
                if sm:
                    sm.marks_obtained = mark_val
                else:
                    self.session.add(StudentMarks(id=str(uuid.uuid4()), exam_id=exam_id, student_id=sid, question_id=qid, marks_obtained=mark_val))
                processed += 1
            except Exception: pass
        await self.session.commit()
        return {"rows_processed": processed}

    async def _save_spreadsheet_rows(self, exam_id: str, rows: List[Dict], headers: List[str]) -> Dict[str, Any]:
        exam_ctx = await self._load_exam_context(exam_id)
        q_map: Dict[str, str] = exam_ctx["qid_by_number"]
        q_max: Dict[str, float] = exam_ctx["qmax_by_number"]
        exam_total = exam_ctx["exam_total"]
        either_pairs = await self._load_either_or_pairs(exam_id)
        enrolled = exam_ctx["enrolled"]

        normalized_rows: List[Dict[str, Any]] = []
        for row in rows:
            sid = str(
                row.get("student_id", row.get("roll_no", row.get("roll", row.get("Student", row.get("student", "")))))
            ).strip()
            marks: Dict[str, Any] = {}
            for col, val in row.items():
                if not col:
                    continue
                col_norm = str(col).strip().lower()
                if col_norm in ("student_id", "student", "name", "roll_no", "roll", "sno", "s.no"):
                    continue
                q_num = re.sub(r"[Qq]", "", str(col)).strip()
                marks[q_num] = val
            normalized_rows.append({"student_id": sid, "marks": marks})

        validation_errors = self._validate_marks_rows(
            normalized_rows=normalized_rows,
            q_max_by_number=q_max,
            exam_total=exam_total,
            either_pairs=either_pairs,
            enrolled=enrolled,
        )
        if validation_errors:
            return {"rows_processed": 0, "errors": validation_errors[:50]}

        processed = 0
        for row in normalized_rows:
            sid = row["student_id"]
            if not sid:
                continue
            for q_num, val in row.get("marks", {}).items():
                q_id = q_map.get(str(q_num))
                if not q_id or val is None or str(val).strip() == "":
                    continue
                try:
                    mark_val = Decimal(str(float(val)))
                    existing = await self.session.execute(
                        select(StudentMarks).where(
                            and_(
                                StudentMarks.exam_id == exam_id,
                                StudentMarks.student_id == sid,
                                StudentMarks.question_id == q_id,
                            )
                        )
                    )
                    sm = existing.scalar_one_or_none()
                    if sm:
                        sm.marks_obtained = mark_val
                    else:
                        self.session.add(
                            StudentMarks(
                                id=str(uuid.uuid4()),
                                exam_id=exam_id,
                                student_id=sid,
                                question_id=q_id,
                                marks_obtained=mark_val,
                            )
                        )
                    processed += 1
                except Exception:
                    pass
        await self.session.commit()
        return {"rows_processed": processed}

    async def _load_exam_context(self, exam_id: str) -> Dict[str, Any]:
        ex_result = await self.session.execute(select(Exam).where(Exam.id == exam_id))
        exam = ex_result.scalar_one_or_none()
        if not exam:
            raise ValueError(f"Exam {exam_id} not found")

        q_result = await self.session.execute(
            select(ExamQuestion.question_number, ExamQuestion.id, ExamQuestion.marks)
            .where(ExamQuestion.exam_id == exam_id)
        )
        q_rows = q_result.all()
        qid_by_number: Dict[str, str] = {str(r[0]): r[1] for r in q_rows}
        qmax_by_number: Dict[str, float] = {str(r[0]): float(r[2]) for r in q_rows}

        enroll_result = await self.session.execute(
            select(StudentEnrollment.student_id).where(StudentEnrollment.course_id == exam.course_id)
        )
        enrolled = {str(r[0]) for r in enroll_result.all()}

        return {
            "exam_total": float(exam.total_marks),
            "qid_by_number": qid_by_number,
            "qmax_by_number": qmax_by_number,
            "enrolled": enrolled,
        }

    async def _load_either_or_pairs(self, exam_id: str) -> List[List[str]]:
        try:
            payload = await get_json(f"exam_question_meta:{exam_id}")
        except Exception:
            payload = None
        if not payload:
            return []

        pair_map: Dict[str, List[str]] = {}
        for q_meta in payload.get("questions", []):
            pair_key = str(q_meta.get("either_or_pair") or "").strip()
            q_num = str(q_meta.get("question_number") or "").strip()
            if not pair_key or not q_num:
                continue
            pair_map.setdefault(pair_key, []).append(q_num)
        return [nums for nums in pair_map.values() if len(nums) >= 2]

    def _validate_marks_rows(
        self,
        normalized_rows: List[Dict[str, Any]],
        q_max_by_number: Dict[str, float],
        exam_total: float,
        either_pairs: List[List[str]],
        enrolled: set,
    ) -> List[str]:
        errors: List[str] = []
        seen_students: set = set()

        for row in normalized_rows:
            sid = str(row.get("student_id", "")).strip()
            if not sid:
                errors.append("Missing roll number in one of the rows")
                continue

            if sid in seen_students:
                errors.append(f"Duplicate entry found for roll number {sid}.")
                continue
            seen_students.add(sid)

            # Only enforce enrollment check when the course actually has enrollment records
            if enrolled and sid not in enrolled:
                # warn but do not block — faculty may upload before enrollment is seeded
                logger.warning(f"Student {sid} not in enrollment list for exam {exam_id} — allowing upload")

            marks = row.get("marks", {}) or {}
            row_total = 0.0
            numeric_marks: Dict[str, float] = {}

            for q_num, raw in marks.items():
                q_key = str(q_num)
                if raw is None or str(raw).strip() == "":
                    continue
                if q_key not in q_max_by_number:
                    errors.append(f"Q{q_key} not found for roll {sid}.")
                    continue
                try:
                    val = float(raw)
                except Exception:
                    errors.append(f"Invalid marks value '{raw}' for roll {sid}, Q{q_key}.")
                    continue

                if val < 0:
                    errors.append(f"Negative marks not allowed. Row: {sid}, Q{q_key}.")
                qmax = float(q_max_by_number[q_key])
                if val > qmax:
                    errors.append(f"Q{q_key} marks {val} exceed question max of {qmax} for {sid}.")

                row_total += val
                numeric_marks[q_key] = val

            if row_total > exam_total:
                errors.append(f"Total marks {row_total} exceed exam maximum of {exam_total} for roll {sid}.")

            for pair in either_pairs:
                non_zero = [q for q in pair if numeric_marks.get(q, 0.0) > 0]
                if len(non_zero) > 1:
                    qtxt = " and ".join([f"Q{q}" for q in non_zero])
                    errors.append(f"Both {qtxt} have marks for {sid}. Only one allowed.")

        return errors

    async def analyze_exam_questions(self, exam_id: str) -> Dict[str, Any]:
        result = await self.session.execute(select(ExamQuestion).where(ExamQuestion.exam_id == exam_id))
        questions = result.unique().scalars().all()
        bloom_dist: Dict[str, int] = {}
        for q in questions:
            bl = str(q.bloom_level.value if hasattr(q.bloom_level,"value") else q.bloom_level)
            bloom_dist[bl] = bloom_dist.get(bl,0) + 1
        return {"total_questions": len(questions), "total_marks": sum(q.marks for q in questions), "bloom_distribution": bloom_dist, "questions": [{"id": q.id, "number": q.question_number, "text": (q.question_text or "")[:120], "marks": q.marks, "bloom_level": str(q.bloom_level.value if hasattr(q.bloom_level,"value") else q.bloom_level), "bloom_confidence": q.bloom_confidence} for q in questions]}

    async def detect_all_bloom_levels(self, exam_id: str) -> Dict[str, Any]:
        result = await self.session.execute(select(ExamQuestion).where(ExamQuestion.exam_id == exam_id))
        questions = result.unique().scalars().all()
        texts = [q.question_text or "" for q in questions]
        bloom_levels = await self._batch_bloom_detect_llm(texts)
        bloom_dist: Dict[str, int] = {}
        for q, lvl in zip(questions, bloom_levels):
            lvl_key = str(lvl or "").strip().lower()
            bloom_enum = BloomTaxonomyLevel(lvl_key if lvl_key in _VALID_BLOOM else "understand")
            q.bloom_level = bloom_enum
            q.bloom_confidence = 0.90
            bloom_dist[bloom_enum.value] = bloom_dist.get(bloom_enum.value, 0) + 1
            self.session.add(QuestionBloomLevel(id=str(uuid.uuid4()), question_id=q.id, bloom_level=bloom_enum, confidence_score=0.90, detection_method="llm_gemini"))
        await self.session.commit()
        return {"detected": len(questions), "bloom_distribution": bloom_dist, "most_common": max(bloom_dist, key=bloom_dist.get) if bloom_dist else "understand"}

    async def map_question_to_cos(self, question_id: str, co_ids: List[str]) -> Dict[str, Any]:
        await self.session.execute(delete(question_co_mapping_table).where(question_co_mapping_table.c.question_id == question_id))
        for co_id in co_ids:
            await self.session.execute(question_co_mapping_table.insert().values(question_id=question_id, course_outcome_id=co_id, similarity_score=1.0, confidence_score=1.0))
        await self.session.commit()
        return {"question_id": question_id, "mapped_cos": len(co_ids)}

    async def _map_question_to_co_llm(self, question_text: str, bloom_level: str, cos: List[tuple]) -> Dict[str, Any]:
        if not cos:
            return {"co_id": None, "confidence": 0.0, "reason": "No COs available for mapping"}
        co_list = "\n".join(f"{i+1}. [{row[1]}] {row[2]}" for i, row in enumerate(cos))
        prompt = (f"Bloom level: {bloom_level}\nQuestion: {question_text[:300]}\n\nCourse Outcomes:\n{co_list}\n\nReply with ONLY the CO number (1,2,...) that best matches. If none match, reply 0.")
        try:
            timeout_sec = min(15.0, float(getattr(_settings, "llm_request_timeout_sec", 30.0) or 30.0))
            response = await asyncio.wait_for(self.llm.generate_completion(prompt), timeout=timeout_sec)
            match = re.search(r"\b(\d+)\b", response.strip())
            if match:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(cos):
                    return {
                        "co_id": cos[idx][0],
                        "confidence": 0.82,
                        "reason": f"Topic similarity and bloom level '{bloom_level}' matched {cos[idx][1]}",
                    }
        except asyncio.TimeoutError:
            logger.warning("CO mapping LLM timed out; using deterministic fallback mapping")
        except Exception as exc:
            logger.warning(f"CO mapping LLM failed: {exc}")
        if cos:
            return {
                "co_id": cos[0][0],
                "confidence": 0.60,
                "reason": "Fallback mapping used due AI ambiguity",
            }
        return {"co_id": None, "confidence": 0.0, "reason": "Unable to map question to CO"}

    async def _batch_bloom_detect_llm(self, texts: List[str]) -> List[str]:
        if not texts: return []
        numbered = "\n".join(f"{i+1}. {t[:200]}" for i, t in enumerate(texts))
        prompt = f"Classify the Bloom's Taxonomy level (remember/understand/apply/analyze/evaluate/create) for each question.\n\n{numbered}\n\nReturn ONLY a JSON array in order. Example: [\"understand\",\"apply\"]"
        try:
            timeout_sec = min(20.0, float(getattr(_settings, "llm_request_timeout_sec", 30.0) or 30.0))
            response = await asyncio.wait_for(self.llm.generate_completion(prompt), timeout=timeout_sec)
            match = re.search(r"\[.*?\]", response, re.DOTALL)
            if match:
                levels = json.loads(match.group(0))
                if isinstance(levels, list) and len(levels) == len(texts):
                    return [lvl.strip().lower() if lvl.strip().lower() in _VALID_BLOOM else "understand" for lvl in levels]
        except asyncio.TimeoutError:
            logger.warning("LLM Bloom detection timed out; using keyword bloom fallback")
        except Exception as exc:
            logger.warning(f"LLM Bloom detection failed: {exc}")
        return [self._keyword_bloom(t) for t in texts]

    def _keyword_bloom(self, text: str) -> str:
        text_lower = (text or "").lower()
        scores = {level: sum(1 for kw in keywords if kw in text_lower) for level, keywords in _BLOOM_KEYWORDS.items()}
        if max(scores.values(), default=0) > 0: return max(scores, key=scores.get)
        return "understand"