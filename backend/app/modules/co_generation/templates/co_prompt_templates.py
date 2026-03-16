"""
CO Generation Prompt Templates
Domain-aware templates for generating high-quality, NBA-compliant Course Outcomes.
"""
from __future__ import annotations
from typing import Dict, List, Optional

# ── Domain detection keyword map ─────────────────────────────────────────────

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "cs": [
        "algorithm", "data structure", "programming", "software", "database",
        "operating system", "network", "compiler", "machine learning", "artificial intelligence",
        "web", "cloud", "cybersecurity", "python", "java", "c++", "object oriented",
        "computer architecture", "distributed", "parallel", "big data",
    ],
    "ece": [
        "circuit", "signal", "microprocessor", "embedded", "vlsi", "analog",
        "digital", "communication", "antenna", "electromagnetic", "control system",
        "power electronics", "sensor", "transducer", "microcontroller", "fpga",
        "wireless", "optical fiber", "modulation", "filter",
    ],
    "mechanical": [
        "thermodynamics", "fluid mechanics", "heat transfer", "manufacturing",
        "machine design", "kinematics", "dynamics", "material science", "cad",
        "cam", "finite element", "robotics", "automobile", "turbine", "stress",
        "strain", "vibration", "casting", "welding", "cnc",
    ],
    "civil": [
        "structural", "concrete", "steel", "soil mechanics", "foundation",
        "surveying", "hydraulics", "transportation", "geotechnical", "construction",
        "rcc", "prestressed", "bridge", "dam", "irrigation", "environmental",
        "water supply", "sanitation", "highway", "pavement",
    ],
    "electrical": [
        "power system", "transformer", "motor", "generator", "transmission",
        "distribution", "protection", "relay", "switchgear", "drives",
        "renewable energy", "solar", "wind", "smart grid", "plc", "scada",
    ],
    "mathematics": [
        "calculus", "differential equation", "linear algebra", "probability",
        "statistics", "numerical method", "discrete mathematics", "graph theory",
        "complex analysis", "fourier", "laplace", "optimization",
    ],
    "management": [
        "management", "marketing", "finance", "accounting", "economics",
        "entrepreneurship", "project management", "supply chain", "hr",
        "organizational behavior", "strategy", "operations",
    ],
    "chemistry": [
        "organic chemistry", "inorganic chemistry", "physical chemistry",
        "polymer", "spectroscopy", "electrochemistry", "thermochemistry",
        "reaction", "catalyst", "synthesis", "analytical chemistry",
    ],
    "physics": [
        "mechanics", "optics", "quantum", "nuclear", "solid state",
        "electromagnetism", "relativity", "wave",
    ],
}

# ── Bloom's action verbs per level ───────────────────────────────────────────

BLOOM_VERBS: Dict[str, List[str]] = {
    "remember":   ["recall", "list", "define", "state", "identify", "name", "recognize", "describe"],
    "understand": ["explain", "summarize", "interpret", "classify", "compare", "discuss", "illustrate", "paraphrase"],
    "apply":      ["apply", "solve", "use", "implement", "demonstrate", "calculate", "execute", "construct"],
    "analyze":    ["analyze", "differentiate", "examine", "distinguish", "investigate", "break down", "compare", "contrast"],
    "evaluate":   ["evaluate", "judge", "critique", "justify", "recommend", "assess", "select", "defend"],
    "create":     ["design", "develop", "formulate", "construct", "plan", "produce", "generate", "synthesize"],
}

# ── Bloom's progression for N COs ────────────────────────────────────────────

BLOOM_PROGRESSION: Dict[int, List[str]] = {
    3: ["remember", "apply", "analyze"],
    4: ["remember", "understand", "apply", "analyze"],
    5: ["remember", "understand", "apply", "analyze", "evaluate"],
    6: ["remember", "understand", "apply", "analyze", "evaluate", "create"],
}


def get_bloom_progression(num_cos: int, unit_guidance: Optional[List[Dict]] = None) -> List[str]:
    """
    Build a Bloom's level sequence for num_cos COs.

    When unit_guidance is provided (from _analyze_units_for_prompt), the sequence
    is derived directly from the unit BT levels so the LLM gets topic-driven
    assignments rather than a fixed positional ladder.

    Fallback to the static BLOOM_PROGRESSION table when no unit guidance exists.
    """
    if unit_guidance:
        level_to_bloom = {
            "L1": "remember", "L2": "understand", "L3": "apply",
            "L4": "analyze",  "L5": "evaluate",  "L6": "create",
        }
        # Collect unit-derived bloom levels in order
        unit_levels = [
            level_to_bloom.get(str(u.get("bt_level", "L3")), "apply")
            for u in unit_guidance
        ]
        # Pad or trim to exactly num_cos entries.
        # When more COs than units: escalate toward higher levels.
        escalation = ["analyze", "evaluate", "create", "evaluate", "analyze"]
        while len(unit_levels) < num_cos:
            unit_levels.append(escalation[(len(unit_levels) - len(unit_guidance)) % len(escalation)])
        sequence = unit_levels[:num_cos]

        # Enforce minimum spread: at least 3 distinct levels for 4+ COs.
        # If the unit analysis produced a narrow band, inject L4 and L6 at the end.
        if num_cos >= 4:
            distinct = set(sequence)
            if len(distinct) < 3:
                if "analyze" not in distinct:
                    sequence[-2] = "analyze"
                if "create" not in distinct and num_cos >= 5:
                    sequence[-1] = "create"
        return sequence

    # Static fallback
    if num_cos <= 3:
        return BLOOM_PROGRESSION[3][:num_cos]
    if num_cos in BLOOM_PROGRESSION:
        return BLOOM_PROGRESSION[num_cos]
    base = BLOOM_PROGRESSION[6]
    extra = ["analyze", "evaluate", "create"]
    return (base + extra * 10)[:num_cos]


# ── Domain-specific fallback COs ─────────────────────────────────────────────

DOMAIN_CO_EXAMPLES: Dict[str, List[Dict]] = {
    "cs": [
        {"bloom_level": "remember",   "statement": "Students will be able to recall and define fundamental data structures including arrays, linked lists, stacks, queues, trees, and graphs."},
        {"bloom_level": "understand", "statement": "Students will be able to explain the working principles of sorting and searching algorithms with their time and space complexity."},
        {"bloom_level": "apply",      "statement": "Students will be able to implement efficient algorithms to solve computational problems using appropriate data structures."},
        {"bloom_level": "analyze",    "statement": "Students will be able to analyze algorithm complexity using Big-O notation and compare trade-offs between different approaches."},
        {"bloom_level": "evaluate",   "statement": "Students will be able to evaluate software design patterns and select appropriate architectural solutions for given problem domains."},
        {"bloom_level": "create",     "statement": "Students will be able to design and develop a complete software system applying OOP principles, design patterns, and software engineering best practices."},
    ],
    "ece": [
        {"bloom_level": "remember",   "statement": "Students will be able to recall fundamental laws of circuit theory including Ohm's law, Kirchhoff's laws, and network theorems."},
        {"bloom_level": "understand", "statement": "Students will be able to explain the operation of analog and digital electronic devices including diodes, transistors, and logic gates."},
        {"bloom_level": "apply",      "statement": "Students will be able to apply signal processing techniques to analyze and process continuous and discrete-time signals."},
        {"bloom_level": "analyze",    "statement": "Students will be able to analyze communication systems and evaluate modulation techniques for efficient signal transmission."},
        {"bloom_level": "evaluate",   "statement": "Students will be able to evaluate embedded system architectures and select appropriate microcontrollers for real-time applications."},
        {"bloom_level": "create",     "statement": "Students will be able to design and implement a complete electronic system integrating sensors, signal conditioning, and microcontroller-based processing."},
    ],
    "mechanical": [
        {"bloom_level": "remember",   "statement": "Students will be able to recall fundamental principles of thermodynamics, laws of motion, and properties of engineering materials."},
        {"bloom_level": "understand", "statement": "Students will be able to explain heat transfer mechanisms, fluid flow behavior, and stress-strain relationships in mechanical systems."},
        {"bloom_level": "apply",      "statement": "Students will be able to apply engineering mechanics principles to solve problems involving forces, moments, and equilibrium of structures."},
        {"bloom_level": "analyze",    "statement": "Students will be able to analyze machine components for stress, fatigue, and failure modes using appropriate design standards."},
        {"bloom_level": "evaluate",   "statement": "Students will be able to evaluate manufacturing processes and select optimal methods considering cost, quality, and sustainability."},
        {"bloom_level": "create",     "statement": "Students will be able to design a mechanical system or component meeting specified performance, safety, and manufacturing constraints."},
    ],
    "civil": [
        {"bloom_level": "remember",   "statement": "Students will be able to recall properties of construction materials, soil classification systems, and structural analysis fundamentals."},
        {"bloom_level": "understand", "statement": "Students will be able to explain behavior of structural elements under various loading conditions and principles of geotechnical engineering."},
        {"bloom_level": "apply",      "statement": "Students will be able to apply structural analysis methods to calculate forces, moments, and deflections in beams, frames, and trusses."},
        {"bloom_level": "analyze",    "statement": "Students will be able to analyze soil properties and foundation requirements for safe and economical structural design."},
        {"bloom_level": "evaluate",   "statement": "Students will be able to evaluate construction methods, materials, and environmental impact for sustainable infrastructure development."},
        {"bloom_level": "create",     "statement": "Students will be able to design reinforced concrete or steel structures complying with relevant IS/BIS codes and safety standards."},
    ],
    "electrical": [
        {"bloom_level": "remember",   "statement": "Students will be able to recall fundamental concepts of electrical circuits, power systems, and electromagnetic theory."},
        {"bloom_level": "understand", "statement": "Students will be able to explain the operating principles of transformers, motors, generators, and power electronic devices."},
        {"bloom_level": "apply",      "statement": "Students will be able to apply power system analysis techniques to solve load flow, fault analysis, and stability problems."},
        {"bloom_level": "analyze",    "statement": "Students will be able to analyze protection schemes and relay coordination for reliable power system operation."},
        {"bloom_level": "evaluate",   "statement": "Students will be able to evaluate renewable energy integration strategies and their impact on grid stability and power quality."},
        {"bloom_level": "create",     "statement": "Students will be able to design an electrical distribution system incorporating protection, metering, and energy management features."},
    ],
    "mathematics": [
        {"bloom_level": "remember",   "statement": "Students will be able to recall fundamental mathematical definitions, theorems, and standard formulas relevant to the course."},
        {"bloom_level": "understand", "statement": "Students will be able to explain mathematical concepts and interpret their geometric or physical significance."},
        {"bloom_level": "apply",      "statement": "Students will be able to apply mathematical techniques to solve engineering and science problems involving differential equations or transforms."},
        {"bloom_level": "analyze",    "statement": "Students will be able to analyze mathematical models and determine convergence, stability, or optimality of solutions."},
        {"bloom_level": "evaluate",   "statement": "Students will be able to evaluate numerical methods for accuracy, stability, and computational efficiency."},
        {"bloom_level": "create",     "statement": "Students will be able to formulate mathematical models for real-world problems and develop solution strategies using appropriate techniques."},
    ],
    "general": [
        {"bloom_level": "remember",   "statement": "Students will be able to recall and describe fundamental concepts, principles, and terminology of the subject domain."},
        {"bloom_level": "understand", "statement": "Students will be able to explain key theories, models, and their practical significance in real-world contexts."},
        {"bloom_level": "apply",      "statement": "Students will be able to apply domain knowledge and learned techniques to solve standard problems in the field."},
        {"bloom_level": "analyze",    "statement": "Students will be able to analyze complex scenarios, identify patterns, and determine root causes using systematic approaches."},
        {"bloom_level": "evaluate",   "statement": "Students will be able to evaluate alternative solutions, methodologies, and approaches to select the most appropriate option."},
        {"bloom_level": "create",     "statement": "Students will be able to design and develop innovative solutions to domain-specific problems integrating multiple concepts."},
    ],
}

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an expert OBE (Outcome-Based Education) curriculum designer with 15+ years of experience "
    "in NBA/NAAC accreditation. Your task is to generate Course Outcomes (COs) that are SPECIFIC, "
    "MEASURABLE, ACHIEVABLE, RELEVANT, and BLOOM'S ALIGNED.\n\n"
    "CRITICAL RULES:\n"
    "- Each CO MUST start with 'Students will be able to' followed by a Bloom's action verb\n"
    "- Each CO must be UNIQUE — no overlap in content or skills\n"
    "- BT levels are assigned dynamically from syllabus unit complexity — do NOT assume a fixed L1→L6 ladder\n"
    "- Do NOT use vague verbs like 'understand', 'know', 'learn', 'appreciate'\n"
    "- Return ONLY valid JSON array, no markdown, no explanation text"
)


# ── Main generation prompt ────────────────────────────────────────────────────

def build_generation_prompt(
    course_name: str,
    syllabus: str,
    num_cos: int,
    domain: str,
    bloom_sequence: List[str],
    po_context: str = "",
    pso_context: str = "",
    has_mappings: bool = False,
    unit_guidance: Optional[List[Dict]] = None,
    advanced_mode: bool = True,
    course_code: str = "",
    department: str = "",
    semester: Optional[int] = None,
    credits: Optional[int] = None,
    enrolled_students: Optional[int] = None,
) -> str:
    # Build unit guidance lines — include hours and priority flag so the LLM
    # knows which units carry the most teaching weight.
    unit_guidance = unit_guidance or []
    unit_lines_parts: List[str] = []
    for u in unit_guidance[:12]:
        hours_tag = f", hours={u['hours']}" if u.get("hours") is not None else ""
        priority_tag = " [HIGH-PRIORITY — must be covered by at least one CO]" if u.get("is_priority") else ""
        verbs = ", ".join(BLOOM_VERBS.get(u.get("bloom_level", "apply"), [])[:4])
        unit_lines_parts.append(
            f"  - {u.get('unit', 'UNIT')}{hours_tag}: "
            f"bt_level={u.get('bt_level', 'L3')} ({u.get('bloom_level', 'apply')}), "
            f"suggested verb={u.get('suggested_action_verb', 'apply')}, "
            f"verbs=[{verbs}]{priority_tag}"
        )
    unit_lines = "\n".join(unit_lines_parts) if unit_lines_parts else (
        "  - Derive unit complexity dynamically from syllabus topic vocabulary and assign suitable Bloom levels."
    )

    # Bloom instructions are derived from unit guidance (dynamic), not a fixed
    # positional sequence. Each CO slot maps to the unit whose BT level it should
    # reflect. When there are more COs than units, later COs escalate toward L6.
    bloom_instructions_parts: List[str] = []
    for i, level in enumerate(bloom_sequence):
        verbs = ", ".join(BLOOM_VERBS.get(level, [])[:4])
        # Annotate which unit this CO should draw from if unit guidance is available
        unit_hint = ""
        if i < len(unit_guidance):
            unit_hint = f" — draw content from: {unit_guidance[i].get('unit', '')}"
        bloom_instructions_parts.append(
            f"  CO{i+1}: Bloom's Level = {level.upper()} | verbs: {verbs}{unit_hint}"
        )
    bloom_instructions = "\n".join(bloom_instructions_parts)

    # NOTE: po_mapping/pso_mapping intentionally excluded from generation schema.
    # CO-PO mapping is handled separately in the mapping interface.

    return (
        f"Generate exactly {num_cos} Course Outcomes for the following course.\n\n"
        f"COURSE: {course_name}{(' (' + course_code + ')') if course_code else ''}\n"
        f"DOMAIN: {domain.upper()}\n"
        + (f"DEPARTMENT: {department}\n" if department else "")
        + (f"SEMESTER: {semester}\n" if semester else "")
        + (f"CREDITS: {credits}\n" if credits else "")
        + (f"ENROLLED STUDENTS: {enrolled_students}\n" if enrolled_students else "")
        + "\n"
        f"SYLLABUS:\n{syllabus[:3000]}\n"
        f"{po_context}{pso_context}\n"
        f"UNIT COMPLEXITY ANALYSIS (use this to assign BT levels — fully dynamic from topic vocabulary):\n"
        f"{unit_lines}\n\n"
        f"BT LEVEL ASSIGNMENT RULES:\n"
        f"  Topics with: define/list/recall/state/name → L1 Remember\n"
        f"  Topics with: explain/describe/summarize/classify/interpret → L2 Understand\n"
        f"  Topics with: implement/solve/use/execute/compute/apply → L3 Apply\n"
        f"  Topics with: analyze/compare/differentiate/examine/contrast → L4 Analyze\n"
        f"  Topics with: evaluate/justify/assess/recommend/select → L5 Evaluate\n"
        f"  Topics with: design/develop/construct/formulate/create/synthesize → L6 Create\n\n"
        f"REQUIRED CO BLOOM LEVELS (derived from unit analysis above):\n"
        f"{bloom_instructions}\n\n"
        f"BT DISTRIBUTION CHECK: The {num_cos} COs must span at least 3 different BT levels. "
        f"If all COs cluster at one level, redistribute — add at least one Analyze (L4) and one Create (L6) CO.\n\n"
        f"Return ONLY this JSON array (no wrapper object, no markdown), no other text:\n"
        f"[\n"
        f"  {{\n"
        f'    "code": "CO1",\n'
        f'    "bt_level": "L3",\n'
        f'    "verb": "implement",\n'
        f'    "statement": "Students will be able to implement [specific content from THIS syllabus].",\n'
        f'    "bloom_level": "{bloom_sequence[0] if bloom_sequence else "apply"}",\n'
        f'    "units_covered": ["UNIT 1"],\n'
        f'    "description": "Brief assessment method"\n'
        f"  }}\n"
        f"]\n\n"
        f"BEFORE RESPONDING CHECK:\n"
        f"- Each statement starts with exactly 'Students will be able to'\n"
        f"- Each uses a Bloom's action verb matching the specified level — NO vague verbs (understand/know/learn)\n"
        f"- Include bt_level, verb, and units_covered for every CO\n"
        f"- Each CO is specific to THIS course syllabus content — not generic\n"
        f"- No two COs overlap in skill or content\n"
        f"- High-priority units (marked above) must be covered by at least one CO\n"
        f"- COs span at least 3 distinct BT levels"
    )


# ── Single CO regeneration prompt ────────────────────────────────────────────

def build_regeneration_prompt(
    course_name: str,
    syllabus_snippet: str,
    co_code: str,
    current_statement: str,
    current_bloom: str,
    other_cos: List[Dict],
    domain: str,
    reason: Optional[str] = None,
) -> str:
    other_ctx = "\n".join(
        f"  {c['code']} ({c['bloom_level'].upper()}): {c['statement']}"
        for c in other_cos
    )
    reason_line = f"\nREASON FOR REGENERATION: {reason}" if reason else ""
    verbs = ", ".join(BLOOM_VERBS.get(current_bloom, BLOOM_VERBS["understand"])[:5])

    return (
        f"Regenerate ONLY the following Course Outcome. Keep the same Bloom's level.\n\n"
        f"COURSE: {course_name}\n"
        f"DOMAIN: {domain.upper()}\n"
        f"SYLLABUS CONTEXT: {syllabus_snippet[:1500]}\n"
        f"{reason_line}\n\n"
        f"CO TO REGENERATE:\n"
        f"  Code: {co_code}\n"
        f"  Current: {current_statement}\n"
        f"  Bloom's level: {current_bloom.upper()} (use verbs like: {verbs})\n\n"
        f"EXISTING COs (new one must be DISTINCT from all of these):\n{other_ctx}\n\n"
        f"Return ONLY this JSON object:\n"
        f'{{"statement": "Students will be able to [verb] [specific content].", '
        f'"bloom_level": "{current_bloom}", '
        f'"description": "Brief assessment method"}}'
    )


# ── CO-PO mapping with justification prompt ───────────────────────────────────

def build_co_po_mapping_prompt(
    co_code: str,
    co_statement: str,
    co_bloom: str,
    pos: List[Dict],
    psos: Optional[List[Dict]] = None,
) -> str:
    """
    Build a focused prompt to map ONE CO to all POs/PSOs with justification.
    One CO at a time keeps the prompt small and avoids LLM timeout.
    """
    po_lines = "\n".join(f"  {p['code']}: {p.get('statement') or p.get('name') or p['code']}" for p in pos)
    pso_block = ""
    if psos:
        pso_block = "\nProgram Specific Outcomes:\n" + "\n".join(
            f"  {p['code']}: {p.get('statement') or p.get('name') or p['code']}" for p in psos
        )

    po_codes_str = ", ".join(f'"{p["code"]}": 0' for p in pos)
    pso_codes_str = ", ".join(f'"{p["code"]}": 0' for p in (psos or []))
    just_str = ", ".join(f'"{p["code"]}": "reason"' for p in pos[:3])
    pso_mapping_section = f', "pso_mapping": {{{pso_codes_str}}}' if pso_codes_str else ""

    return (
        f"NBA OBE expert task: map one Course Outcome to Program Outcomes.\n\n"
        f"CO: {co_code} | Bloom: {co_bloom.upper()}\n"
        f"Statement: {co_statement}\n\n"
        f"Program Outcomes:\n{po_lines}{pso_block}\n\n"
        f"Levels: 3=Strong, 2=Medium, 1=Weak, 0=None\n\n"
        f"Return ONLY this JSON (all PO codes required, 0 for no correlation):\n"
        f'{{"po_mapping": {{{po_codes_str}}}'
        f'{pso_mapping_section}'
        f', "justification": {{{just_str}}}}}\n'
        f"justification: include only for level >= 1, one sentence each. No text outside JSON."
    )
