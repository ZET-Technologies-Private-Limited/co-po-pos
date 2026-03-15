"""
CO Generation Service
– generates COs from syllabus via LLM
– (optionally) accepts PO/PSO lists and creates CO↔PO/PSO mappings in one shot
– supports weighted CO-PO mapping level (1/2/3) derived from LLM output
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import (
    Course, CourseOutcome,
    ProgramOutcome, ProgramSpecificOutcome,
    co_po_mapping_table, co_pso_mapping_table,
)
from app.core.logging.system_logger import SystemLogger
from app.ai_engine.llm.llm_client import LLMClient

logger = SystemLogger("co_generation_service")

_BLOOM_VALID = {
    "remember", "understand", "apply", "analyze", "analyse", "evaluate", "create",
}
_BLOOM_ALIASES = {
    "analyse": "analyze",
    "application": "apply",
    "comprehension": "understand",
    "knowledge": "remember",
}


def _normalise_bloom(raw: str) -> str:
    val = raw.strip().lower()
    val = _BLOOM_ALIASES.get(val, val)
    return val if val in _BLOOM_VALID else "understand"


def _extract_json(text: str) -> Any:
    """Extract first JSON array from LLM output (handles markdown fences)."""
    # Strip ```json … ``` fences
    fenced = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    # Find first raw array
    bracket = re.search(r"\[.*\]", text, re.DOTALL)
    if bracket:
        return json.loads(bracket.group(0))
    return json.loads(text)


class CoGenerationService:

    def __init__(self, session: AsyncSession):
        self.session = session
        self.llm = LLMClient()

    # ── Manual CO creation ────────────────────────────────────────────────────

    async def create_course_outcome(
        self,
        course_id: str,
        co_code: str,
        co_statement: str,
        bloom_level: str,
        description: Optional[str] = None,
    ) -> CourseOutcome:
        co = CourseOutcome(
            id=str(uuid.uuid4()),
            course_id=course_id,
            code=co_code,
            statement=co_statement,
            bloom_level=_normalise_bloom(bloom_level),
            description=description,
        )
        self.session.add(co)
        await self.session.commit()
        logger.info(f"CO created: {co.id}")
        return co

    # ── AI CO generation ──────────────────────────────────────────────────────

    async def generate_cos_from_syllabus(
        self,
        course_id: str,
        syllabus: str,
        program_outcomes: Optional[List[Dict[str, str]]] = None,
        program_specific_outcomes: Optional[List[Dict[str, str]]] = None,
        num_cos: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate COs from the course syllabus aligned with Bloom's Taxonomy.
        If POs/PSOs are provided, also maps each CO to the relevant POs/PSOs
        (mapping strength 1=weak, 2=medium, 3=strong).

        Returns a dict with:
          - course_outcomes   : list of saved CourseOutcome objects
          - co_po_mappings    : list of {co_code, po_code, level}
          - co_pso_mappings   : list of {co_code, pso_code, level}
        """
        course_result = await self.session.execute(
            select(Course).where(Course.id == course_id)
        )
        course = course_result.scalar_one_or_none()
        if not course:
            raise ValueError(f"Course {course_id} not found")

        # Build PO/PSO context string
        po_context = ""
        if program_outcomes:
            po_lines = "\n".join(f"  {po['code']}: {po['statement']}" for po in program_outcomes)
            po_context = f"\nProgram Outcomes (POs):\n{po_lines}"
        pso_context = ""
        if program_specific_outcomes:
            pso_lines = "\n".join(f"  {pso['code']}: {pso['statement']}" for pso in program_specific_outcomes)
            pso_context = f"\nProgram Specific Outcomes (PSOs):\n{pso_lines}"

        mapping_instruction = ""
        if program_outcomes or program_specific_outcomes:
            mapping_instruction = (
                "\n\nFor each CO also provide:\n"
                "- 'po_mapping': object mapping PO codes to strength (1=weak, 2=medium, 3=strong)\n"
                "  Example: {\"PO1\": 3, \"PO2\": 1}\n"
                "  Only include POs with strength >= 1.\n"
            )
            if program_specific_outcomes:
                mapping_instruction += (
                    "- 'pso_mapping': same format for PSO codes\n"
                )

        prompt = (
            f"You are an OBE curriculum expert. Analyze the course syllabus below and generate exactly "
            f"{num_cos} Course Outcomes (COs) following Bloom's Taxonomy progression "
            f"(from lower to higher order thinking).\n\n"
            f"Course: {course.course_name}\n"
            f"Syllabus:\n{syllabus}"
            f"{po_context}{pso_context}"
            f"{mapping_instruction}\n\n"
            "Return ONLY a valid JSON array with no extra text:\n"
            "[\n"
            "  {\n"
            '    "code": "CO1",\n'
            '    "statement": "Students will be able to ...",\n'
            '    "bloom_level": "remember|understand|apply|analyze|evaluate|create"'
            + (',\n    "po_mapping": {"PO1": 3, "PO2": 2},\n    "pso_mapping": {}' if (program_outcomes or program_specific_outcomes) else "")
            + "\n  }\n]"
        )

        try:
            response = await asyncio.wait_for(
                self.llm.generate_completion(prompt),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            logger.warning("CO generation LLM call timed out; using default CO set")
            response = None

        try:
            cos_data = _extract_json(response)
            if not isinstance(cos_data, list):
                raise ValueError("LLM did not return a list")
        except Exception as exc:
            logger.warning(f"LLM JSON parse failed ({exc}), using defaults")
            cos_data = self._get_default_cos(num_cos)

        # Ensure we have the right number of COs
        cos_data = cos_data[:num_cos]

        # Persist POs/PSOs if provided (upsert by code)
        po_db: Dict[str, ProgramOutcome] = {}
        if program_outcomes:
            po_db = await self._upsert_program_outcomes(program_outcomes, course_id)

        pso_db: Dict[str, ProgramSpecificOutcome] = {}
        if program_specific_outcomes:
            pso_db = await self._upsert_program_specific_outcomes(program_specific_outcomes, course_id)

        # Delete existing COs for this course to avoid duplicates on re-generation
        await self.session.execute(
            delete(CourseOutcome).where(CourseOutcome.course_id == course_id)
        )
        await self.session.flush()

        # Create COs
        created_cos: List[CourseOutcome] = []
        co_po_mappings: List[Dict] = []
        co_pso_mappings: List[Dict] = []

        for i, co_data in enumerate(cos_data, 1):
            co_code = co_data.get("code", f"CO{i}")
            co_obj = CourseOutcome(
                id=str(uuid.uuid4()),
                course_id=course_id,
                code=co_code,
                statement=co_data.get("statement", ""),
                bloom_level=_normalise_bloom(co_data.get("bloom_level", "understand")),
                description=co_data.get("description"),
            )
            self.session.add(co_obj)
            await self.session.flush()  # get ID

            # CO-PO mappings
            for po_code, level in co_data.get("po_mapping", {}).items():
                po_obj = po_db.get(po_code)
                if po_obj:
                    await self.session.execute(
                        co_po_mapping_table.insert().values(
                            course_outcome_id=co_obj.id,
                            program_outcome_id=po_obj.id,
                            similarity_score=float(level) / 3.0,
                        )
                    )
                    co_po_mappings.append({
                        "co_code": co_code,
                        "po_code": po_code,
                        "mapping_level": level,
                    })

            # CO-PSO mappings
            for pso_code, level in co_data.get("pso_mapping", {}).items():
                pso_obj = pso_db.get(pso_code)
                if pso_obj:
                    await self.session.execute(
                        co_pso_mapping_table.insert().values(
                            course_outcome_id=co_obj.id,
                            program_specific_outcome_id=pso_obj.id,
                            similarity_score=float(level) / 3.0,
                        )
                    )
                    co_pso_mappings.append({
                        "co_code": co_code,
                        "pso_code": pso_code,
                        "mapping_level": level,
                    })

            created_cos.append(co_obj)

        await self.session.commit()
        logger.info(
            f"Generated {len(created_cos)} COs, "
            f"{len(co_po_mappings)} CO-PO mappings, "
            f"{len(co_pso_mappings)} CO-PSO mappings for course {course_id}"
        )
        return {
            "course_outcomes": created_cos,
            "co_po_mappings": co_po_mappings,
            "co_pso_mappings": co_pso_mappings,
        }

    # ── Query helpers ─────────────────────────────────────────────────────────

    async def get_course_outcomes(self, course_id: str) -> List[CourseOutcome]:
        result = await self.session.execute(
            select(CourseOutcome).where(CourseOutcome.course_id == course_id)
        )
        return list(result.scalars().all())

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _upsert_program_outcomes(
        self, pos: List[Dict[str, str]], program_id: str
    ) -> Dict[str, ProgramOutcome]:
        db_map: Dict[str, ProgramOutcome] = {}
        for po_input in pos:
            code = po_input["code"]
            result = await self.session.execute(
                select(ProgramOutcome).where(
                    ProgramOutcome.code == code,
                    ProgramOutcome.program == program_id,
                )
            )
            po_obj = result.scalar_one_or_none()
            if not po_obj:
                po_obj = ProgramOutcome(
                    id=str(uuid.uuid4()),
                    code=code,
                    statement=po_input.get("statement", ""),
                    program=program_id,
                )
                self.session.add(po_obj)
                await self.session.flush()
            else:
                if po_input.get("statement"):
                    po_obj.statement = po_input.get("statement", po_obj.statement)
            db_map[code] = po_obj
        return db_map

    async def _upsert_program_specific_outcomes(
        self, psos: List[Dict[str, str]], program_id: str
    ) -> Dict[str, ProgramSpecificOutcome]:
        db_map: Dict[str, ProgramSpecificOutcome] = {}
        for pso_input in psos:
            code = pso_input["code"]
            result = await self.session.execute(
                select(ProgramSpecificOutcome).where(
                    ProgramSpecificOutcome.code == code,
                    ProgramSpecificOutcome.program == program_id,
                )
            )
            pso_obj = result.scalar_one_or_none()
            if not pso_obj:
                pso_obj = ProgramSpecificOutcome(
                    id=str(uuid.uuid4()),
                    code=code,
                    statement=pso_input.get("statement", ""),
                    program=program_id,
                )
                self.session.add(pso_obj)
                await self.session.flush()
            else:
                if pso_input.get("statement"):
                    pso_obj.statement = pso_input.get("statement", pso_obj.statement)
            db_map[code] = pso_obj
        return db_map

    async def regenerate_single_co(
        self,
        course_id: str,
        co_id: str,
        context: Optional[str] = None,
    ) -> "CourseOutcome":
        """Re-generate a single CO via LLM, leaving all other COs untouched."""
        co_result = await self.session.execute(
            select(CourseOutcome).where(
                CourseOutcome.id == co_id,
                CourseOutcome.course_id == course_id,
            )
        )
        co = co_result.scalar_one_or_none()
        if not co:
            raise ValueError(f"CO {co_id} not found for course {course_id}")

        course_result = await self.session.execute(select(Course).where(Course.id == course_id))
        course = course_result.scalar_one_or_none()
        syllabus = context or (course.syllabus if course else "") or ""

        other_result = await self.session.execute(
            select(CourseOutcome).where(
                CourseOutcome.course_id == course_id,
                CourseOutcome.id != co_id,
            )
        )
        other_cos = other_result.scalars().all()
        other_ctx = "\n".join(
            f"  {c.code}: {c.statement} (BT: {str(c.bloom_level.value if hasattr(c.bloom_level, 'value') else c.bloom_level)})"
            for c in other_cos
        )

        current_bloom = str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level)
        prompt = (
            f"You are an OBE curriculum expert. Regenerate ONLY the following Course Outcome.\n"
            f"Keep the same Bloom's Taxonomy level unless there is a strong reason to change it.\n"
            f"Make it specific, measurable, and distinct from the other existing COs.\n\n"
            f"Course: {course.course_name if course else course_id}\n"
            f"Syllabus context:\n{syllabus[:2000]}\n\n"
            f"CO to regenerate: {co.code} (current BT level: {current_bloom})\n"
            f"Current statement: {co.statement}\n\n"
            f"Other existing COs (make the new one distinct from these):\n{other_ctx}\n\n"
            "Return ONLY a JSON object with no extra text:\n"
            '{"statement": "Students will be able to ...", "bloom_level": "remember|understand|apply|analyze|evaluate|create"}'
        )

        response = await self.llm.generate_completion(prompt)
        try:
            data = _extract_json(response)
            if isinstance(data, list):
                data = data[0] if data else {}
        except Exception as exc:
            logger.warning(f"LLM parse failed for single CO regen ({co_id}): {exc}")
            data = {"statement": co.statement, "bloom_level": current_bloom}

        co.statement = data.get("statement") or co.statement
        co.bloom_level = _normalise_bloom(data.get("bloom_level", current_bloom))
        await self.session.commit()
        logger.info(f"Regenerated single CO {co_id} for course {course_id}")
        return co

    def _get_default_cos(self, num: int = 5) -> List[Dict]:
        defaults = [
            {"code": "CO1", "statement": "Recall and describe fundamental concepts and principles of the subject.", "bloom_level": "remember"},
            {"code": "CO2", "statement": "Explain and interpret key theories and their applications.", "bloom_level": "understand"},
            {"code": "CO3", "statement": "Apply learned techniques to solve real-world problems.", "bloom_level": "apply"},
            {"code": "CO4", "statement": "Analyze complex scenarios and identify root causes.", "bloom_level": "analyze"},
            {"code": "CO5", "statement": "Evaluate different approaches and select the most appropriate solution.", "bloom_level": "evaluate"},
            {"code": "CO6", "statement": "Design and develop innovative solutions to domain-specific problems.", "bloom_level": "create"},
        ]
        return defaults[:num]


class COGenerationService(CoGenerationService):
    """Backward-compatible alias for older imports."""
    pass
