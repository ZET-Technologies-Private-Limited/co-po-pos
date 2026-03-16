from __future__ import annotations

import copy
import json
import re
import uuid
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.constants import BloomTaxonomyLevel, ExamType, QuestionType
from app.core.database.models import (
    Course,
    CourseOutcome,
    Exam,
    ExamQuestion,
    ProgramOutcome,
    ProgramSpecificOutcome,
    StudentMarks,
    co_po_mapping_table,
    co_pso_mapping_table,
    question_co_mapping_table,
)
from app.core.infrastructure.redis_client import get_json, set_json
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("three_message_flow_service")

NBA_STANDARD_POS: List[Dict[str, str]] = [
    {"code": "PO1", "statement": "Engineering knowledge: Apply knowledge of mathematics, science, engineering fundamentals to solve complex engineering problems."},
    {"code": "PO2", "statement": "Problem analysis: Identify, formulate, review research literature, and analyze complex engineering problems."},
    {"code": "PO3", "statement": "Design and development of solutions: Design solutions for complex engineering problems and design system components."},
    {"code": "PO4", "statement": "Conduct investigations of complex problems using research-based knowledge and methods."},
    {"code": "PO5", "statement": "Modern tool usage: Create, select, and apply appropriate techniques, resources, and modern engineering tools."},
    {"code": "PO6", "statement": "The engineer and society: Apply reasoning informed by contextual knowledge to assess societal and legal issues."},
    {"code": "PO7", "statement": "Environment and sustainability: Understand the impact of engineering solutions in societal and environmental contexts."},
    {"code": "PO8", "statement": "Ethics: Apply ethical principles and commit to professional ethics and responsibilities."},
    {"code": "PO9", "statement": "Individual and team work: Function effectively as an individual and as a member or leader in diverse teams."},
    {"code": "PO10", "statement": "Communication: Communicate effectively on complex engineering activities with the engineering community and society."},
    {"code": "PO11", "statement": "Project management and finance: Demonstrate knowledge and understanding of engineering and management principles."},
    {"code": "PO12", "statement": "Life-long learning: Recognize the need for, and have the preparation and ability to engage in independent and life-long learning."},
]

_BLOOM_TO_L = {
    "remember": "L1",
    "understand": "L2",
    "apply": "L3",
    "analyze": "L4",
    "analyse": "L4",
    "evaluate": "L5",
    "create": "L6",
}

_L_TO_BLOOM = {
    "L1": "remember",
    "L2": "understand",
    "L3": "apply",
    "L4": "analyze",
    "L5": "evaluate",
    "L6": "create",
}

_BT_DEFAULT_VERB = {
    "L1": "identify",
    "L2": "explain",
    "L3": "apply",
    "L4": "analyze",
    "L5": "evaluate",
    "L6": "design",
}

_UNIT_COMPLEXITY_CUES = {
    "L1": ["define", "list", "identify", "recall", "state", "outline"],
    "L2": ["explain", "describe", "summarize", "classify", "interpret", "discuss"],
    "L3": ["apply", "implement", "solve", "execute", "demonstrate", "use"],
    "L4": ["analyze", "differentiate", "compare", "contrast", "examine", "investigate"],
    "L5": ["evaluate", "justify", "critique", "assess", "verify", "argue"],
    "L6": ["design", "develop", "construct", "formulate", "create", "synthesize"],
}

_BT_ACTION_VERBS: Dict[str, List[str]] = {
    "L1": ["define", "list", "recall", "name", "state", "identify", "memorise", "recognise"],
    "L2": ["explain", "describe", "classify", "summarise", "interpret", "discuss", "compare"],
    "L3": ["solve", "use", "demonstrate", "compute", "execute", "implement", "calculate"],
    "L4": ["compare", "distinguish", "examine", "differentiate", "infer", "categorise", "analyze"],
    "L5": ["justify", "critique", "assess", "recommend", "argue", "judge", "defend", "evaluate"],
    "L6": ["design", "develop", "construct", "formulate", "produce", "invent", "build", "create"],
}


def _extract_json(text: str) -> Any:
    if not text:
        raise ValueError("Empty response")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    arr = re.search(r"\[.*\]", text, re.DOTALL)
    if arr:
        return json.loads(arr.group(0))
    obj = re.search(r"\{.*\}", text, re.DOTALL)
    if obj:
        return json.loads(obj.group(0))
    return json.loads(text)


def _norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _tokens(value: str) -> set[str]:
    words = set(re.findall(r"\b[a-z]{4,}\b", _norm_text(value)))
    stop = {
        "students", "will", "able", "with", "from", "that", "this", "into", "have",
        "been", "course", "outcome", "engineering", "system", "using", "apply", "design",
    }
    return words - stop


def _extract_verb(statement: str) -> str:
    m = re.search(r"students\s+will\s+be\s+able\s+to\s+([A-Za-z\-]+)", statement, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    words = re.findall(r"[A-Za-z\-]+", statement)
    return words[0] if words else ""


def _co_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm_text(a), _norm_text(b)).ratio()


def _level_min_percent(level: int) -> float:
    if level >= 3:
        return 60.0
    if level == 2:
        return 50.0
    return 0.0


def _attainment_level(value: float) -> int:
    if value >= 60.0:
        return 3
    if value >= 50.0:
        return 2
    return 1


def validate_matrix(
    cos: List[Dict[str, Any]],
    pos: List[Dict[str, Any]],
    mapping_matrix: Dict[str, Any],
) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if not cos:
        errors.append("No COs available for validation")
    if not pos:
        errors.append("No POs available for validation")

    total_cells = len(cos) * len(pos)
    nonzero_cells = 0

    normalized_matrix: Dict[str, int] = {}
    for key, raw_value in mapping_matrix.items():
        value = raw_value
        if isinstance(raw_value, str) and raw_value.strip().isdigit():
            value = int(raw_value.strip())
        normalized_matrix[key] = value
        if isinstance(value, int) and value > 0:
            nonzero_cells += 1
        if value not in [0, 1, 2, 3]:
            errors.append(f"Invalid correlation {value} at {key} - must be 0,1,2,3")

    density = (nonzero_cells / total_cells) if total_cells else 0.0

    for co in cos:
        co_id = str(co.get("id", "")).strip()
        co_mappings = [
            v for k, v in normalized_matrix.items()
            if k.startswith(f"{co_id}_") and isinstance(v, int) and v > 0
        ]
        if pos and len(co_mappings) == 0:
            errors.append(f"{co_id} maps to 0 POs - every CO needs >=1 mapping")
        if pos and len(co_mappings) >= len(pos):
            errors.append(f"{co_id} maps all {len(pos)} POs - reduce over-mapping")

        strong = [
            k for k, v in normalized_matrix.items()
            if k.startswith(f"{co_id}_") and isinstance(v, int) and v >= 2
        ]
        if len(strong) > 7:
            warnings.append(f"{co_id} has {len(strong)} strong mappings (>=2) - review")

    for po in pos:
        po_id = str(po.get("id", "")).strip()
        po_mappings = [
            v for k, v in normalized_matrix.items()
            if k.endswith(f"_{po_id}") and isinstance(v, int) and v > 0
        ]
        if len(po_mappings) == 0:
            warnings.append(f"{po_id} has no mappings - will show 0% in attainment")
        elif len(po_mappings) < 2:
            warnings.append(f"{po_id} has mappings from only {len(po_mappings)} CO(s) - recommended >=2")

    if density < 0.30:
        warnings.append(f"Matrix density {density:.0%} below 30% - check coverage gaps")
    if density > 0.60:
        warnings.append(f"Matrix density {density:.0%} above 60% - check over-mapping")

    for i in range(len(cos)):
        for j in range(i + 1, len(cos)):
            si = str(cos[i].get("statement", ""))
            sj = str(cos[j].get("statement", ""))
            if si and sj and _co_similarity(si, sj) >= 0.80:
                warnings.append(
                    f"{cos[i].get('id')} and {cos[j].get('id')} are very similar - consider merging"
                )

    return {
        "errors": errors,
        "warnings": warnings,
        "can_save": len(errors) == 0,
        "matrix_density": round(density, 4),
        "nonzero_cells": nonzero_cells,
        "total_cells": total_cells,
    }


class ThreeMessageFlowService:
    def __init__(self, session: AsyncSession, user_id: str, user_role: str):
        self.session = session
        self.user_id = user_id
        self.user_role = (user_role or "").lower()
        self.llm = None
        try:
            from app.ai_engine.llm.llm_client import LLMClient  # lazy import for runtime resilience

            self.llm = LLMClient()
        except Exception as exc:
            logger.warning(f"LLM client unavailable, using algorithmic fallback mapping: {exc}")

    @staticmethod
    def _session_key(user_id: str, session_id: str) -> str:
        return f"chatbot_three_flow:{user_id}:{session_id}"

    async def _load_state(self, session_id: str) -> Dict[str, Any]:
        key = self._session_key(self.user_id, session_id)
        payload = await get_json(key)
        if isinstance(payload, dict):
            return payload
        return {
            "session_id": session_id,
            "stage": "awaiting_message_1",
            "workflow_step": 1,
            "course_db_id": None,
            "course_code": None,
            "num_cos": 5,
            "warnings": [],
            "next_step": "course_info",
        }

    @staticmethod
    def _workflow_guide() -> str:
        return (
            "STEP 1: provide course details, unit-wise syllabus, NBA POs, department PSOs, and CO count (4-6).\n"
            "STEP 2: review and confirm the CO-PO-PSO mapping matrix.\n"
            "STEP 3: confirm exam configuration.\n"
            "STEP 4: confirm question to CO and BT mapping.\n"
            "STEP 5: submit marks and compute attainment."
        )

    async def _save_state(self, state: Dict[str, Any]) -> None:
        key = self._session_key(self.user_id, state["session_id"])
        await set_json(key, state, ttl_seconds=86400)

    @staticmethod
    def _numeric_value(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        match = re.search(r"-?\d+(?:\.\d+)?", str(value or ""))
        if not match:
            return None
        try:
            return float(match.group(0))
        except Exception:
            return None

    @staticmethod
    def _question_number(label: str) -> int:
        match = re.search(r"(\d+)", str(label or ""))
        return int(match.group(1)) if match else 0

    @classmethod
    def _question_sort_key(cls, label: str) -> Tuple[int, str]:
        return (cls._question_number(label), str(label or "").upper())

    @staticmethod
    def _duration_to_minutes(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(round(float(value)))
        text = str(value).strip().lower()
        if not text:
            return None
        match = re.search(r"(\d+(?:\.\d+)?)\s*(hour|hours|hr|hrs|minute|minutes|min|mins)", text)
        if match:
            raw = float(match.group(1))
            unit = match.group(2)
            if unit.startswith("hour") or unit.startswith("hr"):
                return int(round(raw * 60))
            return int(round(raw))
        numeric = ThreeMessageFlowService._numeric_value(text)
        return int(round(numeric)) if numeric is not None else None

    @staticmethod
    def _normalize_exam_id(value: str) -> str:
        raw = re.sub(r"[^A-Za-z0-9]+", "", str(value or "").upper())
        if raw.startswith("TEST") and raw[4:].isdigit():
            return f"T{raw[4:]}"
        if raw.startswith("TERMTEST") and raw[8:].isdigit():
            return f"T{raw[8:]}"
        if raw in {"ENDSEM", "ENDSEMESTER", "ENDTERM", "SEMESTEREND", "FINAL", "SEE", "SA"}:
            return "ENDSEM"
        return raw

    @staticmethod
    def _assessment_code(exam_id: str, exam_type: str) -> Optional[str]:
        normalized = ThreeMessageFlowService._normalize_exam_id(exam_id)
        if exam_type == "FA" and re.fullmatch(r"T[1-5]", normalized):
            return normalized
        if exam_type == "SA" and normalized in {"ENDSEM", "SEE", "FINAL", "ENDTERM"}:
            return "SEE"
        return None

    @staticmethod
    def _db_exam_type(exam_type: str) -> ExamType:
        return ExamType.MID_TERM if str(exam_type).upper() == "FA" else ExamType.END_TERM

    @staticmethod
    def _default_duration_minutes(exam_type: str) -> int:
        return 60 if str(exam_type).upper() == "FA" else 180

    @staticmethod
    def _empty_exam_config_draft() -> Dict[str, Any]:
        return {
            "fa_method": None,
            "fa_best_n": None,
            "threshold_pct": None,
            "fa_weight": None,
            "sa_weight": None,
            "direct_weight": 80.0,
            "indirect_weight": 20.0,
            "target_level": 2,
            "exams": [],
        }

    def _merge_exam_config_draft(self, current: Optional[Dict[str, Any]], incoming: Dict[str, Any]) -> Dict[str, Any]:
        merged = copy.deepcopy(current or self._empty_exam_config_draft())
        for key in ("fa_method", "fa_best_n", "threshold_pct", "fa_weight", "sa_weight", "direct_weight", "indirect_weight", "target_level"):
            if incoming.get(key) is not None:
                merged[key] = incoming.get(key)

        exam_by_id = {
            str(item.get("exam_id", "")).upper(): copy.deepcopy(item)
            for item in (merged.get("exams") or [])
            if isinstance(item, dict) and item.get("exam_id")
        }
        for item in incoming.get("exams") or []:
            if not isinstance(item, dict):
                continue
            exam_id = str(item.get("exam_id", "")).upper()
            if not exam_id:
                continue
            target = exam_by_id.get(exam_id, {"exam_id": exam_id})
            for key, value in item.items():
                if value is not None:
                    target[key] = value
            exam_by_id[exam_id] = target

        merged["exams"] = sorted(
            exam_by_id.values(),
            key=lambda item: (item.get("exam_type", "ZZ"), self._question_sort_key(item.get("exam_id", ""))),
        )
        return merged

    def _upsert_exam_skeletons(self, draft: Dict[str, Any], exam_type: str, labels: List[str]) -> None:
        if not labels:
            return
        existing = {str(item.get("exam_id", "")).upper() for item in draft.get("exams") or [] if isinstance(item, dict)}
        for raw_label in labels:
            exam_id = self._normalize_exam_id(raw_label)
            if not exam_id or exam_id in existing:
                continue
            draft.setdefault("exams", []).append(
                {
                    "exam_id": exam_id,
                    "display_name": raw_label.strip(),
                    "exam_type": exam_type,
                    "question_count": None,
                    "marks_per_question": None,
                    "total_marks": None,
                    "duration_minutes": None,
                    "internal_choice": None,
                }
            )
            existing.add(exam_id)

    def _extract_exam_config_from_text(self, text: str, state: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        draft = copy.deepcopy(state.get("exam_config_draft") or self._empty_exam_config_draft())
        lower = text.lower()
        warnings: List[str] = []

        tests_line = re.search(r"(?:^|\n)\s*tests?\s*:\s*([^\n]+)", text, re.IGNORECASE)
        fa_labels: List[str] = []
        if tests_line:
            fa_labels = [
                self._normalize_exam_id(part)
                for part in re.split(r"[,;/]", tests_line.group(1))
                if self._normalize_exam_id(part)
            ]
        if not fa_labels:
            fa_count = self._numeric_value(re.search(r"(\d+)\s+(?:tests?|fas?|formative assessments?)", lower).group(1)) if re.search(r"(\d+)\s+(?:tests?|fas?|formative assessments?)", lower) else None
            if fa_count:
                fa_labels = [f"T{index}" for index in range(1, int(fa_count) + 1)]
        self._upsert_exam_skeletons(draft, "FA", fa_labels)

        sa_count_match = re.search(r"(\d+)\s+(?:end\s*[- ]?semester|end\s*[- ]?sem|summative|final|sa)\s+exam", lower)
        sa_labels: List[str] = []
        if sa_count_match:
            count = int(sa_count_match.group(1))
            sa_labels = ["ENDSEM"] if count == 1 else [f"SA{index}" for index in range(1, count + 1)]
        elif re.search(r"\bend\s*[- ]?sem(?:ester)?\b|\bend\s*term\b|\bfinal exam\b", lower):
            sa_labels = ["ENDSEM"]
        self._upsert_exam_skeletons(draft, "SA", sa_labels)

        fa_weight = re.search(r"fa\s*weight\s*:?\s*(\d+(?:\.\d+)?)%", lower)
        if fa_weight:
            draft["fa_weight"] = float(fa_weight.group(1))
        sa_weight = re.search(r"sa\s*weight\s*:?\s*(\d+(?:\.\d+)?)%", lower)
        if sa_weight:
            draft["sa_weight"] = float(sa_weight.group(1))
        threshold = re.search(r"(?:pass\s*)?threshold\s*:?\s*(\d+(?:\.\d+)?)%", lower)
        if threshold:
            draft["threshold_pct"] = float(threshold.group(1))

        blend = re.search(r"direct\s*:?\s*indirect(?:\s*blend)?\s*:?\s*(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)", lower)
        if blend:
            draft["direct_weight"] = float(blend.group(1))
            draft["indirect_weight"] = float(blend.group(2))
        elif "nba standard" in lower:
            draft["direct_weight"] = 80.0
            draft["indirect_weight"] = 20.0

        best_match = re.search(r"best\s*(\d+)\s*of\s*(\d+)", lower)
        if best_match:
            draft["fa_method"] = "best_n_of_m"
            draft["fa_best_n"] = int(best_match.group(1))
        elif "weighted average" in lower or "weighted" in lower:
            draft["fa_method"] = "weighted_average"
        elif "simple average" in lower or re.search(r"\baverage\b", lower):
            draft["fa_method"] = "simple_average"

        target_exam_types: List[str] = []
        if re.search(r"\btest\b|\btests\b|\bfa\b|\bformative\b", lower):
            target_exam_types.append("FA")
        if re.search(r"end\s*[- ]?sem|end\s*term|summative|\bsa\b|final exam", lower):
            target_exam_types.append("SA")
        target_exam_types = list(dict.fromkeys(target_exam_types))

        question_count = None
        question_count_match = re.search(r"(\d+)\s+questions?", lower)
        if question_count_match:
            question_count = int(question_count_match.group(1))

        marks_per_question = None
        marks_match = re.search(r"(?:each\s+question\s+carr(?:y|ies)|marks\s+per\s+question)\s*:?\s*(\d+(?:\.\d+)?)", lower)
        if marks_match:
            marks_per_question = float(marks_match.group(1))

        total_marks = None
        total_match = re.search(r"total\s+marks(?:\s+per\s+test)?\s*:?\s*(\d+(?:\.\d+)?)", lower)
        if total_match:
            total_marks = float(total_match.group(1))

        duration_minutes = None
        duration_match = re.search(r"(?:exam\s+duration|duration)\s*:?\s*([^\n,;]+)", text, re.IGNORECASE)
        if duration_match:
            duration_minutes = self._duration_to_minutes(duration_match.group(1))

        internal_choice: Optional[str] = None
        choice_match = re.search(r"internal\s+choice\s*:?\s*([^\n,;]+)", text, re.IGNORECASE)
        if choice_match:
            raw_choice = choice_match.group(1).strip()
            if re.search(r"\bno\b|\bnone\b", raw_choice, re.IGNORECASE):
                internal_choice = "No"
            elif re.search(r"\byes\b", raw_choice, re.IGNORECASE):
                internal_choice = "Yes"
            else:
                internal_choice = raw_choice

        if question_count is not None or marks_per_question is not None or total_marks is not None or duration_minutes is not None or internal_choice is not None:
            if not target_exam_types:
                existing_types = {str(item.get("exam_type", "")).upper() for item in state.get("exam_config_draft", {}).get("exams", []) if isinstance(item, dict)}
                target_exam_types = sorted(existing_types) or ["FA"]

            for exam in draft.get("exams") or []:
                if exam.get("exam_type") not in target_exam_types:
                    continue
                if question_count is not None:
                    exam["question_count"] = question_count
                if marks_per_question is not None:
                    exam["marks_per_question"] = marks_per_question
                if total_marks is not None:
                    exam["total_marks"] = total_marks
                if duration_minutes is not None:
                    exam["duration_minutes"] = duration_minutes
                if internal_choice is not None:
                    exam["internal_choice"] = internal_choice
                if exam.get("question_count") and exam.get("marks_per_question"):
                    computed_total = float(exam["question_count"]) * float(exam["marks_per_question"])
                    exam["question_marks"] = {
                        f"Q{index}": float(exam["marks_per_question"])
                        for index in range(1, int(exam["question_count"]) + 1)
                    }
                    if exam.get("total_marks") is None:
                        exam["total_marks"] = computed_total
                    elif abs(float(exam["total_marks"]) - computed_total) > 0.01:
                        warnings.append(
                            f"{exam.get('exam_id')} total marks {exam.get('total_marks')} does not match question count × marks/question ({computed_total:.0f}); computed value will be used"
                        )
                        exam["total_marks"] = computed_total

        return draft, warnings

    def _draft_missing_exam_config_fields(self, draft: Dict[str, Any]) -> List[str]:
        missing: List[str] = []
        exams = [item for item in (draft.get("exams") or []) if isinstance(item, dict)]
        fa_exams = [item for item in exams if str(item.get("exam_type", "")).upper() == "FA"]
        sa_exams = [item for item in exams if str(item.get("exam_type", "")).upper() == "SA"]

        if not fa_exams:
            missing.append("at least one formative assessment (FA)")
        if not sa_exams:
            missing.append("at least one summative assessment (SA)")

        for label, group in (("FA", fa_exams), ("SA", sa_exams)):
            if group and any(not item.get("question_count") or not item.get("marks_per_question") for item in group):
                missing.append(f"{label} question structure")
            if group and any(not item.get("duration_minutes") for item in group):
                missing.append(f"{label} duration")

        if any(str(item.get("exam_type", "")).upper() == "SA" and item.get("internal_choice") is None for item in sa_exams):
            missing.append("SA internal choice")
        if draft.get("fa_weight") is None or draft.get("sa_weight") is None:
            missing.append("FA and SA weights")
        if draft.get("threshold_pct") is None:
            missing.append("pass threshold")
        if not draft.get("fa_method"):
            missing.append("FA aggregation method")
        return list(dict.fromkeys(missing))

    def _draft_to_exam_config(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        config = {
            "fa_method": draft.get("fa_method") or "best_n_of_m",
            "fa_best_n": int(draft.get("fa_best_n") or 3),
            "threshold_pct": float(draft.get("threshold_pct") or 40),
            "fa_weight": float(draft.get("fa_weight") or 40),
            "sa_weight": float(draft.get("sa_weight") or 60),
            "direct_weight": float(draft.get("direct_weight") or 80),
            "indirect_weight": float(draft.get("indirect_weight") or 20),
            "target_level": int(draft.get("target_level") or 2),
            "exams": [],
        }

        for exam in draft.get("exams") or []:
            if not isinstance(exam, dict) or not exam.get("exam_id"):
                continue
            q_marks = exam.get("question_marks") if isinstance(exam.get("question_marks"), dict) else {}
            if not q_marks and exam.get("question_count") and exam.get("marks_per_question"):
                q_marks = {
                    f"Q{index}": float(exam.get("marks_per_question") or 0)
                    for index in range(1, int(exam.get("question_count") or 0) + 1)
                }
            question_marks = {
                str(q_id).upper(): float(mark)
                for q_id, mark in q_marks.items()
            }
            total_marks = sum(question_marks.values()) if question_marks else float(exam.get("total_marks") or 0)
            config["exams"].append(
                {
                    "exam_id": str(exam.get("exam_id", "")).upper(),
                    "display_name": exam.get("display_name") or exam.get("exam_id"),
                    "exam_type": str(exam.get("exam_type", "")).upper(),
                    "question_marks": question_marks,
                    "question_count": len(question_marks) or int(exam.get("question_count") or 0),
                    "total_marks": int(round(total_marks)) if total_marks else 0,
                    "duration_minutes": int(exam.get("duration_minutes") or self._default_duration_minutes(str(exam.get("exam_type", "")))),
                    "internal_choice": exam.get("internal_choice") or "No",
                    "assessment_code": exam.get("assessment_code") or self._assessment_code(str(exam.get("exam_id", "")), str(exam.get("exam_type", "")).upper()),
                }
            )
        return config

    def _validate_exam_configuration_rules(self, config: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str]]:
        validated = copy.deepcopy(config)
        errors: List[str] = []
        warnings: List[str] = []
        exams = [item for item in (validated.get("exams") or []) if isinstance(item, dict)]
        fa_exams = [item for item in exams if str(item.get("exam_type", "")).upper() == "FA"]
        sa_exams = [item for item in exams if str(item.get("exam_type", "")).upper() == "SA"]

        if not fa_exams:
            errors.append("at least one FA exam is required")
        if not sa_exams:
            errors.append("at least one SA exam is required")

        threshold_pct = float(validated.get("threshold_pct", 40) or 40)
        if threshold_pct < 30 or threshold_pct > 60:
            errors.append("threshold_pct must be between 30 and 60")
        elif abs(threshold_pct - 40.0) > 0.01:
            warnings.append(f"Pass threshold set to {threshold_pct:.0f}% instead of the common 40% default")

        for exam in exams:
            exam_id = str(exam.get("exam_id", "")).upper()
            question_marks = exam.get("question_marks") if isinstance(exam.get("question_marks"), dict) else {}
            normalized_marks: Dict[str, float] = {}
            for q_id, raw_mark in question_marks.items():
                try:
                    mark_val = float(raw_mark)
                except Exception:
                    errors.append(f"invalid marks for {exam_id}:{q_id}")
                    continue
                if mark_val <= 0 or abs(mark_val - round(mark_val)) > 0.001:
                    errors.append(f"marks per question must be a positive integer for {exam_id}:{q_id}")
                    continue
                normalized_marks[str(q_id).upper()] = float(int(round(mark_val)))
            question_marks = dict(sorted(normalized_marks.items(), key=lambda item: self._question_sort_key(item[0])))
            question_count = len(question_marks)
            if question_count < 1 or question_count > 10:
                errors.append(f"question count must be between 1 and 10 for exam {exam_id}")
            total_marks = int(round(sum(question_marks.values())))
            if str(exam.get("exam_type", "")).upper() == "FA" and (total_marks < 25 or total_marks > 100):
                warnings.append(f"{exam_id} total marks {total_marks} is outside the usual FA range of 25 to 100")
            exam["question_marks"] = question_marks
            exam["question_count"] = question_count
            exam["total_marks"] = total_marks
            exam["duration_minutes"] = int(exam.get("duration_minutes") or self._default_duration_minutes(str(exam.get("exam_type", ""))))
            if exam.get("internal_choice") in {None, ""}:
                exam["internal_choice"] = "No"

        if str(validated.get("fa_method", "")).lower() == "best_n_of_m":
            available_fas = len(fa_exams)
            requested = int(validated.get("fa_best_n", 3) or 3)
            if available_fas > 0 and requested > available_fas:
                warnings.append(f"Best {requested} of {requested} adjusted to Best {available_fas} of {available_fas} because only {available_fas} FA exam(s) exist")
                validated["fa_best_n"] = available_fas
            if available_fas > 0 and int(validated.get("fa_best_n", 0) or 0) == available_fas:
                warnings.append(f"Best {available_fas} of {available_fas} is equivalent to an FA average")

        return validated, errors, warnings

    def _build_exam_config_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        exams = [item for item in (config.get("exams") or []) if isinstance(item, dict)]
        fa_exams = [item for item in exams if str(item.get("exam_type", "")).upper() == "FA"]
        sa_exams = [item for item in exams if str(item.get("exam_type", "")).upper() == "SA"]
        threshold_pct = float(config.get("threshold_pct", 40) or 40)
        return {
            "fa_count": len(fa_exams),
            "sa_count": len(sa_exams),
            "fa_exams": [
                {
                    "exam_id": item.get("exam_id"),
                    "display_name": item.get("display_name") or item.get("exam_id"),
                    "question_count": item.get("question_count"),
                    "marks_per_question": next(iter((item.get("question_marks") or {0: 0}).values()), 0),
                    "total_marks": item.get("total_marks"),
                    "duration_minutes": item.get("duration_minutes"),
                    "threshold_marks": round((float(item.get("total_marks") or 0) * threshold_pct) / 100.0, 2),
                    "internal_choice": item.get("internal_choice") or "No",
                }
                for item in fa_exams
            ],
            "sa_exams": [
                {
                    "exam_id": item.get("exam_id"),
                    "display_name": item.get("display_name") or item.get("exam_id"),
                    "question_count": item.get("question_count"),
                    "marks_per_question": next(iter((item.get("question_marks") or {0: 0}).values()), 0),
                    "total_marks": item.get("total_marks"),
                    "duration_minutes": item.get("duration_minutes"),
                    "threshold_marks": round((float(item.get("total_marks") or 0) * threshold_pct) / 100.0, 2),
                    "internal_choice": item.get("internal_choice") or "No",
                }
                for item in sa_exams
            ],
            "fa_weight": float(config.get("fa_weight", 40) or 40),
            "sa_weight": float(config.get("sa_weight", 60) or 60),
            "direct_weight": float(config.get("direct_weight", 80) or 80),
            "indirect_weight": float(config.get("indirect_weight", 20) or 20),
            "threshold_pct": threshold_pct,
            "fa_method": str(config.get("fa_method", "best_n_of_m") or "best_n_of_m"),
            "fa_best_n": int(config.get("fa_best_n", 3) or 3),
        }

    def _default_bt_for_co(self, state: Dict[str, Any], co_id: str) -> str:
        for co in state.get("cos") or []:
            if str(co.get("id", "")).upper() == str(co_id).upper():
                return str(co.get("bt_level") or "L2").upper()
        return "L2"

    def _infer_bt_level_from_question_text(self, question_text: str, fallback: str = "L2") -> str:
        lower = str(question_text or "").strip().lower()
        for level, verbs in _BT_ACTION_VERBS.items():
            if any(re.search(rf"\b{re.escape(verb)}\b", lower) for verb in verbs):
                return level
        return fallback

    def _infer_co_from_question_text(self, question_text: str, state: Dict[str, Any]) -> Tuple[str, str]:
        best_score = -1.0
        best_id = ""
        best_reason = ""
        q_tokens = _tokens(question_text)
        q_norm = _norm_text(question_text)
        for co in state.get("cos") or []:
            co_id = str(co.get("id", "")).upper()
            statement = str(co.get("statement", ""))
            overlap = len(q_tokens & _tokens(statement))
            score = overlap * 3.0 + SequenceMatcher(None, q_norm, _norm_text(statement)).ratio()
            if score > best_score:
                best_score = score
                best_id = co_id
                best_reason = f"Auto-mapped from question text similarity with {co_id}"
        return best_id or "CO1", best_reason or "Auto-mapped using default CO fallback"

    def _merge_question_mapping_draft(self, current: Optional[List[Dict[str, Any]]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        mapping: Dict[str, Dict[str, Any]] = {}
        for row in current or []:
            if not isinstance(row, dict):
                continue
            key = f"{str(row.get('exam_id', '')).upper()}:{str(row.get('question_id', '')).upper()}"
            mapping[key] = copy.deepcopy(row)
        for row in incoming:
            key = f"{str(row.get('exam_id', '')).upper()}:{str(row.get('question_id', '')).upper()}"
            mapping[key] = copy.deepcopy(row)
        return sorted(mapping.values(), key=lambda row: (self._normalize_exam_id(str(row.get("exam_id", ""))), self._question_sort_key(str(row.get("question_id", "")))))

    def _extract_question_mapping_from_text(self, text: str, state: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        rows: List[Dict[str, Any]] = []
        errors: List[str] = []
        exam_config = state.get("exam_config") or state.get("pending_exam_config") or {}
        exams = exam_config.get("exams") or []
        exam_lookup = {str(item.get("exam_id", "")).upper(): item for item in exams if isinstance(item, dict)}
        if not exam_lookup:
            return [], ["exam configuration must be confirmed before question mapping"]

        default_exam = next(iter(exam_lookup.keys()), "")
        current_exam = default_exam
        for line in [segment.strip() for segment in str(text or "").splitlines() if segment.strip()]:
            bare_exam = self._normalize_exam_id(line)
            if bare_exam in exam_lookup:
                current_exam = bare_exam
                continue

            header = re.match(r"([A-Za-z0-9_\- ]+)\s*:\s*(.+)", line)
            content = line
            if header:
                possible_exam = self._normalize_exam_id(header.group(1))
                if possible_exam in exam_lookup:
                    current_exam = possible_exam
                    content = header.group(2).strip()

            if re.search(r"\bQ\d+\s*=", content, re.IGNORECASE):
                for segment in [part.strip() for part in re.split(r"[,;]", content) if part.strip()]:
                    match = re.match(r"Q\s*(\d+)\s*=\s*(CO\d+)\s*(?:\(?\s*BT\s*[:=]?\s*(L[1-6])\s*\)?)?", segment, re.IGNORECASE)
                    if not match:
                        continue
                    question_id = f"Q{int(match.group(1))}"
                    co_id = str(match.group(2)).upper()
                    bt_level = str(match.group(3) or self._default_bt_for_co(state, co_id)).upper()
                    rows.append(
                        {
                            "exam_id": current_exam,
                            "question_id": question_id,
                            "co_id": co_id,
                            "bt_level": bt_level,
                            "contribution_pct": 100,
                            "justification": f"Faculty mapped {question_id} to {co_id}",
                        }
                    )
                continue

            text_match = re.match(r"Q\s*(\d+)\s*[\).:-]?\s*(.+)", content, re.IGNORECASE)
            if text_match:
                question_id = f"Q{int(text_match.group(1))}"
                question_text = text_match.group(2).strip()
                co_id, reason = self._infer_co_from_question_text(question_text, state)
                bt_level = self._infer_bt_level_from_question_text(question_text, self._default_bt_for_co(state, co_id))
                rows.append(
                    {
                        "exam_id": current_exam,
                        "question_id": question_id,
                        "co_id": co_id,
                        "bt_level": bt_level,
                        "contribution_pct": 100,
                        "question_text": question_text,
                        "justification": reason,
                    }
                )
                continue

        if not rows:
            errors.append("No question mapping rows detected. Use `T1: Q1=CO1, Q2=CO2` or paste `Q1 ...` lines.")
        return rows, errors

    async def _persist_exam_configuration(self, state: Dict[str, Any], exam_config: Dict[str, Any]) -> Dict[str, Any]:
        course = await self._get_course_from_state(state)
        if not course:
            raise ValueError("Course context missing while persisting exam configuration")

        result = await self.session.execute(select(Exam).where(Exam.course_id == course.id).order_by(Exam.created_at))
        existing_exams = list(result.scalars().all())
        exams_by_name = {str(item.exam_name or "").strip().upper(): item for item in existing_exams}
        exams_by_assessment: Dict[str, Exam] = {}
        for item in existing_exams:
            meta = await get_json(f"exam_meta:{item.id}") or {}
            assessment_code = str(meta.get("assessment_code") or "").strip().upper()
            if assessment_code:
                exams_by_assessment[assessment_code] = item

        fa_count = len([item for item in exam_config.get("exams") or [] if str(item.get("exam_type", "")).upper() == "FA"])
        sa_count = len([item for item in exam_config.get("exams") or [] if str(item.get("exam_type", "")).upper() == "SA"])
        persisted_exams: List[Dict[str, Any]] = []

        for exam in exam_config.get("exams") or []:
            exam_id = str(exam.get("exam_id", "")).upper()
            exam_type = str(exam.get("exam_type", "")).upper()
            exam_name = str(exam.get("display_name") or exam_id).strip() or exam_id
            assessment_code = exam.get("assessment_code") or self._assessment_code(exam_id, exam_type)
            db_exam = None
            if assessment_code:
                db_exam = exams_by_assessment.get(str(assessment_code).upper())
            if db_exam is None:
                db_exam = exams_by_name.get(exam_name.upper())

            if db_exam is None:
                db_exam = Exam(
                    id=str(uuid.uuid4()),
                    course_id=course.id,
                    exam_name=exam_name,
                    exam_type=self._db_exam_type(exam_type),
                    total_marks=int(exam.get("total_marks") or 0),
                    duration_minutes=int(exam.get("duration_minutes") or self._default_duration_minutes(exam_type)),
                    question_count=int(exam.get("question_count") or 0),
                    created_by=self.user_id,
                )
                self.session.add(db_exam)
                await self.session.flush()
                existing_exams.append(db_exam)
            else:
                db_exam.exam_name = exam_name
                db_exam.exam_type = self._db_exam_type(exam_type)
                db_exam.total_marks = int(exam.get("total_marks") or 0)
                db_exam.duration_minutes = int(exam.get("duration_minutes") or self._default_duration_minutes(exam_type))
                db_exam.question_count = int(exam.get("question_count") or 0)

            questions_result = await self.session.execute(
                select(ExamQuestion).where(ExamQuestion.exam_id == db_exam.id).order_by(ExamQuestion.question_number)
            )
            existing_questions = {int(question.question_number or 0): question for question in questions_result.scalars().all()}
            question_db_ids: Dict[str, str] = {}
            for q_id, mark in sorted((exam.get("question_marks") or {}).items(), key=lambda item: self._question_sort_key(item[0])):
                q_number = self._question_number(q_id)
                question = existing_questions.get(q_number)
                placeholder = f"{exam_id} {q_id} placeholder question. Replace with actual question text."
                if question is None:
                    question = ExamQuestion(
                        id=str(uuid.uuid4()),
                        exam_id=db_exam.id,
                        question_number=q_number,
                        question_text=placeholder,
                        marks=int(round(float(mark))),
                        question_type=QuestionType.SHORT_ANSWER,
                        bloom_level=None,
                        bloom_confidence=0.0,
                    )
                    self.session.add(question)
                    await self.session.flush()
                    existing_questions[q_number] = question
                else:
                    question.marks = int(round(float(mark)))
                    question.question_number = q_number
                    if not (question.question_text or "").strip():
                        question.question_text = placeholder
                    if question.question_type is None:
                        question.question_type = QuestionType.SHORT_ANSWER
                question_db_ids[str(q_id).upper()] = question.id

            weightage_pct = None
            if exam_type == "FA" and fa_count > 0:
                weightage_pct = round(float(exam_config.get("fa_weight", 40)) / fa_count, 2)
            elif exam_type == "SA" and sa_count > 0:
                weightage_pct = round(float(exam_config.get("sa_weight", 60)) / sa_count, 2)

            await set_json(
                f"exam_meta:{db_exam.id}",
                {
                    "assessment_code": assessment_code,
                    "weightage_pct": weightage_pct,
                    "units_covered": [],
                    "number_of_questions": int(exam.get("question_count") or 0),
                    "duration_minutes": int(exam.get("duration_minutes") or self._default_duration_minutes(exam_type)),
                    "internal_choice": exam.get("internal_choice") or "No",
                },
                ttl_seconds=86400 * 30,
            )

            persisted_exams.append({**exam, "db_exam_id": db_exam.id, "assessment_code": assessment_code, "weightage_pct": weightage_pct, "question_db_ids": question_db_ids})

        await self.session.commit()
        persisted = copy.deepcopy(exam_config)
        persisted["exams"] = persisted_exams
        return persisted

    async def _persist_question_mapping(self, state: Dict[str, Any], question_mapping: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        exam_config = state.get("exam_config") or {}
        exams_by_id = {str(item.get("exam_id", "")).upper(): item for item in (exam_config.get("exams") or []) if isinstance(item, dict)}
        co_db_by_code = {
            str(item.get("id", "")).upper(): str(item.get("db_id", ""))
            for item in (state.get("cos") or [])
            if item.get("id") and item.get("db_id")
        }

        persisted_rows: List[Dict[str, Any]] = []
        for row in question_mapping:
            exam_id = str(row.get("exam_id", "")).upper()
            question_id = str(row.get("question_id", "")).upper()
            exam_def = exams_by_id.get(exam_id) or {}
            db_exam_id = exam_def.get("db_exam_id")
            if not db_exam_id:
                continue

            questions_result = await self.session.execute(select(ExamQuestion).where(ExamQuestion.exam_id == db_exam_id))
            by_number = {f"Q{int(question.question_number or 0)}": question for question in questions_result.scalars().all()}
            question = by_number.get(question_id)
            q_number = self._question_number(question_id)
            if question is None:
                question = ExamQuestion(
                    id=str(uuid.uuid4()),
                    exam_id=db_exam_id,
                    question_number=q_number,
                    question_text=str(row.get("question_text") or f"{exam_id} {question_id} placeholder question. Replace with actual question text."),
                    marks=int(round(float((exam_def.get("question_marks") or {}).get(question_id, 0) or 0))),
                    question_type=QuestionType.SHORT_ANSWER,
                    bloom_level=None,
                    bloom_confidence=0.0,
                )
                self.session.add(question)
                await self.session.flush()
            elif row.get("question_text"):
                question.question_text = str(row.get("question_text"))

            bloom_level = _L_TO_BLOOM.get(str(row.get("bt_level", "L2")).upper(), "understand")
            question.bloom_level = BloomTaxonomyLevel(bloom_level)
            if question.question_type is None:
                question.question_type = QuestionType.SHORT_ANSWER

            await self.session.execute(delete(question_co_mapping_table).where(question_co_mapping_table.c.question_id == question.id))
            co_db_id = co_db_by_code.get(str(row.get("co_id", "")).upper())
            if co_db_id:
                await self.session.execute(
                    question_co_mapping_table.insert().values(
                        question_id=question.id,
                        course_outcome_id=co_db_id,
                        similarity_score=1.0,
                        confidence_score=1.0,
                    )
                )

            persisted_rows.append({**row, "db_exam_id": db_exam_id, "db_question_id": question.id, "co_db_id": co_db_id})

        await self.session.commit()
        return persisted_rows

    async def _persist_marks_payload(self, state: Dict[str, Any], payload: Dict[str, Any]) -> None:
        exam_config = state.get("exam_config") or {}
        exam_lookup = {str(item.get("exam_id", "")).upper(): item for item in (exam_config.get("exams") or []) if isinstance(item, dict)}
        for exam_row in payload.get("marks_data") or []:
            if not isinstance(exam_row, dict):
                continue
            exam_id = str(exam_row.get("exam_id", "")).upper()
            exam_def = exam_lookup.get(exam_id) or {}
            db_exam_id = exam_def.get("db_exam_id")
            if not db_exam_id:
                continue
            questions_result = await self.session.execute(select(ExamQuestion).where(ExamQuestion.exam_id == db_exam_id))
            question_lookup = {f"Q{int(question.question_number or 0)}": question for question in questions_result.scalars().all()}
            for student in exam_row.get("students") or []:
                if not isinstance(student, dict):
                    continue
                student_id = str(student.get("student_id", "")).strip()
                if not student_id:
                    continue
                for q_label, raw_score in (student.get("marks") or {}).items():
                    normalized_q = str(q_label).upper()
                    if not normalized_q.startswith("Q"):
                        normalized_q = f"Q{self._question_number(normalized_q)}"
                    question = question_lookup.get(normalized_q)
                    if question is None:
                        continue
                    if isinstance(raw_score, str) and raw_score.strip().upper() == "AB":
                        score = 0.0
                    else:
                        score = max(0.0, float(self._numeric_value(raw_score) or 0.0))
                        score = min(score, float(question.marks or 0))

                    existing_result = await self.session.execute(
                        select(StudentMarks).where(
                            StudentMarks.exam_id == db_exam_id,
                            StudentMarks.student_id == student_id,
                            StudentMarks.question_id == question.id,
                        )
                    )
                    existing = existing_result.scalar_one_or_none()
                    if existing:
                        existing.marks_obtained = score
                    else:
                        self.session.add(
                            StudentMarks(
                                id=str(uuid.uuid4()),
                                exam_id=db_exam_id,
                                student_id=student_id,
                                question_id=question.id,
                                marks_obtained=score,
                            )
                        )
        await self.session.commit()

    async def _persist_indirect_data(self, state: Dict[str, Any], indirect_data: Dict[str, Any]) -> None:
        if not indirect_data:
            return
        course = await self._get_course_from_state(state)
        if not course:
            return

        co_db_by_code = {
            str(item.get("id", "")).upper(): str(item.get("db_id", ""))
            for item in (state.get("cos") or [])
            if item.get("id") and item.get("db_id")
        }

        co_means = indirect_data.get("co_mean_ratings") if isinstance(indirect_data.get("co_mean_ratings"), dict) else {}
        if co_means:
            for co_code, raw_avg in co_means.items():
                co_db_id = co_db_by_code.get(str(co_code).upper())
                if not co_db_id:
                    continue
                survey_avg = max(0.0, min(5.0, float(self._numeric_value(raw_avg) or 0.0)))
                await set_json(
                    f"survey:{course.id}:{co_db_id}",
                    {
                        "survey_avg": round(survey_avg, 2),
                        "scale": 5.0,
                        "indirect_pct": round((survey_avg / 5.0) * 100.0, 2),
                    },
                    ttl_seconds=86400 * 365,
                )

        distributions = indirect_data.get("co_rating_distribution") if isinstance(indirect_data.get("co_rating_distribution"), dict) else {}
        for co_code, dist in distributions.items():
            if not isinstance(dist, dict):
                continue
            co_db_id = co_db_by_code.get(str(co_code).upper())
            if not co_db_id:
                continue
            total = 0.0
            weighted = 0.0
            for rating in range(1, 6):
                count = float(self._numeric_value(dist.get(str(rating), dist.get(rating, 0))) or 0.0)
                total += count
                weighted += rating * count
            if total <= 0:
                continue
            survey_avg = weighted / total
            await set_json(
                f"survey:{course.id}:{co_db_id}",
                {
                    "survey_avg": round(survey_avg, 2),
                    "scale": 5.0,
                    "indirect_pct": round((survey_avg / 5.0) * 100.0, 2),
                },
                ttl_seconds=86400 * 365,
            )

    async def process_message(
        self,
        text: str,
        session_id: str,
        message_number: Optional[int] = None,
        course_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        state = await self._load_state(session_id)
        text = (text or "").strip()
        if not text:
            return {
                "status": "invalid_input",
                "message": "Message text is required. Follow the guided workflow in order.\n" + self._workflow_guide(),
                "session_id": session_id,
            }

        lower = text.lower()
        if state.get("stage") in {"mapping_warning_ack", "mapping_preview_ack"} and self._is_confirm(lower):
            return await self._confirm_warning_save(state)
        if state.get("stage") in {"mapping_warning_ack", "mapping_preview_ack"} and self._is_edit(lower):
            return {
                "status": "mapping_edit_requested",
                "message": "Please send updated PO or PSO inputs and I will regenerate the matrix.",
                "next_action": "provide_updated_po_pso",
                "session_id": session_id,
            }

        if state.get("stage") in {"cos_generated", "co_preview_ack"}:
            if self._is_confirm(lower):
                state["stage"] = "awaiting_mapping_inputs"
                state["workflow_step"] = 2
                state["next_step"] = "co_po_pso_mapping"
                await self._save_state(state)
                return {
                    "status": "co_confirmed",
                    "message": "STEP 1 completed and confirmed. Proceed to STEP 2 by providing or confirming the NBA POs and department PSOs so I can build the CO-PO-PSO mapping matrix for review.",
                    "next_action": "provide_po_pso",
                    "workflow_step": 2,
                    "session_id": session_id,
                }
            if self._is_edit(lower):
                state["stage"] = "awaiting_syllabus"
                state["next_step"] = "provide_syllabus"
                await self._save_state(state)
                return {
                    "status": "co_edit_requested",
                    "message": "Please send the updated syllabus text. I will regenerate COs and show them for confirmation.",
                    "next_action": "provide_syllabus",
                    "workflow_step": 1,
                    "session_id": session_id,
                }
            return {
                "status": "co_confirmation_required",
                "message": "Please review STEP 1 CO output and reply CONFIRM to continue, or EDIT to regenerate.",
                "next_action": "confirm_or_modify_cos",
                "workflow_step": 1,
                "session_id": session_id,
            }

        if state.get("stage") in {
            "mapping_confirmed",
            "awaiting_exam_config",
            "exam_config_preview_ack",
            "awaiting_question_mapping",
            "question_mapping_preview_ack",
            "awaiting_marks_entry",
        }:
            return await self._handle_post_mapping_workflow(text=text, state=state)

        step = message_number
        if step is None:
            if state.get("stage") in {"awaiting_message_1", "course_partial", "course_saved"}:
                step = 1 if state.get("stage") != "course_saved" else 2
            elif state.get("stage") in {"awaiting_syllabus", "cos_generated", "co_preview_ack"}:
                step = 2
            elif state.get("stage") == "awaiting_mapping_inputs":
                step = 3
            elif state.get("stage") in {"awaiting_po_choice", "mapping_warning_ack"}:
                step = 3
            else:
                step = 1

        if step == 1:
            return await self._handle_message_1(text=text, state=state, course_hint=course_id)
        if step == 2:
            return await self._handle_message_2(text=text, state=state)
        if step == 3:
            return await self._handle_message_3(text=text, state=state)

        return {
            "status": "invalid_message_number",
            "message": "message_number must be 1, 2, or 3",
            "session_id": session_id,
        }

    async def _handle_message_1(self, text: str, state: Dict[str, Any], course_hint: Optional[str]) -> Dict[str, Any]:
        extracted = self._extract_course_fields(text)
        validated, failures = self._validate_course_fields(extracted)

        if "department" not in validated:
            validated["department"] = "General"

        if "num_cos" not in validated:
            validated["num_cos"] = 5

        course = await self._resolve_course(validated, state, course_hint)

        if course:
            self._apply_course_updates(course, validated)
            await self.session.commit()
            state["course_db_id"] = course.id
            state["course_code"] = course.course_code
            state["department"] = course.department or validated.get("department", "General")
            state["num_cos"] = int(validated.get("num_cos") or state.get("num_cos") or 5)

        missing_only = [f for f in failures if f != "num_cos"]
        if missing_only:
            state["stage"] = "course_partial"
            state["pending_fields"] = missing_only
            state["next_step"] = "provide_missing_fields"
            await self._save_state(state)
            return {
                "status": "course_partial",
                "course_id": state.get("course_code"),
                "db_course_id": state.get("course_db_id"),
                "missing_fields": missing_only,
                "message": self._build_missing_fields_prompt(missing_only),
                "next_action": "provide_missing_fields",
                "session_id": state["session_id"],
            }

        state["stage"] = "awaiting_syllabus"
        state["workflow_step"] = 1
        state["next_step"] = "provide_syllabus"
        await self._save_state(state)
        sem = int(validated.get("semester", course.semester if course else 0))
        credits = int(validated.get("credits", course.credits if course else 0))
        students = int(validated.get("total_students", course.enrolled_students if course else 0))
        return {
            "status": "course_saved",
            "course_id": state.get("course_code"),
            "db_course_id": state.get("course_db_id"),
            "message": (
                f"STEP 1 started. Course {state.get('course_code')} saved. {students} students, {credits} credits, Sem {sem}. "
                "Now provide complete unit-wise syllabus. You can also include all 12 NBA POs, department PSOs, and preferred CO count (4-6). I will not move to STEP 2 until STEP 1 COs are generated and confirmed."
            ),
            "next_action": "provide_syllabus",
            "workflow_step": 1,
            "session_id": state["session_id"],
        }

    async def _handle_message_2(self, text: str, state: Dict[str, Any]) -> Dict[str, Any]:
        course = await self._get_course_from_state(state)
        if not course:
            return {
                "status": "course_not_ready",
                "message": "Send Message 1 with course details first.",
                "next_action": "provide_course_info",
                "session_id": state["session_id"],
            }

        units = self._parse_units(text)
        unit_analysis = self._analyze_unit_complexity(units)
        course.syllabus = text[:5000]
        await self.session.commit()

        num_cos = int(state.get("num_cos") or 5)
        from app.modules.co_generation.services.co_generation_service import CoGenerationService

        # Auto-load NBA POs and department PSOs if not already in session state
        session_pos = state.get("session_pos") or []
        session_psos = state.get("session_psos") or []

        if not session_pos:
            po_rows = await self._load_program_outcomes_for_context(course, state)
            if not po_rows:
                # Seed NBA standard POs into DB then reload
                dept_key = f"DEPT:{((course.department or 'General').strip() or 'General').upper()}"
                for item in NBA_STANDARD_POS:
                    from app.core.database.models import ProgramOutcome
                    existing = (await self.session.execute(
                        select(ProgramOutcome).where(
                            ProgramOutcome.program == dept_key,
                            ProgramOutcome.code == item["code"],
                        )
                    )).scalar_one_or_none()
                    if not existing:
                        import uuid as _uuid
                        self.session.add(ProgramOutcome(
                            id=str(_uuid.uuid4()),
                            code=item["code"],
                            statement=item["statement"],
                            program=dept_key,
                        ))
                await self.session.commit()
                po_rows = await self._load_program_outcomes_for_context(course, state)
            session_pos = [{"code": r.code, "statement": r.statement} for r in po_rows]

        if not session_psos:
            pso_rows = await self._load_program_specific_outcomes_for_context(course, state)
            session_psos = [{"code": r.code, "statement": r.statement} for r in pso_rows]

        gen_service = CoGenerationService(self.session)
        generated = await gen_service.generate_cos_from_syllabus(
            course_id=course.id,
            syllabus=text,
            program_outcomes=session_pos,
            program_specific_outcomes=session_psos,
            num_cos=num_cos,
        )

        cos = generated.get("course_outcomes", [])
        cos_payload = []
        for co in cos:
            bloom_raw = str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level).lower()
            bt_level = _BLOOM_TO_L.get(bloom_raw, "L2")
            statement = self._normalize_co_statement(co.statement or "", bt_level)
            verb = _extract_verb(statement)
            cos_payload.append(
                {
                    "id": co.code,
                    "db_id": co.id,
                    "bt_level": bt_level,
                    "verb": verb,
                    "statement": statement,
                    "units_covered": self._units_covered(statement, units),
                }
            )

        state["stage"] = "cos_generated"
        state["workflow_step"] = 1
        state["units"] = units
        state["unit_analysis"] = unit_analysis
        state["cos"] = cos_payload
        state["next_step"] = "confirm_or_modify_cos"
        await self._save_state(state)

        return {
            "status": "cos_generated",
            "course_id": state.get("course_code"),
            "cos": cos_payload,
            "unit_analysis": unit_analysis,
            "message": "STEP 1 CO generation complete. Review BT level, action verb, and syllabus coverage for each CO. Reply CONFIRM to proceed to STEP 2 mapping, or EDIT to regenerate COs.",
            "next_action": "confirm_or_modify_cos",
            "workflow_step": 1,
            "session_id": state["session_id"],
        }

    async def _handle_message_3(self, text: str, state: Dict[str, Any]) -> Dict[str, Any]:
        course = await self._get_course_from_state(state)
        if not course:
            return {
                "status": "course_not_ready",
                "message": "Course context is missing. Send Message 1 again.",
                "next_action": "provide_course_info",
                "session_id": state["session_id"],
            }

        cos = await self._load_course_cos(course.id)
        if not cos:
            return {
                "status": "cos_missing",
                "message": "No COs found. Send Message 2 syllabus first.",
                "next_action": "provide_syllabus",
                "session_id": state["session_id"],
            }

        if state.get("stage") == "awaiting_po_choice" and state.get("pending_incoming"):
            incoming_pos = state["pending_incoming"].get("pos", [])
            incoming_psos = state["pending_incoming"].get("psos", [])
            resolution = await self._resolve_po_choice(
                text=text,
                course=course,
                incoming_pos=incoming_pos,
                incoming_psos=incoming_psos,
            )
            if resolution.get("status") == "need_choice":
                await self._save_state(state)
                return resolution
            pos_rows = resolution["pos_rows"]
            pso_rows = resolution["pso_rows"]
        else:
            incoming_pos, incoming_psos = self._extract_po_pso(text)
            resolution = await self._resolve_po_sources(text, course, incoming_pos, incoming_psos, state)
            if resolution.get("status") == "po_pso_missing":
                await self._save_state(state)
                return resolution
            if resolution.get("status") == "need_choice":
                state["stage"] = "awaiting_po_choice"
                state["pending_incoming"] = {"pos": incoming_pos, "psos": incoming_psos}
                await self._save_state(state)
                return resolution
            pos_rows = resolution["pos_rows"]
            pso_rows = resolution["pso_rows"]

        pos_payload = [{"id": r.code, "code": r.code, "statement": r.statement} for r in pos_rows]
        pso_payload = [{"id": r.code, "code": r.code, "statement": r.statement} for r in pso_rows]

        mapping_result = await self._generate_mapping(cos, pos_payload, pso_payload)
        mapping_matrix = mapping_result["mapping_matrix"]

        validation = validate_matrix(cos=cos, pos=pos_payload, mapping_matrix=mapping_matrix)
        validation["warnings"].extend(self._validate_pso_coverage(cos, pso_payload, mapping_result))
        combined_density = self._combined_matrix_density(cos, pos_payload, pso_payload, mapping_result)
        if not validation["can_save"]:
            state["stage"] = "mapping_invalid"
            state["next_step"] = "edit_mapping"
            await self._save_state(state)
            return {
                "status": "mapping_invalid",
                "errors": validation["errors"],
                "warnings": validation["warnings"],
                "can_save": False,
                "matrix_density": combined_density,
                "mapping_matrix": mapping_result.get("mapping_matrix", {}),
                "pso_mapping_matrix": mapping_result.get("pso_mapping_matrix", {}),
                "next_action": "edit_mapping",
                "session_id": state["session_id"],
            }

        state["stage"] = "mapping_preview_ack"
        state["pending_mapping"] = mapping_result
        state["pending_validation"] = validation
        state["warnings"] = validation["warnings"]
        state["mapping"] = mapping_result.get("flat_mapping", [])
        state["next_step"] = "confirm_or_edit"
        state["session_pos"] = [{"code": r.code, "statement": r.statement} for r in pos_rows]
        state["session_psos"] = [{"code": r.code, "statement": r.statement} for r in pso_rows]
        await self._save_state(state)

        return {
            "status": "mapping_preview",
            "matrix_density": combined_density,
            "warnings": validation["warnings"],
            "errors": [],
            "can_save": True,
            "mapping_matrix": mapping_result.get("mapping_matrix", {}),
            "pso_mapping_matrix": mapping_result.get("pso_mapping_matrix", {}),
            "mapping_summary": self._build_mapping_summary(validation, mapping_result, cos, pso_payload),
            "message": "STEP 2 mapping draft ready. Review every CO-PO-PSO correlation using the NBA 0/1/2/3 scale. Reply CONFIRM to save mapping, or EDIT to revise before moving forward.",
            "next_action": "confirm_or_edit",
            "workflow_step": 2,
            "session_id": state["session_id"],
        }

    async def _confirm_warning_save(self, state: Dict[str, Any]) -> Dict[str, Any]:
        course = await self._get_course_from_state(state)
        if not course or not state.get("pending_mapping"):
            return {
                "status": "invalid_state",
                "message": "No pending mapping to confirm.",
                "session_id": state["session_id"],
            }

        cos = await self._load_course_cos(course.id)
        pos_rows = await self._load_program_outcomes_for_context(course, state)
        pso_rows = await self._load_program_specific_outcomes_for_context(course, state)

        pending_mapping = state.get("pending_mapping") or {}
        await self._persist_mapping(course.id, cos, pos_rows, pso_rows, pending_mapping)

        validation = state.get("pending_validation", {})
        combined_density = self._combined_matrix_density(cos, [{"id": p.code} for p in pos_rows], [{"id": p.code} for p in pso_rows], pending_mapping)
        state["stage"] = "mapping_confirmed"
        state["workflow_step"] = 3
        state["warnings"] = validation.get("warnings", [])
        state["mapping"] = pending_mapping.get("flat_mapping", [])
        state["confirmed_mapping_matrix"] = pending_mapping.get("mapping_matrix", {})
        state["confirmed_pso_mapping_matrix"] = pending_mapping.get("pso_mapping_matrix", {})
        state["pending_mapping"] = None
        state["pending_validation"] = None
        state["stage"] = "awaiting_exam_config"
        state["next_step"] = "exam_configuration"
        await self._save_state(state)

        return {
            "status": "mapping_generated",
            "matrix_density": combined_density,
            "warnings": validation.get("warnings", []),
            "errors": [],
            "can_save": True,
            "mapping_matrix": pending_mapping.get("mapping_matrix", {}),
            "pso_mapping_matrix": pending_mapping.get("pso_mapping_matrix", {}),
            "mapping_summary": self._build_mapping_summary(validation, pending_mapping, cos, state.get("session_psos", [])),
            "message": "STEP 2 completed. Proceed to STEP 3 by providing examination configuration for each FA/SA exam, including question marks, internal choice, threshold, and FA method.",
            "next_action": "exam_configuration",
            "workflow_step": 3,
            "session_id": state["session_id"],
        }

    async def _handle_post_mapping_workflow(self, text: str, state: Dict[str, Any]) -> Dict[str, Any]:
        stage = state.get("stage")
        lower = text.lower()

        if stage in {"mapping_confirmed", "awaiting_exam_config"}:
            exam_payload, parse_error = self._parse_json_payload(text)
            warnings: List[str] = []
            if parse_error:
                partial_draft, parse_warnings = self._extract_exam_config_from_text(text, state)
                warnings.extend(parse_warnings)
                draft = self._merge_exam_config_draft(state.get("exam_config_draft"), partial_draft)
                state["exam_config_draft"] = draft
                missing_fields = self._draft_missing_exam_config_fields(draft)
                if missing_fields:
                    await self._save_state(state)
                    return {
                        "status": "exam_config_collecting",
                        "exam_config_draft": draft,
                        "missing_fields": missing_fields,
                        "warnings": warnings,
                        "message": (
                            "STEP 3 details captured so far. Still needed: " + ", ".join(missing_fields) + ".\n"
                            "You can continue in plain English, for example: `Each test has 5 questions`, `End-sem has 5 questions`, `FA weight 40%`, `Pass threshold 40%`."
                        ),
                        "next_action": "provide_exam_configuration",
                        "workflow_step": 3,
                        "session_id": state["session_id"],
                    }
                exam_payload = {"exam_config": self._draft_to_exam_config(draft)}

            exam_config, errors = self._extract_exam_configuration(exam_payload)
            exam_config, validation_errors, validation_warnings = self._validate_exam_configuration_rules(exam_config)
            warnings.extend(validation_warnings)
            errors.extend(validation_errors)
            if errors:
                state["exam_config_draft"] = self._merge_exam_config_draft(state.get("exam_config_draft"), exam_config)
                await self._save_state(state)
                return {
                    "status": "exam_config_invalid",
                    "errors": errors,
                    "warnings": warnings,
                    "message": "STEP 3 is incomplete. Please correct exam configuration and resend.",
                    "next_action": "provide_exam_configuration",
                    "workflow_step": 3,
                    "session_id": state["session_id"],
                }

            state["pending_exam_config"] = exam_config
            state["pending_exam_config_warnings"] = warnings
            state["exam_config_draft"] = None
            state["stage"] = "exam_config_preview_ack"
            state["next_step"] = "confirm_exam_configuration"
            await self._save_state(state)
            return {
                "status": "exam_config_preview",
                "exam_config": exam_config,
                "exam_config_summary": self._build_exam_config_summary(exam_config),
                "warnings": warnings,
                "message": "STEP 3 draft captured. Reply CONFIRM to lock exam configuration, or EDIT to resend.",
                "next_action": "confirm_or_edit_exam_configuration",
                "workflow_step": 3,
                "session_id": state["session_id"],
            }

        if stage == "exam_config_preview_ack":
            if self._is_confirm(lower):
                exam_warnings = list(state.get("pending_exam_config_warnings") or [])
                persisted_exam_config = await self._persist_exam_configuration(state, state.get("pending_exam_config") or {})
                state["exam_config"] = persisted_exam_config
                state["pending_exam_config"] = None
                state["pending_exam_config_warnings"] = None
                state["stage"] = "awaiting_question_mapping"
                state["workflow_step"] = 4
                state["next_step"] = "question_to_co_bt_mapping"
                await self._save_state(state)
                return {
                    "status": "exam_config_confirmed",
                    "exam_config": persisted_exam_config,
                    "exam_config_summary": self._build_exam_config_summary(persisted_exam_config),
                    "warnings": state.get("warnings", []) + exam_warnings,
                    "message": "STEP 3 completed. Proceed to STEP 4 by sending question paper mapping, for example `T1: Q1=CO1, Q2=CO2` or paste actual question text lines.",
                    "next_action": "provide_question_mapping",
                    "workflow_step": 4,
                    "session_id": state["session_id"],
                }
            if self._is_edit(lower):
                state["stage"] = "awaiting_exam_config"
                state["next_step"] = "exam_configuration"
                await self._save_state(state)
                return {
                    "status": "exam_config_edit_requested",
                    "message": "Please send updated STEP 3 exam configuration JSON.",
                    "next_action": "provide_exam_configuration",
                    "workflow_step": 3,
                    "session_id": state["session_id"],
                }
            return {
                "status": "exam_config_confirmation_required",
                "message": "Please reply CONFIRM to complete STEP 3, or EDIT to revise exam configuration.",
                "next_action": "confirm_or_edit_exam_configuration",
                "workflow_step": 3,
                "session_id": state["session_id"],
            }

        if stage == "awaiting_question_mapping":
            payload, parse_error = self._parse_json_payload(text)
            if parse_error:
                parsed_rows, parse_errors = self._extract_question_mapping_from_text(text, state)
                if parse_errors and not parsed_rows:
                    return {
                        "status": "question_mapping_required",
                        "errors": parse_errors,
                        "message": "STEP 4 accepts JSON, shorthand like `T1: Q1=CO1, Q2=CO2`, or pasted question text lines such as `Q1 Explain ...`.",
                        "next_action": "provide_question_mapping",
                        "workflow_step": 4,
                        "session_id": state["session_id"],
                    }
                payload = {"question_mapping": self._merge_question_mapping_draft(state.get("question_mapping_draft"), parsed_rows)}

            question_mapping, errors = self._extract_question_mapping(payload, state)
            missing_errors = [error for error in errors if error.startswith("missing STEP 4 mapping")]
            hard_errors = [error for error in errors if error not in missing_errors]
            if hard_errors:
                return {
                    "status": "question_mapping_invalid",
                    "errors": hard_errors,
                    "message": "STEP 4 mapping has validation errors. Please correct and resend.",
                    "next_action": "provide_question_mapping",
                    "workflow_step": 4,
                    "session_id": state["session_id"],
                }

            if missing_errors:
                state["question_mapping_draft"] = question_mapping
                await self._save_state(state)
                return {
                    "status": "question_mapping_collecting",
                    "question_mapping": question_mapping,
                    "missing_fields": missing_errors,
                    "message": "STEP 4 mapping saved partially. Remaining items: " + ", ".join(missing_errors),
                    "next_action": "provide_question_mapping",
                    "workflow_step": 4,
                    "session_id": state["session_id"],
                }

            state["pending_question_mapping"] = question_mapping
            state["question_mapping_draft"] = None
            state["stage"] = "question_mapping_preview_ack"
            state["next_step"] = "confirm_question_mapping"
            await self._save_state(state)
            return {
                "status": "question_mapping_preview",
                "question_mapping": question_mapping,
                "question_mapping_summary": {
                    "mapped_count": len(question_mapping),
                    "exam_ids": sorted({str(row.get('exam_id', '')).upper() for row in question_mapping}),
                },
                "message": "STEP 4 draft ready. Reply CONFIRM to lock question mapping, or EDIT to revise.",
                "next_action": "confirm_or_edit_question_mapping",
                "workflow_step": 4,
                "session_id": state["session_id"],
            }

        if stage == "question_mapping_preview_ack":
            if self._is_confirm(lower):
                persisted_mapping = await self._persist_question_mapping(state, state.get("pending_question_mapping") or [])
                state["question_mapping"] = persisted_mapping
                state["pending_question_mapping"] = None
                state["stage"] = "awaiting_marks_entry"
                state["workflow_step"] = 5
                state["next_step"] = "student_marks_entry"
                await self._save_state(state)
                return {
                    "status": "question_mapping_confirmed",
                    "question_mapping": persisted_mapping,
                    "message": "STEP 4 completed. Proceed to STEP 5 by sending student marks and optional indirect survey data.",
                    "next_action": "provide_marks",
                    "workflow_step": 5,
                    "session_id": state["session_id"],
                }
            if self._is_edit(lower):
                state["stage"] = "awaiting_question_mapping"
                state["next_step"] = "question_to_co_bt_mapping"
                await self._save_state(state)
                return {
                    "status": "question_mapping_edit_requested",
                    "message": "Please send updated STEP 4 question mapping JSON.",
                    "next_action": "provide_question_mapping",
                    "workflow_step": 4,
                    "session_id": state["session_id"],
                }
            return {
                "status": "question_mapping_confirmation_required",
                "message": "Please reply CONFIRM to complete STEP 4, or EDIT to revise mapping.",
                "next_action": "confirm_or_edit_question_mapping",
                "workflow_step": 4,
                "session_id": state["session_id"],
            }

        if stage == "awaiting_marks_entry":
            payload, parse_error = self._parse_json_payload(text)
            if parse_error:
                return {
                    "status": "marks_required",
                    "message": "STEP 5 requires marks JSON. Include marks_data and optional indirect_data.",
                    "expected_schema": {
                        "marks_data": [
                            {
                                "exam_id": "T1",
                                "students": [
                                    {
                                        "student_id": "22CS001",
                                        "marks": {"Q1": 8, "Q2": 7},
                                        "absent": False
                                    }
                                ]
                            }
                        ],
                        "indirect_data": {
                            "responses": 45,
                            "co_mean_ratings": {"CO1": 3.8, "CO2": 4.0}
                        }
                    },
                    "next_action": "provide_marks",
                    "workflow_step": 5,
                    "session_id": state["session_id"],
                }

            calc_result = await self._calculate_attainment(state=state, payload=payload)
            if calc_result.get("status") != "calculation_complete":
                return calc_result

            state["stage"] = "workflow_complete"
            state["workflow_step"] = 5
            state["next_step"] = "report_generation"
            state["latest_calculation"] = calc_result
            await self._save_state(state)
            return calc_result

        return {
            "status": "invalid_stage",
            "message": "Workflow state is not recognized. Please restart from STEP 1.",
            "session_id": state.get("session_id"),
        }

    def _parse_json_payload(self, text: str) -> Tuple[Dict[str, Any], Optional[str]]:
        try:
            parsed = _extract_json(text)
        except Exception:
            return {}, "invalid_json"
        if not isinstance(parsed, dict):
            return {}, "json_must_be_object"
        return parsed, None

    def _extract_exam_configuration(self, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        errors: List[str] = []
        raw = payload.get("exam_config") if isinstance(payload.get("exam_config"), dict) else payload

        fa_method_raw = str(raw.get("fa_method", "best_n_of_m")).strip().lower()
        fa_method_alias = {
            "best": "best_n_of_m",
            "best_n": "best_n_of_m",
            "best_n_of_m": "best_n_of_m",
            "simple_avg": "simple_average",
            "simple": "simple_average",
            "simple_average": "simple_average",
            "average": "simple_average",
            "weighted": "weighted_average",
            "weighted_avg": "weighted_average",
            "weighted_average": "weighted_average",
        }
        fa_method = fa_method_alias.get(fa_method_raw, "")
        if not fa_method:
            errors.append("fa_method must be best_n_of_m, simple_average, or weighted_average")

        threshold_pct = self._numeric_value(raw.get("threshold_pct", 40))
        if threshold_pct is None:
            errors.append("threshold_pct must be numeric")
            threshold_pct = 40.0

        fa_weight = self._numeric_value(raw.get("fa_weight", 40))
        sa_weight = self._numeric_value(raw.get("sa_weight", 60))
        if fa_weight is None or sa_weight is None:
            errors.append("fa_weight and sa_weight must be numeric")
            fa_weight = 40.0
            sa_weight = 60.0
        if fa_weight + sa_weight != 100:
            errors.append("fa_weight + sa_weight must equal 100")

        direct_weight = self._numeric_value(raw.get("direct_weight", 80))
        indirect_weight = self._numeric_value(raw.get("indirect_weight", 20))
        if direct_weight is None or indirect_weight is None:
            errors.append("direct_weight and indirect_weight must be numeric")
            direct_weight = 80.0
            indirect_weight = 20.0
        if direct_weight + indirect_weight != 100:
            errors.append("direct_weight + indirect_weight must equal 100")

        target_level = raw.get("target_level", 2)
        if not str(target_level).isdigit() or int(target_level) not in {1, 2, 3}:
            errors.append("target_level must be 1, 2, or 3")
            target_level = 2
        target_level = int(target_level)

        fa_best_n = raw.get("fa_best_n", 3)
        if not str(fa_best_n).isdigit() or int(fa_best_n) < 1:
            errors.append("fa_best_n must be >= 1")
            fa_best_n = 3
        fa_best_n = int(fa_best_n)

        exams: List[Dict[str, Any]] = []
        raw_exams = raw.get("exams", [])
        if not isinstance(raw_exams, list) or not raw_exams:
            errors.append("at least one exam entry is required")
            raw_exams = []

        for item in raw_exams:
            if not isinstance(item, dict):
                errors.append("each exam entry must be an object")
                continue
            exam_id = self._normalize_exam_id(str(item.get("exam_id", "")).strip())
            exam_type_raw = str(item.get("exam_type", "")).strip().lower()
            if exam_type_raw in {"formative", "fa", "t1", "t2", "t3", "t4", "t5", "test", "tests", "mid_term", "midterm"} or exam_id.startswith("T"):
                exam_type = "FA"
            elif exam_type_raw in {"summative", "sa", "end sem", "endsem", "end_sem", "end_term", "final", "see"} or exam_id in {"ENDSEM", "SEE", "FINAL"}:
                exam_type = "SA"
            else:
                exam_type = ""

            if not exam_id:
                errors.append("exam_id is required for each exam")
            if not exam_type:
                errors.append(f"exam_type invalid for exam {exam_id or '<unknown>'}")

            question_marks = item.get("question_marks")
            if not isinstance(question_marks, dict) or not question_marks:
                errors.append(f"question_marks must be a non-empty object for exam {exam_id or '<unknown>'}")
                question_marks = {}

            normalized_q: Dict[str, float] = {}
            for q_id, q_mark in question_marks.items():
                q_key = str(q_id).strip().upper()
                try:
                    mark_val = float(q_mark)
                except Exception:
                    errors.append(f"invalid marks for {exam_id}:{q_key}")
                    continue
                if mark_val <= 0:
                    errors.append(f"max marks must be > 0 for {exam_id}:{q_key}")
                    continue
                normalized_q[q_key] = mark_val

            duration_minutes = self._duration_to_minutes(item.get("duration_minutes") or item.get("duration") or item.get("exam_duration"))
            total_marks = int(round(sum(normalized_q.values()))) if normalized_q else int(self._numeric_value(item.get("total_marks") or 0) or 0)

            exams.append(
                {
                    "exam_id": exam_id,
                    "display_name": str(item.get("display_name") or item.get("exam_name") or exam_id).strip() or exam_id,
                    "exam_type": exam_type,
                    "question_marks": normalized_q,
                    "question_count": len(normalized_q),
                    "total_marks": total_marks,
                    "duration_minutes": duration_minutes or self._default_duration_minutes(exam_type),
                    "internal_choice": str(item.get("internal_choice", "")).strip() or "No",
                    "assessment_code": item.get("assessment_code") or self._assessment_code(exam_id, exam_type),
                }
            )

        exam_ids = [e.get("exam_id") for e in exams if e.get("exam_id")]
        if len(exam_ids) != len(set(exam_ids)):
            errors.append("exam_id values must be unique")

        config = {
            "fa_method": fa_method or "best_n_of_m",
            "fa_best_n": fa_best_n,
            "threshold_pct": threshold_pct,
            "fa_weight": fa_weight,
            "sa_weight": sa_weight,
            "direct_weight": direct_weight,
            "indirect_weight": indirect_weight,
            "target_level": target_level,
            "exams": exams,
        }
        return config, errors

    def _extract_question_mapping(self, payload: Dict[str, Any], state: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        errors: List[str] = []
        rows = payload.get("question_mapping")
        if not isinstance(rows, list) or not rows:
            return [], ["question_mapping must be a non-empty list"]

        exam_config = state.get("exam_config") or state.get("pending_exam_config") or {}
        exams = exam_config.get("exams") or []
        exam_lookup = {str(e.get("exam_id", "")).upper(): e for e in exams}
        co_ids = {str(c.get("id", "")).upper() for c in (state.get("cos") or [])}

        mapped: List[Dict[str, Any]] = []
        unique_keys: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                errors.append("each question_mapping row must be an object")
                continue
            exam_id = str(row.get("exam_id", "")).strip().upper()
            question_id = str(row.get("question_id", "")).strip().upper()
            co_id = str(row.get("co_id", "")).strip().upper()
            bt_level = str(row.get("bt_level", "")).strip().upper()
            contribution = row.get("contribution_pct", 100)

            if exam_id not in exam_lookup:
                errors.append(f"exam_id {exam_id} not present in STEP 3 exam configuration")
            if not question_id:
                errors.append("question_id is required")
            if co_id not in co_ids:
                errors.append(f"co_id {co_id} is not a generated CO")
            if bt_level not in {"L1", "L2", "L3", "L4", "L5", "L6"}:
                errors.append(f"bt_level must be L1-L6 for {exam_id}:{question_id}")

            try:
                contribution_pct = float(contribution)
            except Exception:
                contribution_pct = -1
            if contribution_pct <= 0 or contribution_pct > 100:
                errors.append(f"contribution_pct must be in (0,100] for {exam_id}:{question_id}")

            q_key = f"{exam_id}:{question_id}"
            if q_key in unique_keys:
                errors.append(f"duplicate mapping for question {q_key}")
            unique_keys.add(q_key)

            mapped.append(
                {
                    "exam_id": exam_id,
                    "question_id": question_id,
                    "co_id": co_id,
                    "bt_level": bt_level,
                    "contribution_pct": contribution_pct,
                    "question_text": str(row.get("question_text", "")).strip(),
                    "justification": str(row.get("justification", "")).strip(),
                }
            )

        for exam_id, exam in exam_lookup.items():
            for question_id in (exam.get("question_marks") or {}).keys():
                key = f"{exam_id}:{question_id}"
                if key not in unique_keys:
                    errors.append(f"missing STEP 4 mapping for {key}")

        return mapped, errors

    async def _calculate_attainment(self, state: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        exam_config = state.get("exam_config") or {}
        question_mapping = state.get("question_mapping") or []
        cos = state.get("cos") or []
        if not exam_config or not question_mapping or not cos:
            return {
                "status": "calculation_blocked",
                "message": "Cannot compute attainment. STEP 1-4 data must be completed and confirmed first.",
                "workflow_step": 5,
                "session_id": state.get("session_id"),
            }

        marks_data = payload.get("marks_data")
        if not isinstance(marks_data, list) or not marks_data:
            return {
                "status": "marks_data_incomplete",
                "message": "marks_data is required and must include at least one exam.",
                "next_action": "provide_marks",
                "workflow_step": 5,
                "session_id": state.get("session_id"),
            }

        course = await self._get_course_from_state(state)
        total_students = int(getattr(course, "enrolled_students", 0) or 0)
        if total_students <= 0:
            student_ids = {
                str(s.get("student_id", "")).strip()
                for exam in marks_data if isinstance(exam, dict)
                for s in (exam.get("students") or []) if isinstance(s, dict)
            }
            total_students = len([s for s in student_ids if s])

        if total_students <= 0:
            return {
                "status": "marks_data_incomplete",
                "message": "No valid student count available. Provide enrolled students in STEP 1 or marks with student_id.",
                "next_action": "provide_marks",
                "workflow_step": 5,
                "session_id": state.get("session_id"),
            }

        exam_lookup = {str(e.get("exam_id", "")).upper(): e for e in (exam_config.get("exams") or [])}
        map_lookup: Dict[str, Dict[str, Any]] = {
            f"{m.get('exam_id', '').upper()}:{m.get('question_id', '').upper()}": m
            for m in question_mapping
        }
        co_ids = [str(c.get("id", "")).upper() for c in cos]

        missing_items: List[str] = []
        for exam_row in marks_data:
            if not isinstance(exam_row, dict):
                missing_items.append("each marks_data row must be an object")
                continue
            exam_id = str(exam_row.get("exam_id", "")).strip().upper()
            if exam_id not in exam_lookup:
                missing_items.append(f"exam_id {exam_id} missing from STEP 3")
                continue
            if not isinstance(exam_row.get("students"), list):
                missing_items.append(f"students array missing for exam {exam_id}")
                continue
            for student in exam_row.get("students") or []:
                if not isinstance(student, dict):
                    continue
                if not str(student.get("student_id", "")).strip():
                    missing_items.append(f"student_id missing in exam {exam_id}")

        if missing_items:
            return {
                "status": "marks_data_incomplete",
                "errors": missing_items,
                "message": "Marks payload has validation issues. Please fix and resend.",
                "next_action": "provide_marks",
                "workflow_step": 5,
                "session_id": state.get("session_id"),
            }

        await self._persist_marks_payload(state, payload)
        if isinstance(payload.get("indirect_data"), dict):
            await self._persist_indirect_data(state, payload.get("indirect_data") or {})

        threshold_pct = float(exam_config.get("threshold_pct", 40))
        fa_weight = float(exam_config.get("fa_weight", 40))
        sa_weight = float(exam_config.get("sa_weight", 60))
        direct_weight = float(exam_config.get("direct_weight", 80))
        indirect_weight = float(exam_config.get("indirect_weight", 20))
        target_level = int(exam_config.get("target_level", 2))

        co_exam_pass: Dict[str, Dict[str, int]] = {co_id: {} for co_id in co_ids}
        co_exam_att: Dict[str, Dict[str, float]] = {co_id: {} for co_id in co_ids}
        question_perf: Dict[str, List[float]] = {}
        marks_validation_warnings: List[str] = []

        for exam_row in marks_data:
            exam_id = str(exam_row.get("exam_id", "")).strip().upper()
            exam_def = exam_lookup.get(exam_id) or {}
            q_max = exam_def.get("question_marks") or {}
            students = exam_row.get("students") or []

            pass_counts = {co_id: 0 for co_id in co_ids}
            for student in students:
                if not isinstance(student, dict):
                    continue
                is_absent = bool(student.get("absent", False))
                raw_marks = student.get("marks") if isinstance(student.get("marks"), dict) else {}

                co_marks = {co_id: 0.0 for co_id in co_ids}
                co_max_marks = {co_id: 0.0 for co_id in co_ids}
                for q_id, q_max_val in q_max.items():
                    key = f"{exam_id}:{str(q_id).upper()}"
                    q_map = map_lookup.get(key)
                    if not q_map:
                        continue
                    co_id = str(q_map.get("co_id", "")).upper()
                    contribution = float(q_map.get("contribution_pct", 100.0)) / 100.0
                    score_raw = raw_marks.get(q_id)
                    if score_raw is None:
                        score_raw = raw_marks.get(str(q_id).upper())
                    if isinstance(score_raw, str) and score_raw.strip().upper() == "AB":
                        score_val = 0.0
                        is_absent = True
                    else:
                        try:
                            score_val = float(score_raw or 0.0)
                        except Exception:
                            score_val = 0.0
                        if score_val > float(q_max_val):
                            marks_validation_warnings.append(
                                f"{exam_id}:{q_id} score {score_val} exceeded max {q_max_val}; clipped to max"
                            )
                            score_val = float(q_max_val)
                        if score_val < 0:
                            score_val = 0.0

                    co_marks[co_id] = co_marks.get(co_id, 0.0) + (score_val * contribution)
                    co_max_marks[co_id] = co_max_marks.get(co_id, 0.0) + (float(q_max_val) * contribution)

                    q_pct = (score_val / float(q_max_val) * 100.0) if float(q_max_val) > 0 else 0.0
                    question_perf.setdefault(key, []).append(q_pct)

                for co_id in co_ids:
                    max_val = co_max_marks.get(co_id, 0.0)
                    pct = (co_marks.get(co_id, 0.0) / max_val * 100.0) if max_val > 0 else 0.0
                    if (not is_absent) and max_val > 0 and pct >= threshold_pct:
                        pass_counts[co_id] += 1

            for co_id in co_ids:
                co_exam_pass[co_id][exam_id] = pass_counts[co_id]
                co_exam_att[co_id][exam_id] = round((pass_counts[co_id] / total_students) * 100.0, 2)

        fa_exams = [e.get("exam_id") for e in exam_lookup.values() if e.get("exam_type") == "FA"]
        sa_exams = [e.get("exam_id") for e in exam_lookup.values() if e.get("exam_type") == "SA"]
        available_exam_ids = {
            str(x.get("exam_id", "")).strip().upper() for x in marks_data if isinstance(x, dict)
        }
        missing_exams = sorted([eid for eid in exam_lookup.keys() if eid not in available_exam_ids])
        if missing_exams:
            marks_validation_warnings.append(
                "Attainment computed with available exams only. Missing exams: " + ", ".join(missing_exams)
            )

        co_rows: List[Dict[str, Any]] = []
        formula_steps: List[str] = []
        final_lookup: Dict[str, float] = {}
        target_min = _level_min_percent(target_level)

        for co_id in co_ids:
            fa_values = [co_exam_att[co_id][eid] for eid in fa_exams if eid in available_exam_ids]
            sa_values = [co_exam_att[co_id][eid] for eid in sa_exams if eid in available_exam_ids]

            fa_method = exam_config.get("fa_method", "best_n_of_m")
            if fa_method == "best_n_of_m":
                n = int(exam_config.get("fa_best_n", 3))
                selected = sorted(fa_values, reverse=True)[:n]
                fa_att = round(sum(selected) / len(selected), 2) if selected else 0.0
                formula_steps.append(
                    f"{co_id} FA (Best {n}): average({selected}) = {fa_att:.2f}"
                )
            elif fa_method == "weighted_average":
                weights = {"T1": 0.10, "T2": 0.15, "T3": 0.20, "T4": 0.25, "T5": 0.30}
                numerator = 0.0
                denominator = 0.0
                for eid in fa_exams:
                    if eid not in available_exam_ids:
                        continue
                    w = weights.get(eid, 0.0)
                    numerator += co_exam_att[co_id][eid] * w
                    denominator += w
                fa_att = round((numerator / denominator), 2) if denominator > 0 else 0.0
                formula_steps.append(
                    f"{co_id} FA (Weighted): {numerator:.2f}/{denominator:.2f} = {fa_att:.2f}"
                )
            else:
                fa_att = round(sum(fa_values) / len(fa_values), 2) if fa_values else 0.0
                formula_steps.append(
                    f"{co_id} FA (Simple): average({fa_values}) = {fa_att:.2f}"
                )

            if not sa_values:
                sa_att = 0.0
                eff_fa_weight = 100.0
                eff_sa_weight = 0.0
            else:
                sa_att = round(sum(sa_values) / len(sa_values), 2)
                eff_fa_weight = fa_weight
                eff_sa_weight = sa_weight

            direct = round((fa_att * eff_fa_weight + sa_att * eff_sa_weight) / 100.0, 2)
            formula_steps.append(
                f"{co_id} Direct = ({fa_att:.2f}*{eff_fa_weight:.0f} + {sa_att:.2f}*{eff_sa_weight:.0f})/100 = {direct:.2f}"
            )

            indirect_att, indirect_note = self._compute_indirect_for_co(
                co_id=co_id,
                payload=payload.get("indirect_data") if isinstance(payload.get("indirect_data"), dict) else {},
                enrolled=total_students,
                direct_fallback=direct,
            )
            if indirect_note:
                marks_validation_warnings.append(indirect_note)

            final = round((direct * direct_weight + indirect_att * indirect_weight) / 100.0, 1)
            final_lookup[co_id] = final
            level = _attainment_level(final)
            status = "Attained" if level >= target_level else "CAP Required"
            if level < target_level:
                status = "ATTAINMENT GAP"

            co_rows.append(
                {
                    "co": co_id,
                    "fa_att": fa_att,
                    "sa_att": sa_att,
                    "direct": direct,
                    "indirect": indirect_att,
                    "final": final,
                    "level": f"Level {level}",
                    "target": f"Level {target_level}",
                    "status": status,
                }
            )

            formula_steps.append(
                f"{co_id} Final = ({direct:.2f}*{direct_weight:.0f} + {indirect_att:.2f}*{indirect_weight:.0f})/100 = {final:.2f}"
            )

        po_rows, pso_rows = self._compute_po_pso_attainment(state=state, final_lookup=final_lookup, target_level=target_level)
        gap_rows = self._build_gap_analysis(
            co_rows=co_rows,
            target_level=target_level,
            target_min=target_min,
            co_exam_att=co_exam_att,
            question_perf=question_perf,
            question_mapping=question_mapping,
        )

        return {
            "status": "calculation_complete",
            "message": "STEP 5 completed. CO/PO/PSO attainment computed with intermediate formulas.",
            "workflow_step": 5,
            "threshold_pct": threshold_pct,
            "total_students": total_students,
            "co_attainment_table": co_rows,
            "po_attainment_table": po_rows,
            "pso_attainment_table": pso_rows,
            "formula_steps": formula_steps,
            "exam_level_co_attainment": co_exam_att,
            "warnings": marks_validation_warnings,
            "gap_analysis": gap_rows,
            "next_action": "generate_report",
            "session_id": state.get("session_id"),
        }

    def _compute_indirect_for_co(
        self,
        co_id: str,
        payload: Dict[str, Any],
        enrolled: int,
        direct_fallback: float,
    ) -> Tuple[float, Optional[str]]:
        if not payload:
            return round(direct_fallback, 2), "Indirect attainment not available; using direct attainment as final fallback"

        responses = payload.get("responses", 0)
        response_note: Optional[str] = None
        try:
            responses_val = int(responses)
        except Exception:
            responses_val = 0
        if enrolled > 0 and responses_val > 0 and (responses_val / enrolled) < 0.60:
            response_note = f"Indirect response rate for {co_id} below 60% ({responses_val}/{enrolled})"

        co_mean = payload.get("co_mean_ratings")
        if isinstance(co_mean, dict) and co_id in co_mean:
            try:
                mean_rating = float(co_mean[co_id])
            except Exception:
                mean_rating = 0.0
            mean_rating = max(0.0, min(5.0, mean_rating))
            return round((mean_rating / 5.0) * 100.0, 2), response_note

        co_dist = payload.get("co_rating_distribution")
        if isinstance(co_dist, dict) and isinstance(co_dist.get(co_id), dict):
            dist = co_dist[co_id]
            total = 0.0
            weighted = 0.0
            for rating in [1, 2, 3, 4, 5]:
                count_raw = dist.get(str(rating), dist.get(rating, 0))
                try:
                    count_val = float(count_raw)
                except Exception:
                    count_val = 0.0
                weighted += rating * count_val
                total += count_val
            if total > 0:
                mean_rating = weighted / total
                return round((mean_rating / 5.0) * 100.0, 2), response_note

        return round(direct_fallback, 2), "Indirect data missing per-CO rating; using direct attainment as fallback"

    def _compute_po_pso_attainment(
        self,
        state: Dict[str, Any],
        final_lookup: Dict[str, float],
        target_level: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        mapping_matrix = state.get("confirmed_mapping_matrix") or {}
        pso_mapping_matrix = state.get("confirmed_pso_mapping_matrix") or {}
        pos = state.get("session_pos") or []
        psos = state.get("session_psos") or []

        po_rows: List[Dict[str, Any]] = []
        for po in pos:
            po_code = str(po.get("code") or po.get("id") or "").upper()
            numerator = 0.0
            denominator = 0.0
            mapped_co: List[str] = []
            for co_id, final in final_lookup.items():
                weight = mapping_matrix.get(f"{co_id}_{po_code}", 0)
                if isinstance(weight, int) and weight > 0:
                    numerator += final * weight
                    denominator += float(weight)
                    mapped_co.append(f"{co_id}({weight})")
            att = round((numerator / denominator), 2) if denominator > 0 else 0.0
            att = round(att, 1)
            level = _attainment_level(att)
            status = "Met" if level >= target_level else "CAP Required"
            po_rows.append(
                {
                    "po": po_code,
                    "description": str(po.get("statement", ""))[:120],
                    "mapped_cos": mapped_co,
                    "attainment": att,
                    "level": f"Level {level}",
                    "target": f"Level {target_level}",
                    "status": status,
                }
            )

        pso_rows: List[Dict[str, Any]] = []
        for pso in psos:
            pso_code = str(pso.get("code") or pso.get("id") or "").upper()
            numerator = 0.0
            denominator = 0.0
            mapped_co: List[str] = []
            for co_id, final in final_lookup.items():
                weight = pso_mapping_matrix.get(f"{co_id}_{pso_code}", 0)
                if isinstance(weight, int) and weight > 0:
                    numerator += final * weight
                    denominator += float(weight)
                    mapped_co.append(f"{co_id}({weight})")
            att = round((numerator / denominator), 2) if denominator > 0 else 0.0
            att = round(att, 1)
            level = _attainment_level(att)
            status = "Met" if level >= target_level else "CAP Required"
            pso_rows.append(
                {
                    "pso": pso_code,
                    "description": str(pso.get("statement", ""))[:120],
                    "mapped_cos": mapped_co,
                    "attainment": att,
                    "level": f"Level {level}",
                    "target": f"Level {target_level}",
                    "status": status,
                }
            )

        return po_rows, pso_rows

    def _build_gap_analysis(
        self,
        co_rows: List[Dict[str, Any]],
        target_level: int,
        target_min: float,
        co_exam_att: Dict[str, Dict[str, float]],
        question_perf: Dict[str, List[float]],
        question_mapping: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        gap_rows: List[Dict[str, Any]] = []
        for row in co_rows:
            co_id = str(row.get("co", ""))
            final_val = float(row.get("final", 0.0) or 0.0)
            level = _attainment_level(final_val)
            if level >= target_level:
                continue

            gap_pct = max(0.0, target_min - final_val)
            if gap_pct > 15.0:
                severity = "Level 3 gap"
                actions = [
                    "Redesign CO statement",
                    "Change teaching method",
                    "Add remedial class",
                ]
            elif gap_pct >= 10.0:
                severity = "Level 2 gap"
                actions = [
                    "Add more practice problems",
                    "Increase feedback frequency",
                ]
            else:
                severity = "Level 1 gap"
                actions = [
                    "Adjust question difficulty",
                    "Tune marking scheme",
                ]

            exam_breakdown = co_exam_att.get(co_id, {})
            weak_exams = sorted(exam_breakdown.items(), key=lambda x: x[1])[:2]

            weak_questions: List[str] = []
            for qm in question_mapping:
                if str(qm.get("co_id", "")).upper() != co_id.upper():
                    continue
                key = f"{str(qm.get('exam_id', '')).upper()}:{str(qm.get('question_id', '')).upper()}"
                vals = question_perf.get(key, [])
                if vals:
                    avg_pct = sum(vals) / len(vals)
                    if avg_pct < 50.0:
                        weak_questions.append(f"{key} ({avg_pct:.1f}%)")

            gap_rows.append(
                {
                    "co": co_id,
                    "achieved": round(final_val, 2),
                    "target_level": f"Level {target_level}",
                    "severity": severity,
                    "weak_exams": [f"{e}={v:.1f}%" for e, v in weak_exams],
                    "weak_questions": weak_questions[:5],
                    "suggested_actions": actions,
                }
            )
        return gap_rows

    def _extract_course_fields(self, text: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        patterns = {
            "course_name": r"course\s*name\s*[:\-]\s*(.+)",
            "course_code": r"course\s*code\s*[:\-]\s*([A-Za-z0-9]{1,20})",
            "department": r"department\s*[:\-]\s*(.+)",
            "semester": r"semester\s*[:\-]\s*(\d+)",
            "credits": r"credits?\s*[:\-]\s*(\d+)",
            "total_students": r"(?:total\s*students|students)\s*[:\-]\s*(\d+)",
            "num_cos": r"(?:number\s*of\s*cos?\s*(?:needed|required)?|num(?:ber)?\s*of\s*co?s?\s*(?:needed|required)?)\s*[:\-]\s*(\d+)",
        }
        for key, pattern in patterns.items():
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                fields[key] = m.group(1).strip()
        return fields

    def _validate_course_fields(self, fields: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        valid: Dict[str, Any] = {}
        failures: List[str] = []

        name = (fields.get("course_name") or "").strip()
        if name:
            valid["course_name"] = name
        else:
            failures.append("course_name")

        code = (fields.get("course_code") or "").strip().upper()
        if re.fullmatch(r"[A-Za-z0-9]{1,10}", code or ""):
            valid["course_code"] = code
        else:
            failures.append("course_code")

        department = (fields.get("department") or "").strip()
        if department:
            valid["department"] = department

        semester_raw = fields.get("semester")
        if str(semester_raw or "").isdigit() and 1 <= int(semester_raw) <= 8:
            valid["semester"] = int(semester_raw)
        else:
            failures.append("semester")

        credits_raw = fields.get("credits")
        if str(credits_raw or "").isdigit() and 1 <= int(credits_raw) <= 6:
            valid["credits"] = int(credits_raw)
        else:
            failures.append("credits")

        students_raw = fields.get("total_students")
        if str(students_raw or "").isdigit() and int(students_raw) > 0:
            valid["total_students"] = int(students_raw)
        else:
            failures.append("total_students")

        num_cos_raw = fields.get("num_cos")
        if str(num_cos_raw or "").isdigit() and 4 <= int(num_cos_raw) <= 6:
            valid["num_cos"] = int(num_cos_raw)
        else:
            valid["num_cos"] = 5

        return valid, failures

    def _build_missing_fields_prompt(self, fields: List[str]) -> str:
        hints = {
            "course_name": "course_name (non-empty)",
            "course_code": "course_code (alphanumeric, max 10 chars)",
            "semester": "semester (1-8)",
            "credits": "credits (1-6)",
            "total_students": "total_students (>0)",
        }
        needed = [hints.get(f, f) for f in fields]
        return "Please provide only these fields again: " + ", ".join(needed)

    async def _resolve_course(
        self,
        validated: Dict[str, Any],
        state: Dict[str, Any],
        course_hint: Optional[str],
    ) -> Optional[Course]:
        course: Optional[Course] = None

        if state.get("course_db_id"):
            result = await self.session.execute(select(Course).where(Course.id == state["course_db_id"]))
            course = result.scalar_one_or_none()

        if not course and course_hint:
            result = await self.session.execute(
                select(Course).where((Course.id == course_hint) | (Course.course_code == course_hint))
            )
            candidate = result.scalar_one_or_none()
            if candidate and self._can_access_course(candidate):
                course = candidate

        code = validated.get("course_code")
        if not course and code:
            result = await self.session.execute(select(Course).where(Course.course_code == code))
            candidate = result.scalar_one_or_none()
            if candidate and self._can_access_course(candidate):
                course = candidate

        if not course:
            required = {"course_name", "course_code", "semester", "credits", "total_students"}
            if required.issubset(set(validated.keys())):
                course = Course(
                    id=str(uuid.uuid4()),
                    course_code=validated["course_code"],
                    course_name=validated["course_name"],
                    semester=int(validated["semester"]),
                    credits=int(validated["credits"]),
                    department=validated.get("department") or "General",
                    enrolled_students=int(validated["total_students"]),
                    created_by=self.user_id,
                )
                self.session.add(course)
        return course

    def _can_access_course(self, course: Course) -> bool:
        if self.user_role in {"admin", "hod", "course_lead", "subject_lead"}:
            return True
        return str(course.created_by or "") == str(self.user_id)

    def _apply_course_updates(self, course: Course, validated: Dict[str, Any]) -> None:
        if "course_name" in validated:
            course.course_name = validated["course_name"]
        if "course_code" in validated:
            course.course_code = validated["course_code"]
        if "department" in validated:
            course.department = validated["department"] or "General"
        elif not course.department:
            course.department = "General"
        if "semester" in validated:
            course.semester = int(validated["semester"])
        if "credits" in validated:
            course.credits = int(validated["credits"])
        if "total_students" in validated:
            course.enrolled_students = int(validated["total_students"])

    async def _get_course_from_state(self, state: Dict[str, Any]) -> Optional[Course]:
        course_id = state.get("course_db_id")
        if not course_id:
            return None
        result = await self.session.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if course and self._can_access_course(course):
            return course
        return None

    def _parse_units(self, syllabus: str) -> List[Dict[str, Any]]:
        units: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None

        # Normalize line endings and split inline unit headers
        normalized = (syllabus or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(
            r"(?i)(?<!^)(?<!\n)\s*((?:unit|module|chapter)\s*\d+\b)",
            r"\n\1",
            normalized,
        )
        lines = [ln.strip() for ln in normalized.splitlines() if ln.strip()]

        unit_header = re.compile(r"^(unit|module|chapter)\s*(\d+)\s*[:\-]?\s*(.*)$", re.IGNORECASE)
        for line in lines:
            m = unit_header.match(line)
            if m:
                if current:
                    units.append(current)
                label = m.group(1).upper().rstrip("S")
                idx = m.group(2)
                title_suffix = (m.group(3) or "").strip()
                # Strip trailing hours annotation from title
                title_suffix_clean = re.split(r"\s*(?:->|→)\s*", title_suffix, maxsplit=1)[0].strip()
                title = f"{label} {idx}"
                if title_suffix_clean:
                    title = f"{title}: {title_suffix_clean}"

                # Extract hours: "(10 hours)" or "10 Hrs" or "10 hours"
                hours: Optional[int] = None
                hours_m = re.search(r"\(\s*(\d{1,3})\s*(?:hours?|hrs?)\s*\)", line, re.IGNORECASE)
                if not hours_m:
                    hours_m = re.search(r"\b(\d{1,3})\s*(?:hours?|hrs?)\b", line, re.IGNORECASE)
                if hours_m:
                    try:
                        hours = int(hours_m.group(1))
                    except Exception:
                        hours = None

                current = {"unit": title, "topics": []}
                if hours is not None:
                    current["hours"] = hours
                continue

            if current is None:
                current = {"unit": "UNIT 1", "topics": []}

            topic = re.sub(r"^[\-\*\d\.\)\(\s]+", "", line).strip()
            if topic:
                current["topics"].append(topic)

        if current:
            units.append(current)

        if not units:
            units.append({"unit": "UNIT 1", "topics": [syllabus[:300]]})
        return units

    def _units_covered(self, co_statement: str, units: List[Dict[str, Any]]) -> List[str]:
        co_kw = _tokens(co_statement)
        covered: List[str] = []
        for unit in units:
            unit_text = " ".join(unit.get("topics", [])) + " " + unit.get("unit", "")
            unit_kw = _tokens(unit_text)
            if len(co_kw & unit_kw) >= 2:
                covered.append(unit.get("unit", ""))
        if not covered and units:
            covered.append(units[0].get("unit", "UNIT 1"))
        return covered

    def _normalize_co_statement(self, statement: str, bt_level: str) -> str:
        cleaned = re.sub(r"\s+", " ", (statement or "").strip())
        if not cleaned:
            return f"Students will be able to {_BT_DEFAULT_VERB.get(bt_level, 'explain')} core concepts in given context"

        # Only prepend the prefix if missing — do NOT replace the LLM's chosen verb
        if not re.search(r"^students\s+will\s+be\s+able\s+to\s+", cleaned, flags=re.IGNORECASE):
            cleaned = f"Students will be able to {cleaned[0].lower() + cleaned[1:] if len(cleaned) > 1 else cleaned.lower()}"
        return cleaned

    def _analyze_unit_complexity(self, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        analysis: List[Dict[str, Any]] = []
        level_order = ["L1", "L2", "L3", "L4", "L5", "L6"]

        # Determine max hours across all units for priority boosting
        hours_values = [int(u["hours"]) for u in units if isinstance(u.get("hours"), int)]
        max_hours = max(hours_values) if hours_values else None

        for unit in units:
            unit_name = str(unit.get("unit", "")).strip() or "UNIT"
            topics = unit.get("topics", []) or []
            hours = unit.get("hours")
            text_blob = _norm_text(unit_name + " " + " ".join(str(t) for t in topics))

            scores: Dict[str, int] = {lvl: 0 for lvl in level_order}
            matches: Dict[str, List[str]] = {lvl: [] for lvl in level_order}
            for lvl in level_order:
                for cue in _UNIT_COMPLEXITY_CUES[lvl]:
                    if re.search(rf"\b{re.escape(cue)}\b", text_blob):
                        scores[lvl] += 1
                        matches[lvl].append(cue)

            if all(v == 0 for v in scores.values()):
                scores["L3"] = 1

            dominant = max(level_order, key=lambda lvl: (scores[lvl], level_order.index(lvl)))

            # Hour-weighting rule: units with max hours must have at least L3 (apply)
            # Design/algorithm topics (L6 cues present) stay at L6 regardless
            if max_hours is not None and isinstance(hours, int) and hours == max_hours:
                dominant_idx = level_order.index(dominant)
                if dominant_idx < level_order.index("L3"):
                    dominant = "L3"

            complexity_score = int(dominant[1])
            is_priority = max_hours is not None and isinstance(hours, int) and hours == max_hours
            analysis.append(
                {
                    "unit": unit_name,
                    "topics": topics,
                    "hours": hours,
                    "complexity_score": complexity_score,
                    "bt_level": dominant,
                    "bloom_level": _L_TO_BLOOM[dominant],
                    "suggested_action_verb": _BT_DEFAULT_VERB[dominant],
                    "evidence_keywords": matches[dominant][:5],
                    "is_priority": is_priority,
                }
            )
        return analysis

    async def _load_course_cos(self, course_id: str) -> List[Dict[str, Any]]:
        rows = (await self.session.execute(
            select(CourseOutcome).where(CourseOutcome.course_id == course_id).order_by(CourseOutcome.code)
        )).scalars().all()
        return [{"id": co.code, "db_id": co.id, "statement": co.statement} for co in rows]

    def _extract_po_pso(self, text: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        pos: List[Dict[str, str]] = []
        psos: List[Dict[str, str]] = []

        if "nba standard" in text.lower() and "po" in text.lower():
            pos = list(NBA_STANDARD_POS)

        po_matches = re.findall(
            r"(PO\s*\d{1,2})\s*[:\-]\s*(.+?)(?=(?:\s+PO\s*\d{1,2}\s*[:\-])|(?:\s+PSO\s*\d+\s*[:\-])|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for code, stmt in po_matches:
            code_norm = re.sub(r"\s+", "", code).upper()
            pos.append({"code": code_norm, "statement": re.sub(r"\s+", " ", stmt).strip()})

        pso_matches = re.findall(
            r"(PSO\s*\d{1,2})\s*[:\-]\s*(.+?)(?=(?:\s+PSO\s*\d{1,2}\s*[:\-])|$)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for code, stmt in pso_matches:
            code_norm = re.sub(r"\s+", "", code).upper()
            psos.append({"code": code_norm, "statement": re.sub(r"\s+", " ", stmt).strip()})

        if pos:
            pos = self._dedupe_outcomes(pos)
        if psos:
            psos = self._dedupe_outcomes(psos)
        return pos, psos

    def _dedupe_outcomes(self, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        by_code: Dict[str, Dict[str, str]] = {}
        for item in items:
            code = str(item.get("code", "")).strip().upper()
            stmt = str(item.get("statement", "")).strip()
            if code and stmt:
                by_code[code] = {"code": code, "statement": stmt}
        return [by_code[k] for k in sorted(by_code.keys())]

    async def _resolve_po_sources(
        self,
        text: str,
        course: Course,
        incoming_pos: List[Dict[str, str]],
        incoming_psos: List[Dict[str, str]],
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        department = (course.department or "General").strip() or "General"
        dept_key = f"DEPT:{department.upper()}"
        course_key = f"COURSE:{course.id}"

        override_pos = await self._get_program_outcomes(course_key)
        override_psos = await self._get_program_specific_outcomes(course_key)
        if override_pos or override_psos:
            return {"pos_rows": override_pos, "pso_rows": override_psos}

        master_pos = await self._get_program_outcomes(dept_key)
        master_psos = await self._get_program_specific_outcomes(dept_key)

        # No incoming list: default to master if exists.
        if not incoming_pos and not incoming_psos:
            if master_pos or master_psos:
                return {"pos_rows": master_pos, "pso_rows": master_psos}
            return {
                "status": "po_pso_missing",
                "message": "No department PO or PSO master found. Provide PO/PSO list in this message.",
                "next_action": "provide_po_pso",
                "session_id": state["session_id"],
            }

        explicit_course_only = "just for this course" in text.lower()
        explicit_update_master = any(k in text.lower() for k in ["update", "replace", "save as master"])
        explicit_use_saved = any(k in text.lower() for k in ["use saved", "use master", "keep saved"])

        if master_pos or master_psos:
            if explicit_use_saved:
                return {"pos_rows": master_pos, "pso_rows": master_psos}

            incoming_matches_master = self._same_outcomes(incoming_pos, master_pos) and self._same_outcomes(incoming_psos, master_psos)
            if incoming_matches_master:
                return {"pos_rows": master_pos, "pso_rows": master_psos}

            if explicit_course_only:
                pos_rows = await self._replace_program_outcomes(course_key, incoming_pos)
                pso_rows = await self._replace_program_specific_outcomes(course_key, incoming_psos)
                return {"pos_rows": pos_rows, "pso_rows": pso_rows}

            if explicit_update_master:
                pos_rows = await self._replace_program_outcomes(dept_key, incoming_pos)
                pso_rows = await self._replace_program_specific_outcomes(dept_key, incoming_psos)
                return {"pos_rows": pos_rows, "pso_rows": pso_rows}

            return {
                "status": "need_choice",
                "message": "Your department already has saved POs/PSOs. Reply with 'use saved version', 'update with new list', or 'just for this course'.",
                "next_action": "choose_master_or_update",
                "session_id": state["session_id"],
            }

        # First-time master save.
        pos_rows = await self._replace_program_outcomes(dept_key, incoming_pos)
        pso_rows = await self._replace_program_specific_outcomes(dept_key, incoming_psos)
        return {"pos_rows": pos_rows, "pso_rows": pso_rows}

    async def _resolve_po_choice(
        self,
        text: str,
        course: Course,
        incoming_pos: List[Dict[str, str]],
        incoming_psos: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        lower = text.lower()
        department = (course.department or "General").strip() or "General"
        dept_key = f"DEPT:{department.upper()}"
        course_key = f"COURSE:{course.id}"

        if any(k in lower for k in ["use saved", "use master", "keep saved"]):
            return {
                "pos_rows": await self._get_program_outcomes(dept_key),
                "pso_rows": await self._get_program_specific_outcomes(dept_key),
            }

        if "just for this course" in lower:
            return {
                "pos_rows": await self._replace_program_outcomes(course_key, incoming_pos),
                "pso_rows": await self._replace_program_specific_outcomes(course_key, incoming_psos),
            }

        if any(k in lower for k in ["update", "replace", "save as master"]):
            return {
                "pos_rows": await self._replace_program_outcomes(dept_key, incoming_pos),
                "pso_rows": await self._replace_program_specific_outcomes(dept_key, incoming_psos),
            }

        return {
            "status": "need_choice",
            "message": "Reply exactly with: use saved version, update with new list, or just for this course.",
            "next_action": "choose_master_or_update",
        }

    def _same_outcomes(self, incoming: List[Dict[str, str]], existing_rows: List[Any]) -> bool:
        if not incoming and not existing_rows:
            return True
        incoming_norm = sorted((x["code"].upper(), _norm_text(x["statement"])) for x in incoming)
        existing_norm = sorted((x.code.upper(), _norm_text(x.statement)) for x in existing_rows)
        return incoming_norm == existing_norm

    async def _get_program_outcomes(self, program_key: str) -> List[ProgramOutcome]:
        rows = (await self.session.execute(
            select(ProgramOutcome).where(ProgramOutcome.program == program_key).order_by(ProgramOutcome.code)
        )).scalars().all()
        return list(rows)

    async def _get_program_specific_outcomes(self, program_key: str) -> List[ProgramSpecificOutcome]:
        rows = (await self.session.execute(
            select(ProgramSpecificOutcome).where(ProgramSpecificOutcome.program == program_key).order_by(ProgramSpecificOutcome.code)
        )).scalars().all()
        return list(rows)

    async def _replace_program_outcomes(self, program_key: str, items: List[Dict[str, str]]) -> List[ProgramOutcome]:
        clean = self._dedupe_outcomes(items)
        await self.session.execute(delete(ProgramOutcome).where(ProgramOutcome.program == program_key))
        created: List[ProgramOutcome] = []
        for item in clean:
            po = ProgramOutcome(
                id=str(uuid.uuid4()),
                code=item["code"],
                statement=item["statement"],
                program=program_key,
            )
            self.session.add(po)
            created.append(po)
        await self.session.flush()
        await self.session.commit()
        return created

    async def _replace_program_specific_outcomes(self, program_key: str, items: List[Dict[str, str]]) -> List[ProgramSpecificOutcome]:
        clean = self._dedupe_outcomes(items)
        await self.session.execute(delete(ProgramSpecificOutcome).where(ProgramSpecificOutcome.program == program_key))
        created: List[ProgramSpecificOutcome] = []
        for item in clean:
            pso = ProgramSpecificOutcome(
                id=str(uuid.uuid4()),
                code=item["code"],
                statement=item["statement"],
                program=program_key,
            )
            self.session.add(pso)
            created.append(pso)
        await self.session.flush()
        await self.session.commit()
        return created

    async def _generate_mapping(
        self,
        cos: List[Dict[str, Any]],
        pos: List[Dict[str, Any]],
        psos: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        prompt = self._build_mapping_prompt(cos, pos, psos)
        ai_payload: Dict[str, Any] = {}
        try:
            text = await self.llm.generate_completion(prompt=prompt)
            if text:
                parsed = _extract_json(text)
                if isinstance(parsed, dict):
                    ai_payload = parsed
        except Exception as exc:
            logger.warning(f"Mapping AI parse failed, fallback used: {exc}")

        mapping_entries = ai_payload.get("mapping") if isinstance(ai_payload, dict) else None
        pso_entries = ai_payload.get("pso_mapping") if isinstance(ai_payload, dict) else None

        if not isinstance(mapping_entries, list):
            mapping_entries = self._fallback_po_mapping(cos, pos)
        if not isinstance(pso_entries, list):
            pso_entries = self._fallback_pso_mapping(cos, psos)

        mapping_matrix: Dict[str, Any] = {}
        for co in cos:
            for po in pos:
                mapping_matrix[f"{co['id']}_{po['id']}"] = 0

        flat_mapping: List[Dict[str, Any]] = []
        for item in mapping_entries:
            co_id = str(item.get("co_id", "")).strip().upper()
            po_id = str(item.get("po_id", "")).strip().upper()
            corr = item.get("correlation", 0)
            if isinstance(corr, str) and corr.strip().isdigit():
                corr = int(corr.strip())
            key = f"{co_id}_{po_id}"
            if key in mapping_matrix:
                mapping_matrix[key] = corr
                flat_mapping.append({
                    "co_id": co_id,
                    "po_id": po_id,
                    "correlation": corr,
                    "reason": str(item.get("reason", "")).strip(),
                })

        pso_mapping_matrix: Dict[str, int] = {}
        pso_flat: List[Dict[str, Any]] = []
        for co in cos:
            for pso in psos:
                pso_mapping_matrix[f"{co['id']}_{pso['id']}"] = 0

        for item in pso_entries:
            co_id = str(item.get("co_id", "")).strip().upper()
            pso_id = str(item.get("pso_id", "")).strip().upper()
            corr = item.get("correlation", 0)
            if isinstance(corr, str) and corr.strip().isdigit():
                corr = int(corr.strip())
            key = f"{co_id}_{pso_id}"
            if key in pso_mapping_matrix:
                pso_mapping_matrix[key] = max(0, min(3, int(corr))) if str(corr).lstrip("-").isdigit() else 0
                pso_flat.append({
                    "co_id": co_id,
                    "pso_id": pso_id,
                    "correlation": pso_mapping_matrix[key],
                    "reason": str(item.get("reason", "")).strip(),
                })

        return {
            "mapping_matrix": mapping_matrix,
            "pso_mapping_matrix": pso_mapping_matrix,
            "flat_mapping": flat_mapping,
            "flat_pso_mapping": pso_flat,
        }

    def _build_mapping_prompt(self, cos: List[Dict[str, Any]], pos: List[Dict[str, Any]], psos: List[Dict[str, Any]]) -> str:
        co_lines = "\n".join(f"- {c['id']}: {c.get('statement', '')}" for c in cos)
        po_lines = "\n".join(f"- {p['id']}: {p.get('statement', '')}" for p in pos)
        pso_lines = "\n".join(f"- {p['id']}: {p.get('statement', '')}" for p in psos)
        return (
            "Given these COs, POs, and PSOs, produce an NBA-aligned mapping matrix.\n"
            "Correlation rubric: 3=High (direct, substantial), 2=Medium (partial), 1=Low (indirect), 0=None.\n"
            "Use correlation 0 when there is no meaningful relation; do not over-map.\n"
            "Each reason must cite key PO/PSO intent and how CO action verb/topic supports that intent.\n"
            "Return strict JSON only with this schema:\n"
            "{\n"
            "  \"mapping\": [{\"co_id\":\"CO1\",\"po_id\":\"PO1\",\"correlation\":0|1|2|3,\"reason\":\"...\"}],\n"
            "  \"pso_mapping\": [{\"co_id\":\"CO1\",\"pso_id\":\"PSO1\",\"correlation\":0|1|2|3,\"reason\":\"...\"}]\n"
            "}\n"
            "COs:\n"
            f"{co_lines}\n\n"
            "POs:\n"
            f"{po_lines}\n\n"
            "PSOs:\n"
            f"{pso_lines}\n"
        )

    def _fallback_po_mapping(self, cos: List[Dict[str, Any]], pos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for co in cos:
            co_kw = _tokens(str(co.get("statement", "")))
            scored: List[Tuple[str, float, List[str]]] = []
            for po in pos:
                po_kw = _tokens(str(po.get("statement", "")))
                overlap = sorted(list(co_kw & po_kw))
                union = len(co_kw | po_kw) or 1
                score = len(overlap) / union
                scored.append((po["id"], score, overlap))
            scored.sort(key=lambda x: x[1], reverse=True)

            for po_id, score, overlap in scored:
                corr = 0
                if score >= 0.35:
                    corr = 3
                elif score >= 0.20:
                    corr = 2
                elif score >= 0.10:
                    corr = 1
                if corr > 0:
                    reason = "Shared topics: " + ", ".join(overlap[:3]) if overlap else "Semantic overlap"
                    result.append({"co_id": co["id"], "po_id": po_id, "correlation": corr, "reason": reason})
        return result

    def _fallback_pso_mapping(self, cos: List[Dict[str, Any]], psos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for co in cos:
            co_kw = _tokens(str(co.get("statement", "")))
            scored: List[Tuple[str, float, List[str]]] = []
            for pso in psos:
                p_kw = _tokens(str(pso.get("statement", "")))
                overlap = sorted(list(co_kw & p_kw))
                union = len(co_kw | p_kw) or 1
                score = len(overlap) / union
                scored.append((pso["id"], score, overlap))
            scored.sort(key=lambda x: x[1], reverse=True)

            for pso_id, score, overlap in scored:
                corr = 0
                if score >= 0.35:
                    corr = 3
                elif score >= 0.20:
                    corr = 2
                elif score >= 0.10:
                    corr = 1
                if corr > 0:
                    reason = "Shared topics: " + ", ".join(overlap[:3]) if overlap else "Semantic overlap"
                    result.append({"co_id": co["id"], "pso_id": pso_id, "correlation": corr, "reason": reason})
        return result

    async def _persist_mapping(
        self,
        course_id: str,
        cos: List[Dict[str, Any]],
        pos_rows: List[ProgramOutcome],
        pso_rows: List[ProgramSpecificOutcome],
        mapping_result: Dict[str, Any],
    ) -> None:
        co_code_to_db = {c["id"]: c["db_id"] for c in cos}
        po_code_to_id = {p.code: p.id for p in pos_rows}
        pso_code_to_id = {p.code: p.id for p in pso_rows}

        co_db_ids = list(co_code_to_db.values())
        if co_db_ids:
            await self.session.execute(
                delete(co_po_mapping_table).where(co_po_mapping_table.c.course_outcome_id.in_(co_db_ids))
            )
            await self.session.execute(
                delete(co_pso_mapping_table).where(co_pso_mapping_table.c.course_outcome_id.in_(co_db_ids))
            )

        for cell, raw_val in mapping_result.get("mapping_matrix", {}).items():
            try:
                co_code, po_code = cell.split("_", 1)
            except ValueError:
                continue
            if co_code not in co_code_to_db or po_code not in po_code_to_id:
                continue
            if not isinstance(raw_val, int) or raw_val <= 0:
                continue
            level = max(1, min(3, raw_val))
            await self.session.execute(
                co_po_mapping_table.insert().values(
                    course_outcome_id=co_code_to_db[co_code],
                    program_outcome_id=po_code_to_id[po_code],
                    similarity_score=float(level) / 3.0,
                )
            )

        for cell, raw_val in mapping_result.get("pso_mapping_matrix", {}).items():
            try:
                co_code, pso_code = cell.split("_", 1)
            except ValueError:
                continue
            if co_code not in co_code_to_db or pso_code not in pso_code_to_id:
                continue
            if not isinstance(raw_val, int) or raw_val <= 0:
                continue
            level = max(1, min(3, raw_val))
            await self.session.execute(
                co_pso_mapping_table.insert().values(
                    course_outcome_id=co_code_to_db[co_code],
                    program_specific_outcome_id=pso_code_to_id[pso_code],
                    similarity_score=float(level) / 3.0,
                )
            )

        await self.session.commit()

    def _build_mapping_summary(
        self,
        validation: Dict[str, Any],
        mapping_result: Dict[str, Any],
        cos: List[Dict[str, Any]],
        psos: List[Dict[str, Any]],
    ) -> str:
        po_nonzero = int(validation.get("nonzero_cells", 0))
        po_total = int(validation.get("total_cells", 0))
        pso_nonzero = sum(
            1 for v in (mapping_result.get("pso_mapping_matrix") or {}).values()
            if isinstance(v, int) and v > 0
        )
        pso_total = len(cos) * len(psos)
        nonzero = po_nonzero + pso_nonzero
        total = po_total + pso_total

        co_with_mapping = set()
        for cell, v in (mapping_result.get("mapping_matrix") or {}).items():
            if isinstance(v, int) and v > 0:
                co_with_mapping.add(cell.split("_", 1)[0])

        pso_counts: Dict[str, int] = {}
        for cell, v in (mapping_result.get("pso_mapping_matrix") or {}).items():
            if isinstance(v, int) and v > 0:
                _, pso_id = cell.split("_", 1)
                pso_counts[pso_id] = pso_counts.get(pso_id, 0) + 1

        pso_ok = [p for p in psos if pso_counts.get(p.get("id"), 0) >= 2]
        return (
            f"{nonzero} of {total} cells mapped. "
            f"{len(co_with_mapping)} of {len(cos)} COs have >=1 PO mapping. "
            f"{len(pso_ok)} PSOs have >=2 mappings."
        )

    def _combined_matrix_density(
        self,
        cos: List[Dict[str, Any]],
        pos: List[Dict[str, Any]],
        psos: List[Dict[str, Any]],
        mapping_result: Dict[str, Any],
    ) -> float:
        total_cells = len(cos) * (len(pos) + len(psos))
        if total_cells <= 0:
            return 0.0
        nonzero_po = sum(
            1 for v in (mapping_result.get("mapping_matrix") or {}).values()
            if isinstance(v, int) and v > 0
        )
        nonzero_pso = sum(
            1 for v in (mapping_result.get("pso_mapping_matrix") or {}).values()
            if isinstance(v, int) and v > 0
        )
        return round((nonzero_po + nonzero_pso) / total_cells, 4)

    def _validate_pso_coverage(
        self,
        cos: List[Dict[str, Any]],
        psos: List[Dict[str, Any]],
        mapping_result: Dict[str, Any],
    ) -> List[str]:
        warnings: List[str] = []
        matrix = mapping_result.get("pso_mapping_matrix") or {}
        for pso in psos:
            pso_id = str(pso.get("id", "")).strip()
            mapped_cos = 0
            for co in cos:
                co_id = str(co.get("id", "")).strip()
                val = matrix.get(f"{co_id}_{pso_id}", 0)
                if isinstance(val, int) and val > 0:
                    mapped_cos += 1
            if mapped_cos < 2:
                warnings.append(f"{pso_id} has mappings from only {mapped_cos} CO(s) - recommended >=2")
        return warnings

    def _is_confirm(self, lower_text: str) -> bool:
        return bool(re.search(r"\bconfirm\b", lower_text))

    def _is_edit(self, lower_text: str) -> bool:
        return bool(re.search(r"\bedit\b|\bfix\b|\bchange\b", lower_text))

    async def _load_program_outcomes_for_context(self, course: Course, state: Dict[str, Any]) -> List[ProgramOutcome]:
        course_key = f"COURSE:{course.id}"
        override = await self._get_program_outcomes(course_key)
        if override:
            return override
        dept = (course.department or "General").strip() or "General"
        return await self._get_program_outcomes(f"DEPT:{dept.upper()}")

    async def _load_program_specific_outcomes_for_context(self, course: Course, state: Dict[str, Any]) -> List[ProgramSpecificOutcome]:
        course_key = f"COURSE:{course.id}"
        override = await self._get_program_specific_outcomes(course_key)
        if override:
            return override
        dept = (course.department or "General").strip() or "General"
        return await self._get_program_specific_outcomes(f"DEPT:{dept.upper()}")


async def validate_course_matrix_before_save(session: AsyncSession, course_id: str) -> Dict[str, Any]:
    course_result = await session.execute(select(Course).where(Course.id == course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        return {"errors": ["Course not found"], "warnings": [], "can_save": False, "matrix_density": 0.0}

    cos_rows = (await session.execute(
        select(CourseOutcome).where(CourseOutcome.course_id == course_id).order_by(CourseOutcome.code)
    )).scalars().all()
    cos = [{"id": co.code, "statement": co.statement, "db_id": co.id} for co in cos_rows]

    dept_key = f"DEPT:{((course.department or 'General').strip() or 'General').upper()}"
    pos_rows = (await session.execute(
        select(ProgramOutcome).where(ProgramOutcome.program == dept_key).order_by(ProgramOutcome.code)
    )).scalars().all()

    # Fallback to mapped POs only if no master exists.
    if not pos_rows:
        mapped_po_rows = (await session.execute(
            select(ProgramOutcome)
            .join(co_po_mapping_table, co_po_mapping_table.c.program_outcome_id == ProgramOutcome.id)
            .join(CourseOutcome, CourseOutcome.id == co_po_mapping_table.c.course_outcome_id)
            .where(CourseOutcome.course_id == course_id)
            .distinct()
            .order_by(ProgramOutcome.code)
        )).scalars().all()
        pos_rows = list(mapped_po_rows)

    pos = [{"id": po.code, "statement": po.statement} for po in pos_rows]

    matrix: Dict[str, int] = {}
    for co in cos:
        for po in pos:
            matrix[f"{co['id']}_{po['id']}"] = 0

    if cos and pos:
        rows = (await session.execute(
            select(CourseOutcome.code, ProgramOutcome.code, co_po_mapping_table.c.similarity_score)
            .join(co_po_mapping_table, co_po_mapping_table.c.course_outcome_id == CourseOutcome.id)
            .join(ProgramOutcome, ProgramOutcome.id == co_po_mapping_table.c.program_outcome_id)
            .where(CourseOutcome.course_id == course_id)
        )).all()
        for co_code, po_code, score in rows:
            level = int(round(float(score or 0) * 3))
            matrix[f"{co_code}_{po_code}"] = max(0, min(3, level))

    return validate_matrix(cos=cos, pos=pos, mapping_matrix=matrix)
