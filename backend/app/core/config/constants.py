"""
Application constants and enumerations
"""
from enum import Enum


class BloomTaxonomyLevel(str, Enum):
    """Bloom's Taxonomy levels for learning outcomes"""
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class AttainmentLevel(str, Enum):
    """Academic attainment levels"""
    LEVEL_3 = "Level 3"
    LEVEL_2 = "Level 2"
    LEVEL_1 = "Level 1"
    NOT_ATTAINED = "Not Attained"


class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"
    FACULTY = "faculty"
    HOD = "hod"
    COURSE_LEAD = "course_lead"
    ACCREDITATION_OFFICER = "accreditation_officer"
    VIEWER = "viewer"


class OutcomeType(str, Enum):
    """Types of learning outcomes"""
    COURSE_OUTCOME = "CO"
    PROGRAM_OUTCOME = "PO"
    PROGRAM_SPECIFIC_OUTCOME = "PSO"


class ExamType(str, Enum):
    """Types of exams"""
    MID_TERM = "mid_term"
    END_TERM = "end_term"
    PRACTICAL = "practical"
    ASSIGNMENT = "assignment"


class QuestionType(str, Enum):
    """Types of exam questions"""
    MULTIPLE_CHOICE = "mcq"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    PRACTICAL = "practical"
    ESSAY = "essay"


# Bloom's Taxonomy Keywords by Level
BLOOM_KEYWORDS = {
    BloomTaxonomyLevel.REMEMBER: [
        "recall", "list", "name", "define", "state", "identify",
        "memorize", "recognize", "describe", "reproduce"
    ],
    BloomTaxonomyLevel.UNDERSTAND: [
        "summarize", "explain", "interpret", "classify", "compare",
        "contrast", "discuss", "paraphrase", "restate", "translate"
    ],
    BloomTaxonomyLevel.APPLY: [
        "apply", "use", "implement", "solve", "calculate", "demonstrate",
        "execute", "illustrate", "practice", "sketch"
    ],
    BloomTaxonomyLevel.ANALYZE: [
        "analyze", "distinguish", "differentiate", "discriminate", "examine",
        "experiment", "question", "test", "compare", "contrast"
    ],
    BloomTaxonomyLevel.EVALUATE: [
        "evaluate", "judge", "appraise", "critique", "argue", "defend",
        "decide", "select", "choose", "support", "rate", "recommend"
    ],
    BloomTaxonomyLevel.CREATE: [
        "create", "design", "construct", "plan", "produce", "compose",
        "generate", "develop", "synthesize", "formulate", "invent"
    ],
}

# Default CO Generation Parameters
CO_GENERATION_PARAMS = {
    "co_count_min": 4,
    "co_count_max": 6,
    "temperature": 0.3,
    "max_tokens": 1500,
}

# Semantic Similarity Thresholds
SEMANTIC_SIMILARITY_THRESHOLD_HIGH = 0.8
SEMANTIC_SIMILARITY_THRESHOLD_MEDIUM = 0.6
SEMANTIC_SIMILARITY_THRESHOLD_LOW = 0.4

# Academic Formulas Constants
ATTAINMENT_CALCULATION_METHOD = "weighted_average"
PO_CALCULATION_METHOD = "simple_average"
PSO_CALCULATION_METHOD = "simple_average"

# Cache TTL in seconds
CACHE_TTL_SHORT = 300  # 5 minutes
CACHE_TTL_MEDIUM = 1800  # 30 minutes
CACHE_TTL_LONG = 86400  # 1 day
