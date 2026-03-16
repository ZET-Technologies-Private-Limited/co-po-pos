"""
CO Generation Service
Generates NBA-compliant Course Outcomes from syllabus via LLM with:
- Domain detection (CS/ECE/Mechanical/Civil/Electrical/Math/General)
- Structured prompt templates per domain
- Bloom's Taxonomy progression enforcement (L1→L6)
- CO quality validation (measurability, action verb, specificity)
- Overlap detection between generated COs
- Retry logic with refined prompts on parse/quality failure
- Subject-specific fallback COs when LLM unavailable
- CO↔PO/PSO mapping with strength levels (1/2/3)
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import (
    Course, CourseOutcome, COAttainment,
    ProgramOutcome, ProgramSpecificOutcome,
    co_po_mapping_table, co_pso_mapping_table, question_co_mapping_table,
)
from app.core.config.constants import BloomTaxonomyLevel
from app.core.logging.system_logger import SystemLogger
from app.ai_engine.llm.llm_client import LLMClient
from app.modules.co_generation.templates.co_prompt_templates import (
    DOMAIN_KEYWORDS, BLOOM_VERBS, DOMAIN_CO_EXAMPLES,
    SYSTEM_PROMPT,
    get_bloom_progression,
    build_generation_prompt,
    build_regeneration_prompt,
    build_co_po_mapping_prompt,
)
from app.core.prompts.nba_obe_system_prompt import get_system_prompt as _nba_prompt
from app.core.infrastructure.redis_client import get_json, set_json

# Merge domain template system prompt with full NBA system prompt
_CO_SYSTEM_PROMPT = _nba_prompt("co_generation") + "\n\n" + SYSTEM_PROMPT

logger = SystemLogger("co_generation_service")

_CO_HISTORY_TTL = 86400 * 30  # 30 days
_CO_SESSION_TTL = 86400 * 7   # 7 days
_CO_ITEM_HISTORY_TTL = 86400 * 90  # 90 days


def _co_history_key(course_id: str) -> str:
    return f"co_generation:history:{course_id}"


def _co_session_key(course_id: str) -> str:
    return f"co_generation:session:{course_id}"

def _co_item_history_key(course_id: str, co_code: str) -> str:
    safe_code = (co_code or "").strip().upper() or "CO?"
    return f"co_generation:item_history:{course_id}:{safe_code}"


async def _append_co_item_version(course_id: str, co_code: str, snapshot: Dict[str, Any]) -> None:
    """
    Append a per-CO version snapshot to Redis.

    Snapshot schema (best-effort):
      {timestamp, co_code, statement, bloom_level, source, reason}
    """
    try:
        key = _co_item_history_key(course_id, co_code)
        existing = await get_json(key) or {"versions": []}
        versions: List[Dict[str, Any]] = existing.get("versions", [])
        versions.insert(0, snapshot)
        versions = versions[:20]  # keep last 20 versions per CO
        await set_json(key, {"versions": versions}, ttl_seconds=_CO_ITEM_HISTORY_TTL)
    except Exception as exc:
        logger.warning(f"Failed to append CO item history for {course_id}/{co_code}: {exc}")

async def _save_co_version(course_id: str, cos: List[Dict], domain: str, syllabus_snippet: str) -> None:
    """Persist a CO version snapshot to Redis before overwriting."""
    try:
        key = _co_history_key(course_id)
        existing = await get_json(key) or {"versions": []}
        versions: List[Dict] = existing.get("versions", [])
        snapshot = {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "domain": domain,
            "syllabus_snippet": syllabus_snippet[:300],
            "cos": [
                {"code": c.get("code", ""), "statement": c.get("statement", ""), "bloom_level": c.get("bloom_level", "")}
                for c in cos
            ],
        }
        versions.insert(0, snapshot)
        versions = versions[:10]  # keep last 10 versions
        await set_json(key, {"versions": versions}, ttl_seconds=_CO_HISTORY_TTL)
    except Exception as exc:
        logger.warning(f"Failed to save CO version history for {course_id}: {exc}")


async def _save_co_session(course_id: str, syllabus: str, domain: str, num_cos: int) -> None:
    """Persist generation session context to Redis for session memory."""
    try:
        payload = {
            "course_id": course_id,
            "syllabus_snippet": syllabus[:500],
            "domain": domain,
            "num_cos": num_cos,
            "last_generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
        await set_json(_co_session_key(course_id), payload, ttl_seconds=_CO_SESSION_TTL)
    except Exception as exc:
        logger.warning(f"Failed to save CO session for {course_id}: {exc}")

_BLOOM_ALIASES = {
    "analyse": "analyze",
    "application": "apply",
    "comprehension": "understand",
    "knowledge": "remember",
}
_BLOOM_VALID = set(BLOOM_VERBS.keys())

# Vague verbs that indicate a low-quality CO statement
_VAGUE_VERBS = {"understand", "know", "learn", "appreciate", "be aware", "grasp", "study", "cover"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _normalise_bloom(raw: str) -> BloomTaxonomyLevel:
    val = (raw or "understand").strip().lower()
    val = _BLOOM_ALIASES.get(val, val)
    if val not in _BLOOM_VALID:
        val = "understand"
    return BloomTaxonomyLevel[val.upper()]


def _extract_json(text: str) -> Any:
    """Extract first JSON array or object from LLM output (handles markdown fences)."""
    if not text:
        raise ValueError("Empty LLM response")
    fenced = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    arr = re.search(r"\[.*\]", text, re.DOTALL)
    if arr:
        return json.loads(arr.group(0))
    obj = re.search(r"\{.*\}", text, re.DOTALL)
    if obj:
        return json.loads(obj.group(0))
    return json.loads(text)


def _detect_domain(course_name: str, syllabus: str) -> str:
    """Detect subject domain from course name and syllabus keywords."""
    text = (course_name + " " + syllabus).lower()
    scores: Dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] >= 2 else "general"


def _validate_co_quality(co: Dict, bloom_level: str) -> Tuple[bool, str]:
    """
    Validate a single CO dict for NBA quality standards.
    Returns (is_valid, reason_if_invalid).

    This is intentionally strict because it is the single source of truth
    for CO quality checks across generation, regeneration, and manual edits.
    """
    stmt = (co.get("statement") or "").strip()
    if not stmt:
        return False, "Empty statement"

    stmt_lower = stmt.lower()
    if not stmt_lower.startswith("students will be able to"):
        return False, f"Statement must start with 'Students will be able to', got: {stmt[:60]}"

    # Enforce single-sentence format with a terminating period.
    # Treat "?", "!" or ":" as potential secondary sentence delimiters.
    sentence_like = [ch for ch in stmt if ch in ".!?"]
    if len(sentence_like) > 1:
        return False, "Statement must be a single sentence"
    if not stmt.rstrip().endswith("."):
        return False, "Statement must end with a period"

    # Max word count to keep COs concise and measurable.
    words = stmt.split()
    if len(words) > 30:
        return False, "Statement too long — keep it within 30 words for measurability"

    # Check for vague verbs immediately after the fixed prefix.
    if len(words) > 5:
        verb_candidate = words[5].lower()
        if verb_candidate in _VAGUE_VERBS:
            return False, f"Vague verb '{verb_candidate}' — use a specific Bloom's action verb"

    # Check that at least one valid Bloom's verb for the level appears
    valid_verbs = BLOOM_VERBS.get(bloom_level, [])
    if not any(v in stmt_lower for v in valid_verbs):
        return False, f"No {bloom_level.upper()} level verb found in statement"

    # Ensure minimum specificity
    if len(stmt) < 30:
        return False, "Statement too short — must be specific to course content"

    return True, ""


def _detect_overlap(cos: List[Dict]) -> List[Tuple[int, int, str]]:
    """
    Detect overlapping COs by checking shared key noun phrases.
    Returns list of (i, j, reason) for overlapping pairs.
    """
    overlaps = []
    statements = [
        set(re.findall(r"\b[a-z]{4,}\b", (c.get("statement") or "").lower()))
        for c in cos
    ]
    for i in range(len(statements)):
        for j in range(i + 1, len(statements)):
            shared = statements[i] & statements[j] - {
                "students", "able", "will", "with", "that", "this",
                "their", "using", "from", "into", "have", "been",
            }
            if len(shared) >= 5:
                overlaps.append((i, j, f"Shared terms: {', '.join(list(shared)[:5])}"))
    return overlaps


# ── Service ───────────────────────────────────────────────────────────────────

class CoGenerationService:

    def __init__(self, session: AsyncSession):
        self.session = session
        try:
            self.llm = LLMClient()
        except Exception as exc:
            logger.warning(f"LLM client init failed, will use domain fallbacks: {exc}")
            self.llm = None

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
        logger.info(f"CO created manually: {co.id}")
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
        Generate NBA-compliant COs from course syllabus.

        Pipeline:
          1. Detect domain from course name + syllabus
          2. Build structured domain-aware prompt with Bloom's progression
          3. Call LLM with system prompt + user prompt
          4. Parse + validate JSON response
          5. Retry once with refined prompt if quality fails
          6. Fall back to domain-specific defaults if LLM unavailable/fails
          7. Detect and log CO overlaps
          8. Persist COs + CO-PO/PSO mappings

        Returns:
          course_outcomes   : list of saved CourseOutcome objects
          co_po_mappings    : list of {co_code, po_code, mapping_level}
          co_pso_mappings   : list of {co_code, pso_code, mapping_level}
          domain            : detected domain string
          quality_warnings  : list of any quality issues found
        """
        course = await self._get_course(course_id)
        syllabus = (syllabus or "").strip() or (course.syllabus or "").strip()
        if not syllabus:
            raise ValueError("Syllabus is required for CO generation")

        # Cache course metadata for use in prompt building
        self._course_code = course.course_code or ""
        self._course_department = course.department or ""
        self._course_semester = course.semester
        self._course_credits = course.credits
        self._course_enrolled = course.enrolled_students

        domain = _detect_domain(course.course_name, syllabus)
        units_for_prompt = self._parse_syllabus_units(syllabus)
        unit_guidance = self._analyze_units_for_prompt(units_for_prompt)
        # Bloom sequence is now derived from unit analysis (dynamic), not a fixed table
        bloom_sequence = get_bloom_progression(num_cos, unit_guidance=unit_guidance)
        has_mappings = bool(program_outcomes or program_specific_outcomes)

        po_context = self._build_po_context(program_outcomes)
        pso_context = self._build_pso_context(program_specific_outcomes)

        # ── Step 1: Try LLM generation ────────────────────────────────────────
        cos_data = await self._generate_with_llm(
            course_name=course.course_name,
            syllabus=syllabus,
            num_cos=num_cos,
            domain=domain,
            bloom_sequence=bloom_sequence,
            po_context=po_context,
            pso_context=pso_context,
            has_mappings=has_mappings,
            unit_guidance=unit_guidance,
        )

        # ── Step 2: Validate quality; perform at most two corrective retries
        #            when the model output does not satisfy NBA constraints. ───
        quality_warnings: List[str] = []
        attempts = 0
        while cos_data and attempts < 2:
            attempts += 1

            # Enforce exact CO count if the model returned too many/few.
            if len(cos_data) != num_cos:
                quality_warnings.append(
                    f"LLM returned {len(cos_data)} COs, expected {num_cos} — issuing corrective retry"
                )
                logger.warning(
                    f"CO count mismatch for {course_id}: got {len(cos_data)}, expected {num_cos}"
                )
                cos_data = await self._retry_with_fixes(
                    cos_data=cos_data,
                    issues=[f"Generated {len(cos_data)} COs, must generate exactly {num_cos}."],
                    course_name=course.course_name,
                    syllabus=syllabus,
                    num_cos=num_cos,
                    domain=domain,
                    bloom_sequence=bloom_sequence,
                    po_context=po_context,
                    pso_context=pso_context,
                    has_mappings=has_mappings,
                    unit_guidance=unit_guidance,
                )
                continue

            issues = self._check_quality(cos_data, bloom_sequence)
            coverage_issues = self._coverage_issues(units_for_prompt, cos_data)
            if coverage_issues:
                issues.extend(coverage_issues)
            if not issues:
                break

            quality_warnings.extend(issues)
            logger.warning(f"Quality issues on attempt {attempts} for {course_id}: {issues}")
            retry_data = await self._retry_with_fixes(
                cos_data=cos_data,
                issues=issues,
                course_name=course.course_name,
                syllabus=syllabus,
                num_cos=num_cos,
                domain=domain,
                bloom_sequence=bloom_sequence,
                po_context=po_context,
                pso_context=pso_context,
                has_mappings=has_mappings,
                unit_guidance=unit_guidance,
            )
            if retry_data:
                cos_data = retry_data
                quality_warnings.append(f"Retry {attempts} succeeded — quality improved")
            else:
                # If retry fails, exit loop and fall back (or accept with warnings).
                break

        # ── Step 3: Fall back to domain defaults if LLM failed ────────────────
        if not cos_data:
            logger.warning(f"LLM unavailable/failed for {course_id}, using {domain} domain defaults")
            cos_data = self._get_domain_defaults(domain, num_cos)
            quality_warnings.append(f"Used {domain} domain default COs (LLM unavailable)")

        cos_data = cos_data[:num_cos]

        # ── Step 4: Overlap detection ─────────────────────────────────────────
        overlaps = _detect_overlap(cos_data)
        for i, j, reason in overlaps:
            msg = f"CO{i+1} and CO{j+1} may overlap: {reason}"
            quality_warnings.append(msg)
            logger.warning(msg)

        # ── Step 5: Persist POs/PSOs under the dept program key ─────────────
        dept_key = f"DEPT:{(self._course_department or 'GENERAL').strip().upper()}"
        po_db: Dict[str, ProgramOutcome] = {}
        if program_outcomes:
            po_db = await self._upsert_program_outcomes(program_outcomes, dept_key)

        pso_db: Dict[str, ProgramSpecificOutcome] = {}
        if program_specific_outcomes:
            pso_db = await self._upsert_program_specific_outcomes(program_specific_outcomes, dept_key)

        # ── Step 5b: Save version history before deleting ────────────────────
        existing_cos_result = await self.session.execute(
            select(CourseOutcome).where(CourseOutcome.course_id == course_id)
        )
        existing_cos_objs = list(existing_cos_result.scalars().all())
        if existing_cos_objs:
            prev_snapshot = [
                {
                    "code": co.code,
                    "statement": co.statement,
                    "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level),
                }
                for co in existing_cos_objs
            ]
            await _save_co_version(course_id, prev_snapshot, domain, syllabus[:300])

        # ── Step 5c: Save session memory ──────────────────────────────────────
        await _save_co_session(course_id, syllabus, domain, num_cos)

        # ── Step 6: Delete existing COs (re-generation) ───────────────────────
        await self._delete_existing_cos(course_id)

        # ── Step 7: Persist new COs + mappings ───────────────────────────────
        created_cos, co_po_mappings, co_pso_mappings = await self._persist_cos(
            cos_data=cos_data,
            course_id=course_id,
            bloom_sequence=bloom_sequence,
            po_db=po_db,
            pso_db=pso_db,
        )

        await self.session.commit()
        logger.info(
            f"Generated {len(created_cos)} COs [{domain}], "
            f"{len(co_po_mappings)} PO mappings, {len(co_pso_mappings)} PSO mappings "
            f"for course {course_id}"
        )

        # ── Step 8: Unit coverage validation ─────────────────────────────────
        coverage_result = self._validate_unit_coverage(units_for_prompt, created_cos)
        for uncovered in coverage_result["uncovered_units"]:
            quality_warnings.append(f"Unit '{uncovered}' not covered by any CO — consider adding a CO for this topic")

        # ── Step 9: Async CO-PO mapping with justification ────────────────────
        mapping_justifications: Dict[str, Dict[str, str]] = {}
        if program_outcomes and self.llm:
            mapping_justifications = await self._map_cos_to_pos_with_justification(
                created_cos=created_cos,
                program_outcomes=program_outcomes,
                program_specific_outcomes=program_specific_outcomes or [],
                po_db=po_db,
                pso_db=pso_db,
                course_id=course_id,
            )
            # Reload mappings after async mapping
            co_po_mappings_new, co_pso_mappings_new = await self._reload_mappings(created_cos)
            if co_po_mappings_new:
                co_po_mappings = co_po_mappings_new
            if co_pso_mappings_new:
                co_pso_mappings = co_pso_mappings_new

        return {
            "course_outcomes": created_cos,
            "co_po_mappings": co_po_mappings,
            "co_pso_mappings": co_pso_mappings,
            "domain": domain,
            "quality_warnings": quality_warnings,
            "units": units_for_prompt,
            "coverage": coverage_result,
            "mapping_justifications": mapping_justifications,
        }

    # ── Single CO regeneration ────────────────────────────────────────────────

    async def regenerate_single_co(
        self,
        course_id: str,
        co_id: str,
        context: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> CourseOutcome:
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

        course = await self._get_course(course_id)
        syllabus = (context or (course.syllabus if course else "") or "").strip()
        domain = _detect_domain(course.course_name if course else "", syllabus)

        other_result = await self.session.execute(
            select(CourseOutcome).where(
                CourseOutcome.course_id == course_id,
                CourseOutcome.id != co_id,
            )
        )
        other_cos = [
            {
                "code": c.code,
                "statement": c.statement,
                "bloom_level": str(c.bloom_level.value if hasattr(c.bloom_level, "value") else c.bloom_level),
            }
            for c in other_result.scalars().all()
        ]

        current_bloom = str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level)

        prompt = build_regeneration_prompt(
            course_name=course.course_name if course else course_id,
            syllabus_snippet=syllabus,
            co_code=co.code,
            current_statement=co.statement,
            current_bloom=current_bloom,
            other_cos=other_cos,
            domain=domain,
            reason=reason,
        )

        response = None
        if self.llm:
            try:
                response = await asyncio.wait_for(
                    self.llm.generate_completion(prompt, system_prompt=_CO_SYSTEM_PROMPT),
                    timeout=30.0,
                )
            except (asyncio.TimeoutError, Exception) as exc:
                logger.warning(f"LLM failed for single CO regen {co_id}: {exc}")

        data: Dict = {}
        if response:
            try:
                parsed = _extract_json(response)
                data = parsed[0] if isinstance(parsed, list) and parsed else parsed
            except Exception as exc:
                logger.warning(f"JSON parse failed for CO regen {co_id}: {exc}")

        new_statement = data.get("statement", "").strip()
        new_bloom = data.get("bloom_level", current_bloom)

        # Validate the regenerated CO
        if new_statement:
            valid, reason_str = _validate_co_quality(
                {"statement": new_statement}, new_bloom
            )
            if not valid:
                logger.warning(f"Regenerated CO {co_id} failed quality check: {reason_str}")
                new_statement = co.statement  # keep original if quality fails

        # Save per-CO version before overwriting
        prev_bloom = str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level)
        await _append_co_item_version(
            course_id=course_id,
            co_code=co.code,
            snapshot={
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                "co_code": co.code,
                "statement": co.statement,
                "bloom_level": prev_bloom,
                "source": "ai_regenerate_single",
                "reason": reason or "",
            },
        )

        co.statement = new_statement or co.statement
        co.bloom_level = _normalise_bloom(new_bloom)
        await self.session.commit()
        logger.info(f"Regenerated CO {co_id} for course {course_id}")
        return co

    # ── Query helpers ─────────────────────────────────────────────────────────

    async def get_course_outcomes(self, course_id: str) -> List[CourseOutcome]:
        result = await self.session.execute(
            select(CourseOutcome).where(CourseOutcome.course_id == course_id)
        )
        return list(result.scalars().all())

    # ── LLM call + parse ──────────────────────────────────────────────────────

    async def _generate_with_llm(
        self,
        course_name: str,
        syllabus: str,
        num_cos: int,
        domain: str,
        bloom_sequence: List[str],
        po_context: str,
        pso_context: str,
        has_mappings: bool,
        unit_guidance: Optional[List[Dict]] = None,
    ) -> Optional[List[Dict]]:
        if not self.llm:
            return None

        prompt = build_generation_prompt(
            course_name=course_name,
            syllabus=syllabus,
            num_cos=num_cos,
            domain=domain,
            bloom_sequence=bloom_sequence,
            po_context=po_context,
            pso_context=pso_context,
            has_mappings=has_mappings,
            unit_guidance=unit_guidance,
            advanced_mode=True,
            course_code=getattr(self, '_course_code', ''),
            department=getattr(self, '_course_department', ''),
            semester=getattr(self, '_course_semester', None),
            credits=getattr(self, '_course_credits', None),
            enrolled_students=getattr(self, '_course_enrolled', None),
        )

        try:
            response = await asyncio.wait_for(
                self.llm.generate_completion(prompt, system_prompt=_CO_SYSTEM_PROMPT),
                timeout=90.0,
            )
        except asyncio.TimeoutError:
            logger.warning(f"LLM timed out for CO generation ({course_name})")
            return None
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                logger.warning(f"LLM rate-limited for CO generation ({course_name}): {err_str[:120]}")
            else:
                logger.error(f"LLM call failed: {exc}")
            return None

        if not response:
            return None

        try:
            parsed = _extract_json(response)
            if isinstance(parsed, list) and parsed:
                # If the model produced the wrong number of COs, keep the
                # parsed list but let the caller decide whether to retry
                # with an explicit count correction instruction.
                return parsed
            logger.warning(f"LLM returned non-list JSON for {course_name}")
            return None
        except Exception as exc:
            logger.warning(f"JSON parse failed for {course_name}: {exc} | Raw: {response[:200]}")
            return None

    async def _retry_with_fixes(
        self,
        cos_data: List[Dict],
        issues: List[str],
        course_name: str,
        syllabus: str,
        num_cos: int,
        domain: str,
        bloom_sequence: List[str],
        po_context: str,
        pso_context: str,
        has_mappings: bool,
        unit_guidance: Optional[List[Dict]] = None,
    ) -> Optional[List[Dict]]:
        """Retry LLM with explicit issue list appended to prompt."""
        if not self.llm:
            return None

        issue_block = "\n".join(f"  - {issue}" for issue in issues[:5])
        base_prompt = build_generation_prompt(
            course_name=course_name,
            syllabus=syllabus,
            num_cos=num_cos,
            domain=domain,
            bloom_sequence=bloom_sequence,
            po_context=po_context,
            pso_context=pso_context,
            has_mappings=has_mappings,
            unit_guidance=unit_guidance,
            advanced_mode=True,
            course_code=getattr(self, '_course_code', ''),
            department=getattr(self, '_course_department', ''),
            semester=getattr(self, '_course_semester', None),
            credits=getattr(self, '_course_credits', None),
            enrolled_students=getattr(self, '_course_enrolled', None),
        )
        retry_prompt = (
            f"{base_prompt}\n\n"
            f"PREVIOUS ATTEMPT HAD THESE ISSUES — FIX ALL OF THEM:\n{issue_block}\n"
            f"Generate corrected COs now."
        )

        try:
            response = await asyncio.wait_for(
                self.llm.generate_completion(retry_prompt, system_prompt=_CO_SYSTEM_PROMPT),
                timeout=90.0,
            )
            if response:
                parsed = _extract_json(response)
                if isinstance(parsed, list) and parsed:
                    return parsed
        except Exception as exc:
            logger.warning(f"Retry LLM call failed: {exc}")
        return None

    # ── Quality checks ────────────────────────────────────────────────────────

    def _check_quality(self, cos_data: List[Dict], bloom_sequence: List[str]) -> List[str]:
        """
        Run quality checks on all COs.

        Validates per-CO statement quality and enforces minimum BT distribution
        across the CO set. Does NOT enforce exact positional bloom level matching
        because the LLM may legitimately assign a higher level than the unit
        analysis suggested (e.g. a unit with 'implement' topics may produce an
        L4 CO when the LLM detects comparative analysis in the content).
        """
        issues: List[str] = []
        level_histogram: Dict[str, int] = {}

        for i, co in enumerate(cos_data):
            expected_bloom = bloom_sequence[i] if i < len(bloom_sequence) else "apply"
            actual_bloom = (co.get("bloom_level") or "").strip().lower()
            actual_bloom = _BLOOM_ALIASES.get(actual_bloom, actual_bloom)

            valid, reason = _validate_co_quality(co, actual_bloom or expected_bloom)
            if not valid:
                issues.append(f"CO{i+1}: {reason}")

            # Only flag a mismatch when the LLM went LOWER than the unit-derived
            # level (going higher is acceptable — it means richer content coverage).
            if actual_bloom and actual_bloom in _BLOOM_VALID:
                bloom_order = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
                actual_idx = bloom_order.index(actual_bloom) if actual_bloom in bloom_order else 0
                expected_idx = bloom_order.index(expected_bloom) if expected_bloom in bloom_order else 0
                if actual_idx < expected_idx - 1:  # more than one level below expected
                    issues.append(
                        f"CO{i+1}: Bloom's level '{actual_bloom}' is significantly below "
                        f"the unit-derived target '{expected_bloom}' — consider a higher-order verb"
                    )

            lvl_key = actual_bloom or expected_bloom
            if lvl_key:
                level_histogram[lvl_key] = level_histogram.get(lvl_key, 0) + 1

        # Distribution check: at least 3 distinct BT levels for 4+ COs.
        total_cos = len(cos_data)
        distinct_levels = {lvl for lvl, cnt in level_histogram.items() if cnt > 0}
        if total_cos >= 4 and len(distinct_levels) < 3:
            level_list = ", ".join(sorted(distinct_levels)) or "none"
            issues.append(
                f"All COs are at {level_list} level — consider one Analyse (L4) and one Create (L6) CO "
                f"for better cognitive spread across the {total_cos} COs."
            )

        # Semantic duplicate check (80% similarity)
        statements = [_norm_text(str(c.get("statement") or "")) for c in cos_data]
        for i in range(len(statements)):
            for j in range(i + 1, len(statements)):
                if not statements[i] or not statements[j]:
                    continue
                sim = SequenceMatcher(None, statements[i], statements[j]).ratio()
                if sim >= 0.80:
                    issues.append(
                        f"CO{i+1} and CO{j+1} are too similar (similarity {sim:.0%}) — rewrite to avoid duplication"
                    )

        return issues

    # ── Domain-specific fallback COs ──────────────────────────────────────────

    def _get_domain_defaults(self, domain: str, num: int) -> List[Dict]:
        examples = DOMAIN_CO_EXAMPLES.get(domain, DOMAIN_CO_EXAMPLES["general"])
        bloom_seq = get_bloom_progression(num)
        result = []
        for i, level in enumerate(bloom_seq):
            # Find example matching this bloom level
            match = next((e for e in examples if e["bloom_level"] == level), examples[i % len(examples)])
            result.append({
                "code": f"CO{i+1}",
                "statement": match["statement"],
                "bloom_level": level,
                "description": f"Assessed via exams and assignments targeting {level} level skills.",
            })
        return result

    # ── Persistence helpers ───────────────────────────────────────────────────

    async def _get_course(self, course_id: str) -> Course:
        result = await self.session.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            raise ValueError(f"Course {course_id} not found")
        return course

    async def _delete_existing_cos(self, course_id: str) -> None:
        existing_ids_result = await self.session.execute(
            select(CourseOutcome.id).where(CourseOutcome.course_id == course_id)
        )
        existing_co_ids = list(existing_ids_result.scalars().all())
        if existing_co_ids:
            await self.session.execute(
                delete(co_po_mapping_table).where(
                    co_po_mapping_table.c.course_outcome_id.in_(existing_co_ids)
                )
            )
            await self.session.execute(
                delete(co_pso_mapping_table).where(
                    co_pso_mapping_table.c.course_outcome_id.in_(existing_co_ids)
                )
            )
            await self.session.execute(
                delete(question_co_mapping_table).where(
                    question_co_mapping_table.c.course_outcome_id.in_(existing_co_ids)
                )
            )
            await self.session.execute(
                delete(COAttainment).where(COAttainment.course_outcome_id.in_(existing_co_ids))
            )
        await self.session.execute(
            delete(CourseOutcome).where(CourseOutcome.course_id == course_id)
        )
        await self.session.flush()

    async def _persist_cos(
        self,
        cos_data: List[Dict],
        course_id: str,
        bloom_sequence: List[str],
        po_db: Dict[str, ProgramOutcome],
        pso_db: Dict[str, ProgramSpecificOutcome],
    ) -> Tuple[List[CourseOutcome], List[Dict], List[Dict]]:
        created_cos: List[CourseOutcome] = []
        co_po_mappings: List[Dict] = []
        co_pso_mappings: List[Dict] = []

        for i, co_data in enumerate(cos_data, 1):
            co_code = co_data.get("code") or f"CO{i}"
            # Respect the LLM's bloom level assignment (unit-driven, dynamic).
            # Only fall back to the sequence position when the LLM returned nothing.
            expected_bloom = bloom_sequence[i - 1] if (i - 1) < len(bloom_sequence) else "apply"
            raw_bloom = (co_data.get("bloom_level") or "").strip().lower()
            raw_bloom = _BLOOM_ALIASES.get(raw_bloom, raw_bloom)
            # Accept LLM level if valid; fall back to expected only when absent/invalid
            final_bloom = raw_bloom if raw_bloom in _BLOOM_VALID else expected_bloom

            co_obj = CourseOutcome(
                id=str(uuid.uuid4()),
                course_id=course_id,
                code=co_code,
                statement=(
                    co_data.get("statement")
                    or f"Students will be able to achieve {co_code} outcomes."
                ),
                bloom_level=_normalise_bloom(final_bloom),
                description=co_data.get("description"),
            )
            self.session.add(co_obj)
            await self.session.flush()

            # CO-PO mappings
            for po_code, level in co_data.get("po_mapping", {}).items():
                po_obj = po_db.get(po_code)
                if po_obj:
                    level_int = max(1, min(3, int(level))) if str(level).isdigit() else 1
                    await self.session.execute(
                        co_po_mapping_table.insert().values(
                            course_outcome_id=co_obj.id,
                            program_outcome_id=po_obj.id,
                            similarity_score=float(level_int) / 3.0,
                        )
                    )
                    co_po_mappings.append({"co_code": co_code, "po_code": po_code, "mapping_level": level_int})

            # CO-PSO mappings
            for pso_code, level in co_data.get("pso_mapping", {}).items():
                pso_obj = pso_db.get(pso_code)
                if pso_obj:
                    level_int = max(1, min(3, int(level))) if str(level).isdigit() else 1
                    await self.session.execute(
                        co_pso_mapping_table.insert().values(
                            course_outcome_id=co_obj.id,
                            program_specific_outcome_id=pso_obj.id,
                            similarity_score=float(level_int) / 3.0,
                        )
                    )
                    co_pso_mappings.append({"co_code": co_code, "pso_code": pso_code, "mapping_level": level_int})

            created_cos.append(co_obj)

        return created_cos, co_po_mappings, co_pso_mappings

    def _parse_syllabus_units(self, syllabus: str) -> List[Dict]:
        """Extract unit names and topics from syllabus text."""
        import re as _re
        units: List[Dict] = []
        current: Optional[Dict] = None

        # Normalize line endings and split inline headers (e.g., "... Unit 2 ...")
        normalized = (syllabus or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized = _re.sub(
            r"(?i)(?<!^)(?<!\n)\s*((?:unit|units|module|chapter)\s*\d+\b)",
            r"\n\1",
            normalized,
        )

        unit_header = _re.compile(r"^(unit|units|module|chapter)\s*(\d+)\s*[:\-]?\s*(.*)", _re.IGNORECASE)
        for line in [ln.strip() for ln in normalized.splitlines() if ln.strip()]:
            m = unit_header.match(line)
            if m:
                if current:
                    units.append(current)

                idx = m.group(2) if m.group(2) else str(len(units) + 1)
                unit_label = m.group(1).upper().rstrip("S")
                details_raw = (m.group(3) or "").strip()
                details_clean = _re.split(r"\s*(?:->|→)\s*", details_raw, maxsplit=1)[0].strip()

                title = f"{unit_label} {idx}"
                if details_clean:
                    title = f"{title}: {details_clean}"

                # Extract unit hours if present, e.g. "(10 hours)" or "10 Hrs"
                hours = None
                hours_m = _re.search(r"\(\s*(\d{1,3})\s*(?:hours?|hrs?)\s*\)", line, flags=_re.IGNORECASE)
                if not hours_m:
                    hours_m = _re.search(r"\b(\d{1,3})\s*(?:hours?|hrs?)\b", line, flags=_re.IGNORECASE)
                if hours_m:
                    try:
                        hours = int(hours_m.group(1))
                    except Exception:
                        hours = None

                current = {"unit": title, "topics": []}
                if hours is not None:
                    current["hours"] = hours

                # If topics are in parenthesis on the same line, seed topics directly.
                inline_topic_groups = _re.findall(r"\(([^\)]{3,})\)", details_clean)
                for grp in inline_topic_groups:
                    for tok in [t.strip(" -") for t in _re.split(r"[,;/|]+", grp) if t.strip()]:
                        current["topics"].append(tok)
            else:
                if current is None:
                    current = {"unit": "UNIT 1", "topics": []}
                topic = _re.sub(r"^[\-\*\d\.\)\(\s]+", "", line).strip()
                if topic:
                    current["topics"].append(topic)
        if current:
            units.append(current)
        if not units and syllabus.strip():
            # No headers — split by double newline as paragraphs
            paras = [p.strip() for p in syllabus.split("\n\n") if len(p.strip()) > 20]
            for i, para in enumerate(paras[:8], 1):
                units.append({"unit": f"Topic {i}", "topics": [para[:200]]})
        return units

    def _coverage_issues(self, units: List[Dict[str, Any]], cos_data: List[Dict[str, Any]]) -> List[str]:
        """
        Pre-persist coverage validation on candidate COs.

        Rules implemented (aligned with Part 2 spec intent):
        - Every unit should be covered by at least one CO (best-effort via keyword overlap).
        - Units with the highest teaching hours are treated as priority and MUST be covered.
        """
        issues: List[str] = []
        if not units or not cos_data:
            return issues

        stop_words = {
            "students", "able", "will", "with", "that", "this", "their",
            "using", "from", "into", "have", "been", "unit", "chapter",
            "topic", "section", "module", "each", "also", "course",
        }

        def _kw(text: str) -> set:
            return {
                w for w in re.findall(r"\b[a-z]{4,}\b", (text or "").lower())
                if w not in stop_words
            }

        co_kw_sets = [_kw(str(c.get("statement") or "")) for c in cos_data]

        uncovered_units: List[str] = []
        priority_uncovered: List[str] = []

        # Priority: all units with the maximum hours (ties) must be covered.
        hours_values = [
            int(u.get("hours")) for u in units if isinstance(u.get("hours"), int)
        ]
        max_hours = max(hours_values) if hours_values else None
        priority_units = set()
        if max_hours is not None:
            for u in units:
                if isinstance(u.get("hours"), int) and int(u.get("hours")) == int(max_hours):
                    priority_units.add(str(u.get("unit") or "").strip())

        for unit in units:
            unit_name = str(unit.get("unit", "")).strip()
            topics = unit.get("topics", []) or []
            unit_text = unit_name + " " + " ".join(str(t) for t in topics)
            unit_kw = _kw(unit_text)

            covered = False
            for i in range(len(co_kw_sets)):
                if len(unit_kw & co_kw_sets[i]) >= 2:
                    covered = True
                    break

            if not covered:
                uncovered_units.append(unit_name or "UNIT")
                if unit_name in priority_units:
                    priority_uncovered.append(unit_name or "UNIT")

        if priority_uncovered:
            issues.append(
                "High-hour units are not covered: "
                + ", ".join(priority_uncovered[:5])
                + " — revise COs to include these topics."
            )

        # If multiple units are uncovered, report as a single correction instruction
        # to keep the retry prompt short.
        if uncovered_units and len(uncovered_units) <= 6:
            issues.append(
                "Some syllabus units are not covered: "
                + ", ".join(uncovered_units)
                + " — ensure every unit is covered by at least one CO."
            )
        elif len(uncovered_units) > 6:
            issues.append(
                f"{len(uncovered_units)} syllabus units are not covered — ensure full unit coverage."
            )

        return issues

    def _analyze_units_for_prompt(self, units: List[Dict]) -> List[Dict]:
        cues = {
            "L1": ["define", "list", "identify", "recall", "state", "outline"],
            "L2": ["explain", "describe", "summarize", "classify", "interpret", "discuss"],
            "L3": ["apply", "implement", "solve", "execute", "demonstrate", "use"],
            "L4": ["analyze", "differentiate", "compare", "contrast", "examine", "investigate"],
            "L5": ["evaluate", "justify", "critique", "assess", "verify", "argue"],
            "L6": ["design", "develop", "construct", "formulate", "create", "synthesize"],
        }
        level_to_bloom = {
            "L1": "remember", "L2": "understand", "L3": "apply",
            "L4": "analyze",  "L5": "evaluate",  "L6": "create",
        }
        defaults = {
            "L1": "identify", "L2": "explain",  "L3": "apply",
            "L4": "analyze",  "L5": "evaluate", "L6": "design",
        }
        level_order = ["L1", "L2", "L3", "L4", "L5", "L6"]

        # Determine max hours for priority flagging
        hours_values = [int(u["hours"]) for u in units if isinstance(u.get("hours"), int)]
        max_hours = max(hours_values) if hours_values else None

        result: List[Dict] = []
        for unit in units:
            unit_name = str(unit.get("unit", "")).strip() or "UNIT"
            topics = unit.get("topics", []) or []
            hours = unit.get("hours")
            text_blob = (unit_name + " " + " ".join(str(t) for t in topics)).lower()

            scores = {lvl: 0 for lvl in level_order}
            for lvl in level_order:
                for cue in cues[lvl]:
                    if re.search(rf"\b{re.escape(cue)}\b", text_blob):
                        scores[lvl] += 1

            if all(v == 0 for v in scores.values()):
                scores["L3"] = 1

            dominant = max(level_order, key=lambda lvl: (scores[lvl], level_order.index(lvl)))

            # Hour-weighting: units with max hours must be at least L3
            is_priority = max_hours is not None and isinstance(hours, int) and hours == max_hours
            if is_priority and level_order.index(dominant) < level_order.index("L3"):
                dominant = "L3"

            entry: Dict = {
                "unit": unit_name,
                "topics": topics,
                "complexity_score": int(dominant[1]),
                "bt_level": dominant,
                "bloom_level": level_to_bloom[dominant],
                "suggested_action_verb": defaults[dominant],
                "is_priority": is_priority,
            }
            if hours is not None:
                entry["hours"] = hours
            result.append(entry)
        return result

    def _build_po_context(self, program_outcomes: Optional[List[Dict]]) -> str:
        if not program_outcomes:
            return ""
        lines = "\n".join(
            f"  {po['code']}: {po.get('statement') or po.get('name') or po['code']}"
            for po in program_outcomes[:12]
        )
        return f"\nProgram Outcomes (PO context for alignment):\n{lines}\n"

    def _build_pso_context(self, program_specific_outcomes: Optional[List[Dict]]) -> str:
        if not program_specific_outcomes:
            return ""
        lines = "\n".join(
            f"  {pso['code']}: {pso.get('statement') or pso.get('name') or pso['code']}"
            for pso in program_specific_outcomes
        )
        return f"\nProgram Specific Outcomes (PSOs) — map each CO to relevant PSOs:\n{lines}\n"

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
            elif po_input.get("statement"):
                po_obj.statement = po_input["statement"]
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
            elif pso_input.get("statement"):
                pso_obj.statement = pso_input["statement"]
            db_map[code] = pso_obj
        return db_map


    # ── Unit coverage validation ───────────────────────────────────────────────

    def _validate_unit_coverage(
        self,
        units: List[Dict],
        created_cos: List[CourseOutcome],
    ) -> Dict[str, Any]:
        """
        Check that every parsed syllabus unit is covered by at least one CO.
        Coverage = at least 2 overlapping content keywords between unit topics and CO statement.
        Returns covered/uncovered unit lists and coverage percentage.
        """
        stop_words = {
            "students", "able", "will", "with", "that", "this", "their",
            "using", "from", "into", "have", "been", "unit", "chapter",
            "topic", "section", "module", "each", "also", "course",
        }

        def _kw(text: str) -> set:
            return {
                w for w in re.findall(r"\b[a-z]{4,}\b", text.lower())
                if w not in stop_words
            }

        co_kw_sets = [
            _kw(co.statement or "")
            for co in created_cos
        ]

        covered: List[str] = []
        uncovered: List[str] = []
        unit_details: List[Dict] = []

        for unit in units:
            unit_name = str(unit.get("unit", ""))
            topics = unit.get("topics", [])
            unit_text = unit_name + " " + " ".join(str(t) for t in topics)
            unit_kw = _kw(unit_text)

            covering_cos: List[str] = []
            for i, co in enumerate(created_cos):
                overlap = len(unit_kw & co_kw_sets[i])
                if overlap >= 2:
                    covering_cos.append(co.code)

            if covering_cos:
                covered.append(unit_name)
            else:
                uncovered.append(unit_name)

            unit_details.append({
                "unit": unit_name,
                "covered": bool(covering_cos),
                "covered_by": covering_cos,
            })

        total = len(units)
        return {
            "total_units": total,
            "covered_count": len(covered),
            "uncovered_count": len(uncovered),
            "coverage_pct": round(len(covered) / total * 100, 1) if total else 100.0,
            "covered_units": covered,
            "uncovered_units": uncovered,
            "unit_details": unit_details,
        }

    # ── CO-PO mapping with justification ──────────────────────────────────────

    async def _map_cos_to_pos_with_justification(
        self,
        created_cos: List[CourseOutcome],
        program_outcomes: List[Dict],
        program_specific_outcomes: List[Dict],
        po_db: Dict[str, "ProgramOutcome"],
        pso_db: Dict[str, "ProgramSpecificOutcome"],
        course_id: str,
    ) -> Dict[str, Dict[str, str]]:
        """
        For each CO, call LLM with a focused single-CO prompt to get PO/PSO
        correlation levels AND justification text. Runs sequentially to avoid
        overwhelming the local Ollama instance. Falls back to keyword similarity
        if LLM fails for any individual CO.
        """
        all_justifications: Dict[str, Dict[str, str]] = {}
        pos_input = program_outcomes[:12]  # cap at 12 NBA POs
        psos_input = program_specific_outcomes[:6]

        # Track PSO coverage to enforce "each PSO mapped by at least 2 COs"
        pso_coverage: Dict[str, int] = {}

        for co in created_cos:
            co_bloom = str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level)
            prompt = build_co_po_mapping_prompt(
                co_code=co.code,
                co_statement=co.statement or "",
                co_bloom=co_bloom,
                pos=pos_input,
                psos=psos_input if psos_input else None,
            )

            co_levels: Dict[str, int] = {}
            co_pso_levels: Dict[str, int] = {}
            co_justifications: Dict[str, str] = {}

            try:
                response = await asyncio.wait_for(
                    self.llm.generate_completion(prompt, system_prompt=_CO_SYSTEM_PROMPT),
                    timeout=45.0,
                )
                if response:
                    parsed = _extract_json(response)
                    if isinstance(parsed, dict):
                        raw_po = parsed.get("po_mapping", {})
                        raw_pso = parsed.get("pso_mapping", {})
                        raw_just = parsed.get("justification", {})
                        co_levels = {
                            k: max(0, min(3, int(v)))
                            for k, v in raw_po.items()
                            if isinstance(v, (int, float))
                        }
                        co_pso_levels = {
                            k: max(0, min(3, int(v)))
                            for k, v in raw_pso.items()
                            if isinstance(v, (int, float))
                        }
                        co_justifications = {
                            k: str(v)[:200]
                            for k, v in raw_just.items()
                            if isinstance(v, str) and v.strip()
                        }
            except Exception as exc:
                logger.warning(f"LLM mapping failed for {co.code}: {exc} — using keyword fallback")
                # Keyword-based fallback: TF-IDF-style overlap scoring
                co_kw = set(re.findall(r"\b[a-z]{4,}\b", (co.statement or "").lower()))
                for po in pos_input:
                    po_kw = set(re.findall(r"\b[a-z]{4,}\b", (po.get("statement", "") or "").lower()))
                    overlap = len(co_kw & po_kw)
                    if overlap >= 4:
                        co_levels[po["code"]] = 3
                    elif overlap >= 2:
                        co_levels[po["code"]] = 2
                    elif overlap >= 1:
                        co_levels[po["code"]] = 1

            # Persist PO mappings
            for po_code, level in co_levels.items():
                if level <= 0:
                    continue
                po_obj = po_db.get(po_code)
                if po_obj:
                    # Delete existing mapping for this CO+PO pair first
                    await self.session.execute(
                        co_po_mapping_table.delete().where(
                            co_po_mapping_table.c.course_outcome_id == co.id,
                            co_po_mapping_table.c.program_outcome_id == po_obj.id,
                        )
                    )
                    await self.session.execute(
                        co_po_mapping_table.insert().values(
                            course_outcome_id=co.id,
                            program_outcome_id=po_obj.id,
                            similarity_score=round(level / 3.0, 6),
                        )
                    )

            # Persist PSO mappings
            for pso_code, level in co_pso_levels.items():
                if level <= 0:
                    continue
                pso_obj = pso_db.get(pso_code)
                if pso_obj:
                    await self.session.execute(
                        co_pso_mapping_table.delete().where(
                            co_pso_mapping_table.c.course_outcome_id == co.id,
                            co_pso_mapping_table.c.program_specific_outcome_id == pso_obj.id,
                        )
                    )
                    await self.session.execute(
                        co_pso_mapping_table.insert().values(
                            course_outcome_id=co.id,
                            program_specific_outcome_id=pso_obj.id,
                            similarity_score=round(level / 3.0, 6),
                        )
                    )
                    pso_coverage[pso_code] = pso_coverage.get(pso_code, 0) + 1

            all_justifications[co.code] = co_justifications
            await self.session.flush()

        # ── Enforce PSO coverage rule: each PSO mapped by at least 2 COs ──────
        if psos_input and pso_db:
            # Build coarse keyword sets for each CO once
            co_kw_cache: Dict[str, set] = {}
            for co in created_cos:
                co_kw_cache[co.id] = set(
                    re.findall(r"\b[a-z]{4,}\b", (co.statement or "").lower())
                )

            for pso in psos_input:
                code = pso.get("code")
                if not code or code not in pso_db:
                    continue
                current = pso_coverage.get(code, 0)
                if current >= 2:
                    continue

                # Need to add (2 - current) weakest level-1 mappings based on keyword overlap.
                needed = 2 - current
                pso_kw = set(
                    re.findall(r"\b[a-z]{4,}\b", (pso.get("statement") or "").lower())
                )
                # Rank COs by overlap, ignoring those that already have a mapping for this PSO.
                candidates: List[Tuple[CourseOutcome, int]] = []
                for co in created_cos:
                    existing_level = 0
                    # Quick check whether mapping already exists in DB for this PSO
                    # (we rely on pso_coverage counts to avoid double counting).
                    kw_overlap = len(co_kw_cache.get(co.id, set()) & pso_kw)
                    if kw_overlap > 0:
                        candidates.append((co, kw_overlap))

                candidates.sort(key=lambda t: t[1], reverse=True)
                for co, _score in candidates[:needed]:
                    pso_obj = pso_db.get(code)
                    if not pso_obj:
                        continue
                    await self.session.execute(
                        co_pso_mapping_table.insert().values(
                            course_outcome_id=co.id,
                            program_specific_outcome_id=pso_obj.id,
                            similarity_score=round(1 / 3.0, 6),  # weak but non-zero
                        )
                    )
                    pso_coverage[code] = pso_coverage.get(code, 0) + 1

        await self.session.commit()
        logger.info(f"CO-PO mapping with justification complete for course {course_id}")
        return all_justifications

    async def _reload_mappings(
        self,
        created_cos: List[CourseOutcome],
    ) -> tuple:
        """Reload PO and PSO mappings from DB after async mapping step."""
        co_ids = [co.id for co in created_cos]
        po_rows = (await self.session.execute(
            co_po_mapping_table.select().where(
                co_po_mapping_table.c.course_outcome_id.in_(co_ids)
            )
        )).fetchall()
        pso_rows = (await self.session.execute(
            co_pso_mapping_table.select().where(
                co_pso_mapping_table.c.course_outcome_id.in_(co_ids)
            )
        )).fetchall()

        co_id_to_code = {co.id: co.code for co in created_cos}

        # Resolve PO codes
        po_id_to_code: Dict[str, str] = {}
        if po_rows:
            po_ids = list({r[1] for r in po_rows})
            po_objs = (await self.session.execute(
                select(ProgramOutcome).where(ProgramOutcome.id.in_(po_ids))
            )).scalars().all()
            po_id_to_code = {po.id: po.code for po in po_objs}

        pso_id_to_code: Dict[str, str] = {}
        if pso_rows:
            pso_ids = list({r[1] for r in pso_rows})
            pso_objs = (await self.session.execute(
                select(ProgramSpecificOutcome).where(ProgramSpecificOutcome.id.in_(pso_ids))
            )).scalars().all()
            pso_id_to_code = {pso.id: pso.code for pso in pso_objs}

        co_po_mappings = [
            {
                "co_code": co_id_to_code.get(r[0], ""),
                "po_code": po_id_to_code.get(r[1], ""),
                "mapping_level": round(float(r[2]) * 3),
            }
            for r in po_rows
            if co_id_to_code.get(r[0]) and po_id_to_code.get(r[1])
        ]
        co_pso_mappings = [
            {
                "co_code": co_id_to_code.get(r[0], ""),
                "pso_code": pso_id_to_code.get(r[1], ""),
                "mapping_level": round(float(r[2]) * 3),
            }
            for r in pso_rows
            if co_id_to_code.get(r[0]) and pso_id_to_code.get(r[1])
        ]
        return co_po_mappings, co_pso_mappings

    # ── Inline CO edit (manual statement update with validation) ─────────────

    async def update_co_statement(
        self,
        course_id: str,
        co_id: str,
        new_statement: str,
        new_bloom_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Faculty inline edit: update CO statement and optionally bloom level.
        Validates NBA quality rules before saving.
        Returns updated CO + any validation warnings.
        """
        co_result = await self.session.execute(
            select(CourseOutcome).where(
                CourseOutcome.id == co_id,
                CourseOutcome.course_id == course_id,
            )
        )
        co = co_result.scalar_one_or_none()
        if not co:
            raise ValueError(f"CO {co_id} not found for course {course_id}")

        stmt = new_statement.strip()
        if not stmt:
            raise ValueError("Statement cannot be empty")

        current_bloom = str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level)
        target_bloom = (new_bloom_level or current_bloom).strip().lower()
        target_bloom = _BLOOM_ALIASES.get(target_bloom, target_bloom)
        if target_bloom not in _BLOOM_VALID:
            target_bloom = current_bloom

        valid, reason = _validate_co_quality({"statement": stmt}, target_bloom)
        warnings: List[str] = []
        if not valid:
            warnings.append(f"Quality warning: {reason}")

        # Check overlap with sibling COs
        siblings_result = await self.session.execute(
            select(CourseOutcome).where(
                CourseOutcome.course_id == course_id,
                CourseOutcome.id != co_id,
            )
        )
        siblings = list(siblings_result.scalars().all())
        new_kw = set(re.findall(r"\b[a-z]{4,}\b", stmt.lower()))
        stop = {"students", "able", "will", "with", "that", "this", "their", "using", "from", "into", "have", "been"}
        new_kw -= stop
        for sib in siblings:
            sib_kw = set(re.findall(r"\b[a-z]{4,}\b", (sib.statement or "").lower())) - stop
            shared = new_kw & sib_kw
            if len(shared) >= 5:
                warnings.append(f"Possible overlap with {sib.code}: shared terms {', '.join(list(shared)[:4])}")

        # Save per-CO version before overwriting
        await _append_co_item_version(
            course_id=course_id,
            co_code=co.code,
            snapshot={
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                "co_code": co.code,
                "statement": (co.statement or ""),
                "bloom_level": current_bloom,
                "source": "faculty_inline_edit",
                "reason": "",
            },
        )

        co.statement = stmt
        co.bloom_level = _normalise_bloom(target_bloom)
        await self.session.commit()
        logger.info(f"CO {co_id} statement updated manually for course {course_id}")

        return {
            "id": co.id,
            "code": co.code,
            "statement": co.statement,
            "bloom_level": target_bloom,
            "warnings": warnings,
            "valid": not bool([w for w in warnings if "Quality" in w]),
        }

    # ── CO generation history ─────────────────────────────────────────────────

    async def get_co_history(self, course_id: str) -> List[Dict]:
        """Return previous CO version snapshots from Redis."""
        try:
            data = await get_json(_co_history_key(course_id))
            return (data or {}).get("versions", [])
        except Exception:
            return []

    async def get_co_session(self, course_id: str) -> Optional[Dict]:
        """Return last generation session context from Redis."""
        try:
            return await get_json(_co_session_key(course_id))
        except Exception:
            return None

    # ── Per-CO item history + rollback ───────────────────────────────────────

    async def get_co_item_history(self, course_id: str, co_code: str) -> List[Dict[str, Any]]:
        """Return per-CO versions (latest first) from Redis."""
        try:
            data = await get_json(_co_item_history_key(course_id, co_code))
            return (data or {}).get("versions", [])
        except Exception:
            return []

    async def rollback_co_to_version(self, course_id: str, co_id: str, version_index: int = 0) -> CourseOutcome:
        """
        Roll back a CO to a previous version stored in per-CO Redis history.
        version_index=0 means the latest saved snapshot.
        """
        co_result = await self.session.execute(
            select(CourseOutcome).where(
                CourseOutcome.id == co_id,
                CourseOutcome.course_id == course_id,
            )
        )
        co = co_result.scalar_one_or_none()
        if not co:
            raise ValueError(f"CO {co_id} not found for course {course_id}")

        versions = await self.get_co_item_history(course_id, co.code)
        if not versions:
            raise ValueError("No per-CO history found to roll back")
        if version_index < 0 or version_index >= len(versions):
            raise ValueError(f"Invalid version index {version_index}; available 0..{len(versions) - 1}")

        target = versions[version_index] or {}
        statement = str(target.get("statement") or "").strip()
        bloom = str(target.get("bloom_level") or "").strip().lower()
        if not statement:
            raise ValueError("Selected version snapshot has empty statement")

        # Save current state before rollback
        current_bloom = str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level)
        await _append_co_item_version(
            course_id=course_id,
            co_code=co.code,
            snapshot={
                "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
                "co_code": co.code,
                "statement": co.statement,
                "bloom_level": current_bloom,
                "source": "rollback_backup",
                "reason": f"rollback_to_index_{version_index}",
            },
        )

        co.statement = statement
        if bloom:
            co.bloom_level = _normalise_bloom(bloom)
        await self.session.commit()
        return co

    # ── NBA SAR export ────────────────────────────────────────────────────────

    async def export_nba_sar(
        self,
        course_id: str,
        program_outcomes: Optional[List[Dict]] = None,
    ) -> bytes:
        """
        Generate NBA SAR (Self-Assessment Report) table as CSV bytes.
        Columns: CO No | CO Statement | BT Level | PO1..PO12 (levels) | Attainment Target | Attainment Achieved | Gap
        All data is read from DB — no hardcodes.
        """
        import csv, io

        course = await self._get_course(course_id)

        # Load COs
        cos_result = await self.session.execute(
            select(CourseOutcome).where(CourseOutcome.course_id == course_id).order_by(CourseOutcome.code)
        )
        cos = list(cos_result.scalars().all())

        # Load PO list dynamically from DB
        po_result = await self.session.execute(
            select(ProgramOutcome).order_by(ProgramOutcome.code)
        )
        all_pos = list(po_result.scalars().all())
        # Deduplicate by code, prefer those with mappings for this course
        seen_codes: set = set()
        pos_for_export: List[ProgramOutcome] = []
        for po in all_pos:
            if po.code not in seen_codes:
                seen_codes.add(po.code)
                pos_for_export.append(po)
        po_codes = [po.code for po in pos_for_export]

        # Load CO-PO mappings
        co_ids = [co.id for co in cos]
        po_map_rows = (await self.session.execute(
            co_po_mapping_table.select().where(
                co_po_mapping_table.c.course_outcome_id.in_(co_ids)
            )
        )).fetchall() if co_ids else []

        # Build mapping dict: co_id -> {po_id -> level}
        po_id_to_code = {po.id: po.code for po in pos_for_export}
        co_po_levels: Dict[str, Dict[str, int]] = {co.id: {} for co in cos}
        for row in po_map_rows:
            co_id, po_id, sim = row[0], row[1], float(row[2])
            level = round(sim * 3)
            po_code = po_id_to_code.get(po_id)
            if po_code and co_id in co_po_levels:
                co_po_levels[co_id][po_code] = level

        # Load attainment data
        att_result = await self.session.execute(
            select(COAttainment).where(COAttainment.course_outcome_id.in_(co_ids))
        ) if co_ids else None
        att_by_co: Dict[str, COAttainment] = {}
        if att_result:
            for att in att_result.scalars().all():
                if att.course_outcome_id not in att_by_co:
                    att_by_co[att.course_outcome_id] = att

        # Write CSV
        buf = io.StringIO()
        writer = csv.writer(buf)

        # Header
        header = ["CO No", "CO Statement", "BT Level"] + po_codes + ["Attainment Target (%)", "Attainment Achieved (%)", "Gap (%)"]
        writer.writerow(header)

        for co in cos:
            bl = str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level)
            po_levels_row = [str(co_po_levels[co.id].get(pc, 0)) for pc in po_codes]
            att = att_by_co.get(co.id)
            target = 60.0  # NBA standard target
            achieved = round(float(att.attainment_percentage), 1) if att else ""
            gap = round(target - float(att.attainment_percentage), 1) if att else ""
            writer.writerow(
                [co.code, co.statement, bl.capitalize()]
                + po_levels_row
                + [str(target), str(achieved), str(gap)]
            )

        # Summary row
        writer.writerow([])
        writer.writerow([f"Course: {course.course_name} ({course.course_code})", f"Semester: {course.semester or '-'}"])
        writer.writerow(["Correlation levels: 3=Strong, 2=Medium, 1=Weak, 0=None"])
        writer.writerow(["NBA SAR Table — Generated by OBE System"])

        return buf.getvalue().encode("utf-8")


class COGenerationService(CoGenerationService):
    """Backward-compatible alias."""
    pass
