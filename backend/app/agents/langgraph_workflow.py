"""
LangGraph-based OBE workflow orchestration.

Architecture:
    User Message
        ↓
    [nlu_node]   ← Rasa NLU server (keyword fallback when Rasa is offline)
        ↓
    [intent_router]  ← Conditional edge: picks the right handler node
        ↓
    [<intent>_node]  ← Domain-specific workflow handler
        ↓
       END

All 7 OBE core functionalities are covered as dedicated graph nodes:
  1  generate_co              – CO generation / retrieval
  2  configure_exam           – Exam setup workflow guide
  3  map_question_co          – Question → CO mapping
  4  student_marks            – Student marks entry / upload
  5  calculate_attainment     – CO attainment calculation
  6  calculate_po_attainment  – PO / PSO attainment pipeline
  7  generate_report          – Reports & visualisation

Supporting nodes:
     map_co_po               – CO → PO semantic mapping
     map_co_pso              – CO → PSO semantic mapping
     add_questions            – Exam question management guide
     detect_bloom             – Bloom's taxonomy level detection
     list_courses             – Enumerate registered courses
     help / greet             – Usage help
     goodbye                  – Session close
     general_llm              – Catch-all LLM fallback
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("langgraph_workflow")

_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


# ── Graph State ────────────────────────────────────────────────────────────────

class OBEGraphState(TypedDict):
    """
    Shared state that flows through every node in the OBE workflow graph.

    The ``db_session`` key carries the live SQLAlchemy AsyncSession and is
    never serialised/checkpointed – it just passes through in memory.
    """
    # ---- inputs -----------------------------------------------------------
    message: str
    course_id: Optional[str]
    session_id: str
    user_id: Optional[str]   # propagated from JWT; used for Redis state key
    db_session: Any          # sqlalchemy.ext.asyncio.AsyncSession
    force_node: Optional[str]  # if set, intent_router bypasses NLU routing

    # ---- NLU output (populated by nlu_node) --------------------------------
    intent: str
    nlu_confidence: float
    nlu_source: str          # "rasa" | "keyword" | "error"
    entities: List[Dict[str, Any]]

    # ---- handler output (populated by the chosen worker node) --------------
    reply: str
    data: Optional[Dict[str, Any]]
    error: Optional[str]


# ── Static help text ──────────────────────────────────────────────────────────

_HELP_TEXT = """\
I am your **OBE Chatbot Assistant** — powered by **LangGraph** + **Rasa NLU**.

| # | Feature | Example phrase |
|---|---|---|
| 1 | **Generate Course Outcomes** | "Generate COs for this syllabus …" |
| 2 | **Configure Exam** | "Configure exam for my course" |
| 3 | **Map Questions → CO** | "Map questions to course outcomes" |
| 4 | **Enter Student Marks** | "Enter student marks for exam …" |
| 5 | **CO Attainment** | "Calculate CO attainment for course …" |
| 6 | **PO / PSO Attainment** | "Calculate PO and PSO attainment …" |
| 7 | **Reports & Visualisation** | "Generate report for course …" |
| + | **CO → PO Mapping** | "Map COs to POs …" |
| + | **CO → PSO Mapping** | "Map COs to PSOs …" |
| + | **Detect Bloom Level** | "What Bloom level is this question?" |
| + | **List Courses** | "List all courses" |

Provide a `course_id` in your request for course-specific operations.
"""


def _extract_value_from_entities(entities: List[Dict[str, Any]], names: List[str]) -> Optional[str]:
    wanted = {n.lower() for n in names}
    for ent in entities or []:
        ent_name = str(ent.get("entity", "")).lower()
        if ent_name in wanted and ent.get("value"):
            return str(ent.get("value"))
    return None


def _extract_named_token(message: str, keys: List[str]) -> Optional[str]:
    for key in keys:
        m = re.search(rf"{re.escape(key)}\s*[:=]\s*([A-Za-z0-9_\-]+)", message, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _extract_program_id(message: str, entities: List[Dict[str, Any]]) -> Optional[str]:
    by_entity = _extract_value_from_entities(entities, ["program_id", "program"])
    if by_entity:
        return by_entity
    by_named = _extract_named_token(message, ["program_id", "program"])
    if by_named:
        return by_named
    m = re.search(r"\b[A-Z]{2,}(?:-[A-Z0-9]{2,})+\b", message)
    return m.group(0) if m else None


def _extract_exam_id(message: str, entities: List[Dict[str, Any]]) -> Optional[str]:
    by_entity = _extract_value_from_entities(entities, ["exam_id", "exam"])
    if by_entity:
        return by_entity
    by_named = _extract_named_token(message, ["exam_id", "exam"])
    if by_named:
        return by_named
    m = _UUID_RE.search(message)
    return m.group(0) if m else None


# ════════════════════════════════════════════════════════════════════════════════
# NODE 0 – NLU  (Rasa + keyword fallback)
# ════════════════════════════════════════════════════════════════════════════════

async def nlu_node(state: OBEGraphState) -> dict:
    """
    Detect intent from the user message.

    Tries the Rasa NLU server first; falls back transparently to keyword
    matching when the server is offline.
    """
    from app.services.rasa_nlu_client import get_rasa_client

    rasa = get_rasa_client()
    try:
        result = await rasa.parse(state["message"])
        return {
            "intent":         result["intent"]["name"],
            "nlu_confidence": result["intent"].get("confidence", 1.0),
            "nlu_source":     result.get("source", "keyword"),
            "entities":       result.get("entities", []),
        }
    except Exception as exc:
        logger.error(f"nlu_node error: {exc}")
        return {
            "intent":         "general",
            "nlu_confidence": 0.0,
            "nlu_source":     "error",
            "entities":       [],
        }


# ── Conditional router ────────────────────────────────────────────────────────

def intent_router(state: OBEGraphState) -> str:
    """Map the detected intent to the name of the next graph node."""
    if state.get("force_node"):
        return state["force_node"]
    _ROUTING: Dict[str, str] = {
        "generate_co":              "generate_co_node",
        "start_co_generation":      "generate_co_node",
        "provide_syllabus":         "generate_co_node",
        "confirm_po_pso":           "generate_co_node",
        "request_co_count":         "generate_co_node",
        "approve_cos":              "generate_co_node",
        "edit_co":                  "generate_co_node",
        "regenerate_cos":           "generate_co_node",
        "regenerate_single_co":     "generate_co_node",
        "explain_co_bt":            "generate_co_node",
        "configure_exam":           "configure_exam_node",
        "setup_exam":               "configure_exam_node",
        "provide_exam_type":        "configure_exam_node",
        "provide_max_marks":        "configure_exam_node",
        "map_co_po":                "map_co_po_node",
        "map_co_pso":               "map_co_pso_node",
        "map_question_co":          "map_question_co_node",
        "analyse_question":         "detect_bloom_node",
        "add_questions":            "add_questions_node",
        "student_marks":            "student_marks_node",
        "upload_marks_intent":      "student_marks_node",
        "calculate_attainment":     "calculate_attainment_node",
        "explain_attainment":       "calculate_attainment_node",
        "calculate_po_attainment":  "calculate_po_attainment_node",
        "ask_po_attainment":        "calculate_po_attainment_node",
        "ask_ay_history":           "calculate_attainment_node",
        "ask_low_co":               "calculate_attainment_node",
        "detect_bloom":             "detect_bloom_node",
        "generate_report":          "generate_report_node",
        "list_courses":             "list_courses_node",
        "help":                     "help_node",
        "greet":                    "help_node",
        "goodbye":                  "goodbye_node",
        "affirm":                   "help_node",
        "deny":                     "help_node",
        "out_of_scope":             "help_node",
    }
    return _ROUTING.get(state.get("intent", "general"), "general_llm_node")


# ════════════════════════════════════════════════════════════════════════════════
# WORKER NODES
# ════════════════════════════════════════════════════════════════════════════════

# ── Func 1 – CO Generation ───────────────────────────────────────────────────

async def generate_co_node(state: OBEGraphState) -> dict:  # noqa: C901
    """Step-driven CO generation wizard — guides faculty through the 7-step CO creation flow."""
    import re as _re
    from datetime import datetime as _dt

    course_id = state.get("course_id")
    user_id   = state.get("user_id")
    session   = state["db_session"]
    message   = state.get("message", "")
    intent    = state.get("intent", "")
    msg_lower = message.lower().strip()

    if not course_id:
        return {
            "reply": (
                "Please provide a `course_id` to work with Course Outcomes.\n\n"
                "Use the CO Generation page for your course to start the wizard."
            ),
            "data": None,
        }

    step_key = f"chatbot_state:{user_id}:{course_id}" if user_id else f"chatbot_state:anon:{course_id}"

    try:
        from app.core.infrastructure.redis_client import get_json as _get_json, set_json as _set_json
        from app.modules.co_generation.services.co_generation_service import CoGenerationService
        from app.core.database.models import Course, ProgramOutcome, ProgramSpecificOutcome
        from sqlalchemy import select as _select

        raw_state = None
        try:
            raw_state = await _get_json(step_key)
        except Exception:
            pass

        step         = (raw_state or {}).get("step", "course_info")
        session_data = (raw_state or {}).get("session_data", {})
        svc          = CoGenerationService(session)

        async def _save_step(new_step: str, updates: dict = None) -> None:
            merged = {**session_data, **(updates or {})}
            try:
                await _set_json(
                    step_key,
                    {"course_id": course_id, "step": new_step, "session_data": merged,
                     "updated_at": _dt.utcnow().isoformat()},
                    ttl_seconds=86400,
                )
            except Exception:
                pass  # Redis not critical — wizard still works

        # ── STEP course_info ──────────────────────────────────────────────────
        if step == "course_info" or intent in ("start_co_generation", "generate_co") and step not in (
            "syllabus", "po_pso_confirm", "co_count", "generate", "review", "save"
        ):
            res = await session.execute(_select(Course).where(Course.id == course_id))
            course = res.scalar_one_or_none()
            if not course:
                return {"reply": f"Course `{course_id}` not found.", "data": None}
            await _save_step("syllabus")
            return {
                "reply": (
                    f"**CO Generation Wizard — {course.course_name} ({course.course_code})**\n\n"
                    "I'll guide you through 7 steps to create well-structured Course Outcomes (COs).\n\n"
                    "**Step 1 of 7 — Syllabus**\n"
                    "Please paste your course syllabus text (up to 5 000 chars). "
                    + (f"\n_Current syllabus on file: {len(course.syllabus)} chars_ — "
                       "type **'use existing'** to proceed with it."
                       if course.syllabus else "\n_No syllabus saved yet._")
                ),
                "data": {
                    "step": "syllabus",
                    "course_name": course.course_name,
                    "has_existing_syllabus": bool(course.syllabus),
                    "suggested_replies": ["Use existing syllabus", "Paste new syllabus"],
                },
            }

        # ── STEP syllabus ─────────────────────────────────────────────────────
        if step == "syllabus":
            if any(k in msg_lower for k in ("use existing", "use current", "keep", "already")):
                res = await session.execute(_select(Course).where(Course.id == course_id))
                course = res.scalar_one_or_none()
                if course and course.syllabus:
                    await _save_step("po_pso_confirm", {"syllabus": course.syllabus})
                    return {
                        "reply": (
                            "Using your existing syllabus.\n\n"
                            "**Step 2 of 7 — PO/PSO Alignment**\n"
                            "Shall I fetch your program's POs and PSOs and align the COs to them?\n"
                            "Reply **'yes'** to include alignment, or **'skip'** to generate without it."
                        ),
                        "data": {
                            "step": "po_pso_confirm",
                            "syllabus_length": len(course.syllabus),
                            "suggested_replies": ["Yes, align with POs", "Skip PO alignment"],
                        },
                    }
                return {"reply": "No existing syllabus found. Please paste your syllabus text:",
                        "data": {"step": "syllabus"}}

            if len(message) >= 50 or intent == "provide_syllabus":
                syllabus_text = message[:5000]
                res = await session.execute(_select(Course).where(Course.id == course_id))
                course = res.scalar_one_or_none()
                if course:
                    course.syllabus = syllabus_text
                    await session.commit()
                await _save_step("po_pso_confirm", {"syllabus": syllabus_text})
                return {
                    "reply": (
                        f"Syllabus saved ({len(syllabus_text)} chars). \u2713\n\n"
                        "**Step 2 of 7 — PO/PSO Alignment**\n"
                        "Shall I fetch your program's POs and PSOs and align the COs to them?\n"
                        "Reply **'yes'** to include alignment, or **'skip'** to generate without it."
                    ),
                    "data": {
                        "step": "po_pso_confirm",
                        "syllabus_chars": len(syllabus_text),
                        "suggested_replies": ["Yes, align with POs", "Skip PO alignment"],
                    },
                }
            return {
                "reply": (
                    "Please paste your course syllabus text (at least 50 characters). "
                    "You can also type **'use existing'** if you already have a saved syllabus."
                ),
                "data": {"step": "syllabus"},
            }

        # ── STEP po_pso_confirm ───────────────────────────────────────────────
        if step == "po_pso_confirm":
            include = not any(k in msg_lower for k in ("skip", "no ", "without"))
            pos_data: list = []
            psos_data: list = []
            if include:
                po_rows  = (await session.execute(_select(ProgramOutcome).limit(12))).scalars().all()
                pso_rows = (await session.execute(_select(ProgramSpecificOutcome).limit(8))).scalars().all()
                pos_data  = [{"code": p.code, "statement": p.statement} for p in po_rows]
                psos_data = [{"code": p.code, "statement": p.statement} for p in pso_rows]

            await _save_step("co_count", {"pos": pos_data, "psos": psos_data})
            po_summary = ", ".join(p["code"] for p in pos_data[:8]) + ("..." if len(pos_data) > 8 else "")
            return {
                "reply": (
                    (f"Found **{len(pos_data)} POs** ({po_summary}) and **{len(psos_data)} PSOs** for alignment.\n\n"
                     if include and pos_data else "Proceeding without PO/PSO alignment.\n\n")
                    + "**Step 3 of 7 — CO Count**\n"
                      "How many COs do you want to generate? Reply **4**, **5**, or **6**."
                ),
                "data": {
                    "step": "co_count",
                    "po_count": len(pos_data),
                    "pso_count": len(psos_data),
                    "suggested_replies": ["4", "5", "6"],
                },
            }

        # ── STEP co_count ─────────────────────────────────────────────────────
        if step == "co_count":
            m = _re.search(r"\b([456])\b", message)
            if m:
                num = int(m.group(1))
                await _save_step("generate", {"num_cos": num})
                return {
                    "reply": (
                        f"**{num} COs** selected. \u2713\n\n"
                        "**Step 4 of 7 — Generate**\n"
                        f"Ready to generate {num} COs using AI. "
                        "Type **'generate'** or **'proceed'** to start."
                    ),
                    "data": {"step": "generate", "num_cos": num,
                             "suggested_replies": ["Generate", "Proceed"]},
                }
            return {
                "reply": "Please choose the number of COs to generate: reply with **4**, **5**, or **6**.",
                "data": {"step": "co_count", "suggested_replies": ["4", "5", "6"]},
            }

        # ── STEP generate ─────────────────────────────────────────────────────
        if step == "generate":
            go = any(k in msg_lower for k in ("generate", "proceed", "start", "go", "yes", "ok", "do it", "sure"))
            if not go and intent not in ("approve_cos", "generate_co", "start_co_generation", "affirm"):
                return {
                    "reply": ("Ready to generate COs. Type **'generate'** to proceed, "
                              "or **'back'** to change the CO count."),
                    "data": {"step": "generate", "suggested_replies": ["Generate", "Back"]},
                }
            syllabus = session_data.get("syllabus", "")
            num_cos  = session_data.get("num_cos", 5)
            pos_data = session_data.get("pos", [])
            psos_data = session_data.get("psos", [])
            if not syllabus:
                res = await session.execute(_select(Course).where(Course.id == course_id))
                c   = res.scalar_one_or_none()
                syllabus = (c.syllabus or "") if c else ""
            if not syllabus:
                await _save_step("syllabus")
                return {"reply": "No syllabus found. Please paste your course syllabus:",
                        "data": {"step": "syllabus"}}

            gen = await svc.generate_cos_from_syllabus(
                course_id=course_id, syllabus=syllabus,
                program_outcomes=pos_data, program_specific_outcomes=psos_data,
                num_cos=num_cos,
            )
            generated_cos = gen["course_outcomes"]
            co_lines = "\n".join(
                f"**{co.code}** "
                f"({str(co.bloom_level.value if hasattr(co.bloom_level, 'value') else co.bloom_level).capitalize()}): "
                f"{co.statement}"
                for co in generated_cos
            )
            await _save_step("review", {"generated_co_codes": [co.code for co in generated_cos]})
            return {
                "reply": (
                    f"**Generated {len(generated_cos)} Course Outcomes:** \u2713\n\n{co_lines}\n\n"
                    "**Step 5 of 7 — Review**\n"
                    "Review the COs in the table on the right pane. You can:\n"
                    "- Type **'redo CO2 only'** to regenerate a specific CO\n"
                    "- Type **'why is CO3 Level 4?'** for Bloom's reasoning\n"
                    "- Type **'save'** to finalise and save all COs"
                ),
                "data": {
                    "step": "review",
                    "cos": [
                        {"code": co.code, "statement": co.statement,
                         "bloom_level": str(co.bloom_level.value if hasattr(co.bloom_level, "value") else co.bloom_level)}
                        for co in generated_cos
                    ],
                    "co_count": len(generated_cos),
                    "co_po_mappings": gen["co_po_mappings"],
                    "suggested_replies": ["Save all COs", "Redo CO1 only", "Why is CO3 Level 4?"],
                },
            }

        # ── STEP review / save ────────────────────────────────────────────────
        if step in ("review", "save"):
            _BT_EXPLAIN = {
                "remember":  "L1 — students recall facts. Verbs: define, list, state.",
                "understand": "L2 — students explain in own words. Verbs: explain, describe, summarise.",
                "apply":     "L3 — students use knowledge to solve problems. Verbs: apply, implement, solve.",
                "analyze":   "L4 — students break down complex ideas. Verbs: analyse, compare, differentiate.",
                "evaluate":  "L5 — students judge and justify. Verbs: evaluate, justify, critique.",
                "create":    "L6 — students design new work. Verbs: design, develop, construct.",
            }

            # BT explanation request
            if intent == "explain_co_bt" or _re.search(r"why.*(co\d+|level|bloom|bt)", msg_lower):
                m = _re.search(r"co(\d+)", msg_lower)
                co_code = f"CO{m.group(1)}" if m else None
                cos = await svc.get_course_outcomes(course_id)
                tgt = next((c for c in cos if co_code and c.code.upper() == co_code.upper()), None)
                if tgt:
                    bl = str(tgt.bloom_level.value if hasattr(tgt.bloom_level, "value") else tgt.bloom_level)
                    return {
                        "reply": (
                            f"**{tgt.code}** is at **{bl.capitalize()}** because:\n\n"
                            f"_{tgt.statement}_\n\n"
                            f"{_BT_EXPLAIN.get(bl, bl.capitalize())}\n\n"
                            "The action verb in the statement determines the cognitive level."
                        ),
                        "data": {"co_code": tgt.code, "bloom_level": bl},
                    }
                return {"reply": f"CO not found. Check the CO code.", "data": None}

            # Single CO regeneration
            if intent == "regenerate_single_co" or _re.search(r"(redo|regenerate|regen|rewrite|change).*co\d+", msg_lower):
                m = _re.search(r"co(\d+)", msg_lower)
                if m:
                    co_code = f"CO{m.group(1)}"
                    cos = await svc.get_course_outcomes(course_id)
                    tgt = next((c for c in cos if c.code.upper() == co_code.upper()), None)
                    if tgt:
                        updated = await svc.regenerate_single_co(course_id=course_id, co_id=tgt.id)
                        bl = str(updated.bloom_level.value if hasattr(updated.bloom_level, "value") else updated.bloom_level)
                        return {
                            "reply": (
                                f"**{co_code} regenerated!** \u2713\n\n"
                                f"New statement: _{updated.statement}_\n"
                                f"BT Level: {bl.capitalize()}\n\n"
                                "Continue reviewing or type **'save'** to finalise."
                            ),
                            "data": {"co_code": co_code, "statement": updated.statement, "bloom_level": bl},
                        }
                    return {"reply": f"CO {co_code} not found. Check the CO code.", "data": None}
                return {"reply": "Please specify which CO to redo (e.g., **'redo CO3 only'**).", "data": None}

            # Save intent
            if any(k in msg_lower for k in ("save", "done", "finalise", "finalize", "complete")) or intent == "approve_cos":
                cos = await svc.get_course_outcomes(course_id)
                await _save_step("save")
                return {
                    "reply": (
                        f"**All {len(cos)} COs saved successfully!** \u2713\n\n"
                        "Your Course Outcomes are now active in the system.\n"
                        "Next steps:\n"
                        "- Map COs to POs: `POST /api/v1/map-co-po`\n"
                        "- Configure exams and add questions\n"
                        "- Check the CO coverage panel at the bottom of the right pane"
                    ),
                    "data": {
                        "step": "save",
                        "co_count": len(cos),
                        "cos": [{"code": co.code, "statement": co.statement} for co in cos],
                    },
                }

            # Default review listing
            cos = await svc.get_course_outcomes(course_id)
            co_lines = "\n".join(f"**{co.code}**: {co.statement}" for co in cos)
            return {
                "reply": (
                    f"**Current COs ({len(cos)}):**\n\n{co_lines}\n\n"
                    "- Type **'redo CO2 only'** to regenerate a specific CO\n"
                    "- Type **'why is CO3 Level 4?'** for Bloom's reasoning\n"
                    "- Type **'save'** to finalise"
                ),
                "data": {"step": "review", "co_count": len(cos),
                         "suggested_replies": ["Save all COs", "Redo CO1 only"]},
            }

        # ── FALLBACK: show existing COs or start wizard ────────────────────────
        cos = await svc.get_course_outcomes(course_id)
        if cos:
            co_lines = "\n".join(
                f"- **{co.code}** ({str(co.bloom_level.value if hasattr(co.bloom_level, 'value') else co.bloom_level).capitalize()}): {co.statement}"
                for co in cos
            )
            return {
                "reply": (
                    f"**Course Outcomes ({len(cos)}):**\n\n{co_lines}\n\n"
                    "Type **'start'** to begin a new CO generation session."
                ),
                "data": {"co_count": len(cos), "course_id": course_id},
            }
        return {
            "reply": "No COs found for this course. Type **'start'** to begin CO generation.",
            "data": {"course_id": course_id},
        }

    except Exception as exc:
        logger.error(f"generate_co_node: {exc}")
        return {"reply": f"CO generation error: {exc}", "data": None}


# ── Func 2 – Exam Configuration ──────────────────────────────────────────────

async def configure_exam_node(state: OBEGraphState) -> dict:
    """Guide the exam setup step-by-step workflow."""
    course_id = state.get("course_id")
    cid_str = f" for course `{course_id}`" if course_id else ""
    return {
        "reply": (
            f"**Exam Configuration Workflow{cid_str}:**\n\n"
            "**Step 1** – Create exam:\n"
            "```\nPOST /api/v1/courses/{course_id}/exams\n"
            "{\n"
            '  "title": "Mid Semester",\n'
            '  "exam_type": "internal",\n'
            '  "total_marks": 50\n'
            "}\n```\n\n"
            "**Step 2** – Add questions:\n"
            "```\nPOST /api/v1/exams/{exam_id}/questions\n"
            "{\n"
            '  "questions": [\n'
            '    {"question_number": 1, "question_text": "...", "marks": 10}\n'
            "  ]\n"
            "}\n```\n\n"
            "**Step 3** – Map questions to COs:\n"
            "```\nPOST /api/v1/exams/{exam_id}/map-questions\n```\n\n"
            "**Step 4** – Enter student marks:\n"
            "```\nPOST /api/v1/exams/{exam_id}/marks\n```"
        ),
        "data": {"course_id": course_id},
    }


# ── CO → PO Mapping ──────────────────────────────────────────────────────────

async def map_co_po_node(state: OBEGraphState) -> dict:
    course_id = state.get("course_id")
    entities = state.get("entities", [])
    program_id = _extract_program_id(state["message"], entities)
    if not course_id or not program_id:
        return {
            "reply": (
                "Provide `course_id` and `program_id` for CO→PO semantic mapping.\n"
                "Example: `map co to po program_id=BTECH-CSE-2026`\n\n"
                "```\nPOST /api/v1/map-co-po?course_id=…&program_id=…\n```\n\n"
                "Optional: `&threshold=0.3` to control alignment sensitivity."
            ),
            "data": None,
        }
    try:
        from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
        session = state["db_session"]
        svc = SemanticMappingService(session)
        result = await svc.map_cos_to_pos(session, course_id, program_id)
        if not result.get("success"):
            return {"reply": f"CO→PO mapping failed: {result.get('message') or result.get('error', 'unknown error')}", "data": result}
        mapping_count = result.get("mapping_count", 0)
        return {
            "reply": (
                f"CO→PO mapping completed for course `{course_id}` and program `{program_id}`.\n"
                f"Mappings created: **{mapping_count}**"
            ),
            "data": result,
        }
    except Exception as exc:
        logger.error(f"map_co_po_node: {exc}")
        return {"reply": f"CO→PO mapping error: {exc}", "data": None}


# ── CO → PSO Mapping ─────────────────────────────────────────────────────────

async def map_co_pso_node(state: OBEGraphState) -> dict:
    course_id = state.get("course_id")
    entities = state.get("entities", [])
    program_id = _extract_program_id(state["message"], entities)
    if not course_id or not program_id:
        return {
            "reply": (
                "Provide `course_id` and `program_id` for CO→PSO semantic mapping.\n\n"
                "```\nPOST /api/v1/map-co-pso?course_id=…&program_id=…\n```"
            ),
            "data": None,
        }
    try:
        from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
        session = state["db_session"]
        svc = SemanticMappingService(session)
        result = await svc.map_cos_to_psos(session, course_id, program_id)
        if not result.get("success"):
            return {"reply": f"CO→PSO mapping failed: {result.get('message') or result.get('error', 'unknown error')}", "data": result}
        mapping_count = result.get("mapping_count", 0)
        return {
            "reply": (
                f"CO→PSO mapping completed for course `{course_id}` and program `{program_id}`.\n"
                f"Mappings created: **{mapping_count}**"
            ),
            "data": result,
        }
    except Exception as exc:
        logger.error(f"map_co_pso_node: {exc}")
        return {"reply": f"CO→PSO mapping error: {exc}", "data": None}


# ── Func 3 – Question → CO Mapping ──────────────────────────────────────────

async def map_question_co_node(state: OBEGraphState) -> dict:
    """Automatically map exam questions to Course Outcomes."""
    course_id = state.get("course_id")
    entities = state.get("entities", [])
    exam_id = _extract_exam_id(state["message"], entities)
    if not course_id or not exam_id:
        return {
            "reply": (
                "Provide both `course_id` and `exam_id` to run question→CO mapping.\n"
                "Example: `map questions to co exam_id=<uuid>`"
            ),
            "data": None,
        }
    try:
        from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
        session = state["db_session"]
        svc = SemanticMappingService(session)
        result = await svc.map_questions_to_cos(session, exam_id, course_id)
        if not result.get("success"):
            return {"reply": f"Question→CO mapping failed: {result.get('message') or result.get('error', 'unknown error')}", "data": result}
        return {
            "reply": f"Question→CO mapping completed for exam `{exam_id}`. Mappings created: **{result.get('mapping_count', 0)}**",
            "data": result,
        }
    except Exception as exc:
        logger.error(f"map_question_co_node: {exc}")
        return {"reply": f"Question→CO mapping error: {exc}", "data": None}


# ── Add Questions ─────────────────────────────────────────────────────────────

async def add_questions_node(state: OBEGraphState) -> dict:
    return {
        "reply": (
            "**Adding Questions to an Exam:**\n\n"
            "```\nPOST /api/v1/exams/{exam_id}/questions\n"
            "{\n"
            '  "questions": [\n'
            '    {"question_number": 1, "question_text": "Describe...", "marks": 10},\n'
            '    {"question_number": 2, "question_text": "Apply...", "marks": 15}\n'
            "  ]\n"
            "}\n```\n\n"
            "Next steps:\n"
            "1. Map to COs: **POST /api/v1/exams/{exam_id}/map-questions**\n"
            "2. Enter marks: **POST /api/v1/exams/{exam_id}/marks**"
        ),
        "data": None,
    }


# ── Func 4 – Student Marks Entry ─────────────────────────────────────────────

async def student_marks_node(state: OBEGraphState) -> dict:
    """Guide marks entry and upload."""
    return {
        "reply": (
            "**Student Marks Entry:**\n\n"
            "**Option A – JSON API:**\n"
            "```\nPOST /api/v1/exams/{exam_id}/marks\n"
            "{\n"
            '  "rows": [\n'
            '    {"student_id": "S001", "marks": {"1": 8,  "2": 7,  "3": 12}},\n'
            '    {"student_id": "S002", "marks": {"1": 6,  "2": 5,  "3": 10}}\n'
            "  ]\n"
            "}\n```\n\n"
            "**Option B – CSV Upload:**\n"
            "```\nPOST /api/v1/exams/{exam_id}/upload-marks\n"
            "(multipart/form-data, field: file)\n```\n\n"
            "After marks are entered:\n"
            "→ Calculate CO attainment: "
            "**POST /api/v1/attainment/calculate-co?course_id=…&exam_id=…**"
        ),
        "data": None,
    }


# ── Func 5 – CO Attainment ────────────────────────────────────────────────────

async def calculate_attainment_node(state: OBEGraphState) -> dict:
    """Retrieve the attainment summary for the course."""
    course_id = state.get("course_id")
    session   = state["db_session"]

    if not course_id:
        return {
            "reply": (
                "Provide a `course_id` to calculate CO attainment.\n\n"
                "**Steps:**\n"
                "1. `POST /api/v1/attainment/calculate-co?course_id=…&exam_id=…`\n"
                "2. `GET  /api/v1/attainment/course/{course_id}`"
            ),
            "data": None,
        }

    entities = state.get("entities", [])
    exam_id = _extract_exam_id(state["message"], entities)
    try:
        from app.modules.attainment_engine.services.attainment_service import AttainmentService
        svc = AttainmentService(session)
        if exam_id:
            await svc.calculate_course_outcome_attainments(course_id, exam_id, threshold_pct=0.60)
        summary = await svc.get_course_attainment_summary(course_id)
        avg_co  = summary.get("average_co_attainment", 0)
        avg_po  = summary.get("average_po_attainment", 0)
        return {
            "reply": (
                f"**Attainment Summary – course `{course_id}`**\n\n"
                f"- Average CO Attainment: **{avg_co:.1f}%**\n"
                f"- Average PO Attainment: **{avg_po:.1f}%**\n"
                f"- Overall Level: **{summary.get('overall_level', '–')}**\n\n"
                "Visualise: **GET /api/v1/visualization/{course_id}**\n"
                "Download:  **GET /api/v1/reports/{course_id}/download?format=pdf**"
            ),
            "data": summary,
        }
    except Exception as exc:
        logger.error(f"calculate_attainment_node: {exc}")
        return {"reply": f"Error calculating attainment: {exc}", "data": None}


# ── Func 6 – PO / PSO Attainment ─────────────────────────────────────────────

async def calculate_po_attainment_node(state: OBEGraphState) -> dict:
    """Run real PO and PSO attainment calculations."""
    course_id = state.get("course_id")
    entities = state.get("entities", [])
    program_id = _extract_program_id(state["message"], entities)
    if not course_id or not program_id:
        return {
            "reply": (
                "Provide `course_id` and `program_id` to calculate PO/PSO attainment.\n"
                "Example: `calculate po attainment program_id=BTECH-CSE-2026`"
            ),
            "data": None,
        }
    try:
        from app.modules.attainment_engine.services.attainment_service import AttainmentService
        session = state["db_session"]
        svc = AttainmentService(session)
        po_rows = await svc.calculate_program_outcome_attainments(course_id, program_id)
        pso_rows = await svc.calculate_pso_attainments(course_id, program_id)
        return {
            "reply": (
                f"PO/PSO attainment calculated for course `{course_id}` and program `{program_id}`.\n"
                f"PO rows: **{len(po_rows)}**, PSO rows: **{len(pso_rows)}**"
            ),
            "data": {"course_id": course_id, "program_id": program_id, "po_attainments": po_rows, "pso_attainments": pso_rows},
        }
    except Exception as exc:
        logger.error(f"calculate_po_attainment_node: {exc}")
        return {"reply": f"PO/PSO attainment error: {exc}", "data": None}


# ── Detect Bloom Level ────────────────────────────────────────────────────────

async def detect_bloom_node(state: OBEGraphState) -> dict:
    message = state["message"]
    try:
        from app.ai_engine.llm.llm_client import LLMClient
        llm    = LLMClient()
        prompt = (
            "Classify the Bloom's Taxonomy cognitive level of the following question or text. "
            "Respond with ONLY one word: remember, understand, apply, analyze, evaluate, or create.\n\n"
            f"Input: {message}"
        )
        level = (await llm.generate_completion(prompt)).strip().lower()
        valid = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
        if level not in valid:
            level = "understand"
        descriptions = {
            "remember":  "Recall facts and basic concepts.",
            "understand": "Explain ideas or concepts.",
            "apply":     "Use information in new situations.",
            "analyze":   "Draw connections and break down information.",
            "evaluate":  "Justify a decision or course of action.",
            "create":    "Produce new or original work.",
        }
        return {
            "reply": (
                f"**Bloom's Level: {level.capitalize()}**\n\n"
                f"{descriptions[level]}\n\n"
                "Classify all questions in an exam: "
                "**POST /api/v1/exams/{exam_id}/detect-bloom**"
            ),
            "data": {"bloom_level": level},
        }
    except Exception as exc:
        logger.error(f"detect_bloom_node: {exc}")
        return {"reply": f"Error detecting Bloom level: {exc}", "data": None}


# ── Func 7 – Reports & Visualisation ─────────────────────────────────────────

async def generate_report_node(state: OBEGraphState) -> dict:
    """Generate real report data for the given course."""
    course_id = state.get("course_id")
    if not course_id:
        return {
            "reply": (
                "Provide a `course_id` to generate reports.\n\n"
                "**Available outputs:**\n"
                "- PDF Report:         `GET /api/v1/reports/{course_id}/download?format=pdf`\n"
                "- Excel Report:       `GET /api/v1/reports/{course_id}/download?format=excel`\n"
                "- CO-PO Matrix:       `GET /api/v1/visualization/{course_id}`\n"
                "- Attainment Charts:  `GET /api/v1/visualization/{course_id}/attainment`"
            ),
            "data": None,
        }
    try:
        from app.modules.attainment_engine.services.attainment_service import AttainmentService
        session = state["db_session"]
        svc = AttainmentService(session)
        summary = await svc.get_course_attainment_summary(course_id)
        matrix = await svc.get_co_po_matrix(course_id)
        viz = await svc.get_visualization_data(course_id)
        return {
            "reply": (
                f"Report data generated for course `{course_id}`.\n"
                f"CO rows: **{len(summary.get('co_attainments', []))}**, "
                f"PO rows: **{len(summary.get('po_attainments', []))}**, "
                f"Matrix COs: **{len(matrix.get('cos', []))}**, POs: **{len(matrix.get('pos', []))}**"
            ),
            "data": {"summary": summary, "co_po_matrix": matrix, "visualization": viz},
        }
    except Exception as exc:
        logger.error(f"generate_report_node: {exc}")
        return {"reply": f"Report generation error: {exc}", "data": None}


# ── List Courses ──────────────────────────────────────────────────────────────

async def list_courses_node(state: OBEGraphState) -> dict:
    session = state["db_session"]
    try:
        from app.modules.courses.services.course_service import CourseService
        svc     = CourseService(session)
        courses = await svc.list_courses()
        if not courses:
            return {
                "reply": "No courses registered yet. Create one via **POST /api/v1/courses**.",
                "data": {"count": 0},
            }
        course_list = "\n".join(
            f"- `{c.course_code}` – {c.course_name}  _(id: `{c.id}`)_"
            for c in courses
        )
        return {
            "reply": f"**Registered Courses ({len(courses)}):**\n\n{course_list}",
            "data": {"count": len(courses)},
        }
    except Exception as exc:
        logger.error(f"list_courses_node: {exc}")
        return {"reply": f"Error listing courses: {exc}", "data": None}


# ── Help / Greet ──────────────────────────────────────────────────────────────

async def help_node(state: OBEGraphState) -> dict:
    return {"reply": _HELP_TEXT, "data": None}


# ── Goodbye ───────────────────────────────────────────────────────────────────

async def goodbye_node(state: OBEGraphState) -> dict:
    return {
        "reply": "Thank you for using the OBE Chatbot Assistant! Goodbye.",
        "data": None,
    }


# ── Fallback: General LLM ─────────────────────────────────────────────────────

async def general_llm_node(state: OBEGraphState) -> dict:
    message   = state["message"]
    course_id = state.get("course_id")
    try:
        from app.ai_engine.llm.llm_client import LLMClient
        llm     = LLMClient()
        context = (
            "You are an OBE (Outcome Based Education) assistant for faculty. "
            + (f"Current course: {course_id}. " if course_id else "")
            + "Help with CO generation, CO-PO mapping, attainment calculation, "
            "Bloom's taxonomy, and report generation.\n\n"
            f"Faculty: {message}"
        )
        reply = await llm.generate_completion(context)
        return {
            "reply": reply or "Type **help** to see all available OBE features.",
            "data": None,
        }
    except Exception as exc:
        logger.error(f"general_llm_node: {exc}")
        return {
            "reply": "I'm your OBE assistant. Type **help** for a full list of features.",
            "data": None,
        }


# ════════════════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ════════════════════════════════════════════════════════════════════════════════

_NODE_MAP: Dict[str, Any] = {
    "nlu_node":                     nlu_node,
    "generate_co_node":             generate_co_node,
    "configure_exam_node":          configure_exam_node,
    "map_co_po_node":               map_co_po_node,
    "map_co_pso_node":              map_co_pso_node,
    "map_question_co_node":         map_question_co_node,
    "add_questions_node":           add_questions_node,
    "student_marks_node":           student_marks_node,
    "calculate_attainment_node":    calculate_attainment_node,
    "calculate_po_attainment_node": calculate_po_attainment_node,
    "detect_bloom_node":            detect_bloom_node,
    "generate_report_node":         generate_report_node,
    "list_courses_node":            list_courses_node,
    "help_node":                    help_node,
    "goodbye_node":                 goodbye_node,
    "general_llm_node":             general_llm_node,
}

_WORKER_NODES = [k for k in _NODE_MAP if k != "nlu_node"]


def _build_obe_graph():
    """Construct and compile the OBE LangGraph StateGraph (called once)."""
    graph = StateGraph(OBEGraphState)

    # Register every node
    for name, fn in _NODE_MAP.items():
        graph.add_node(name, fn)

    # Entry point is always NLU
    graph.set_entry_point("nlu_node")

    # After NLU: conditional routing to the appropriate worker
    routing_map = {node: node for node in _WORKER_NODES}
    graph.add_conditional_edges("nlu_node", intent_router, routing_map)

    # Every worker node terminates the graph
    for node in _WORKER_NODES:
        graph.add_edge(node, END)

    return graph.compile()


def _build_specialized_graph(
    allowed_worker_nodes: List[str],
    *,
    fallback_node: str = "help_node",
):
    """Build a constrained graph for a specific OBE sub-workflow."""
    graph = StateGraph(OBEGraphState)

    # Always include NLU and the shared fallback nodes.
    baseline_nodes = ["nlu_node", "help_node", "general_llm_node", "goodbye_node"]
    for node_name in baseline_nodes + allowed_worker_nodes:
        graph.add_node(node_name, _NODE_MAP[node_name])

    graph.set_entry_point("nlu_node")

    routing_map = {node: node for node in allowed_worker_nodes}
    routing_map.update({
        "help_node": "help_node",
        "general_llm_node": "general_llm_node",
        "goodbye_node": "goodbye_node",
    })

    def _router(state: OBEGraphState) -> str:
        routed = intent_router(state)
        if routed in routing_map:
            return routed
        return fallback_node

    graph.add_conditional_edges("nlu_node", _router, routing_map)

    for node in routing_map.values():
        graph.add_edge(node, END)

    return graph.compile()


# Lazy singleton ---------------------------------------------------------------
_obe_graph = None
_graph_registry: Optional[Dict[str, Any]] = None


def get_obe_graph():
    """Return the compiled OBE LangGraph workflow (lazy singleton)."""
    global _obe_graph
    if _obe_graph is None:
        _obe_graph = _build_obe_graph()
    return _obe_graph


def get_graph_registry() -> Dict[str, Any]:
    """
    Return five distinct compiled LangGraph workflows used by the OBE assistant.
    """
    global _graph_registry
    if _graph_registry is None:
        _graph_registry = {
            # 1) Full conversational orchestration graph
            "obe_assistant": get_obe_graph(),
            # 2) CO creation and syllabus workflow graph
            "co_design": _build_specialized_graph([
                "generate_co_node",
                "map_co_po_node",
                "map_co_pso_node",
                "detect_bloom_node",
            ]),
            # 3) Exam/question/marks workflow graph
            "assessment_flow": _build_specialized_graph([
                "configure_exam_node",
                "add_questions_node",
                "map_question_co_node",
                "student_marks_node",
            ]),
            # 4) Attainment computation workflow graph
            "attainment_flow": _build_specialized_graph([
                "calculate_attainment_node",
                "calculate_po_attainment_node",
                "map_co_po_node",
                "map_co_pso_node",
            ]),
            # 5) Reporting and analytics workflow graph
            "reporting_flow": _build_specialized_graph([
                "generate_report_node",
                "list_courses_node",
                "calculate_attainment_node",
            ]),
        }
    return _graph_registry


def get_graph_inventory() -> Dict[str, Any]:
    """Return lightweight metadata proving the available distinct graph set."""
    registry = get_graph_registry()
    return {
        "count": len(registry),
        "graphs": [
            {"name": name, "type": "StateGraph"}
            for name in registry.keys()
        ],
    }


# ════════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════════

async def run_obe_workflow(
    message:    str,
    course_id:  Optional[str],
    session_id: str,
    db_session: Any,
    user_id:    Optional[str] = None,
    force_node: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the full Rasa NLU + LangGraph OBE workflow for one user message.

    Returns::

        {
            "reply":          str,
            "intent":         str,
            "nlu_confidence": float,
            "nlu_source":     str,    # "rasa" | "keyword"
            "data":           dict | None,
            "session_id":     str,
        }
    """
    graph = get_obe_graph()

    initial_state: OBEGraphState = {
        "message":         message,
        "course_id":       course_id,
        "session_id":      session_id,
        "user_id":         user_id,
        "db_session":      db_session,
        "intent":          "general",
        "force_node":      force_node,
        "nlu_confidence":  0.0,
        "nlu_source":      "keyword",
        "entities":        [],
        "reply":           "",
        "data":            None,
        "error":           None,
    }

    try:
        final_state = await graph.ainvoke(initial_state)
        return {
            "reply":          final_state.get("reply", ""),
            "intent":         final_state.get("intent", "general"),
            "nlu_confidence": final_state.get("nlu_confidence", 0.0),
            "nlu_source":     final_state.get("nlu_source", "keyword"),
            "data":           final_state.get("data"),
            "session_id":     session_id,
        }
    except Exception as exc:
        logger.error(f"LangGraph workflow error: {exc}")
        return {
            "reply":          f"Workflow error: {exc}. Please try again or type 'help'.",
            "intent":         "error",
            "nlu_confidence": 0.0,
            "nlu_source":     "error",
            "data":           None,
            "session_id":     session_id,
        }
