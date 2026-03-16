from pathlib import Path
import copy
import sys
import types
from types import SimpleNamespace

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.services.three_message_flow_service as flow_module
from app.services.three_message_flow_service import ThreeMessageFlowService, validate_matrix


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.flushes = 0
        self.added = []

    async def commit(self):
        self.commits += 1

    async def flush(self):
        self.flushes += 1

    def add(self, obj):
        self.added.append(obj)


@pytest.fixture
def state_store(monkeypatch):
    store = {}

    async def fake_get_json(key):
        return copy.deepcopy(store.get(key))

    async def fake_set_json(key, payload, ttl_seconds=None):
        store[key] = copy.deepcopy(payload)

    monkeypatch.setattr(flow_module, "get_json", fake_get_json)
    monkeypatch.setattr(flow_module, "set_json", fake_set_json)
    return store


def make_service(session=None):
    return ThreeMessageFlowService(
        session=session or FakeSession(),
        user_id="faculty-1",
        user_role="faculty",
    )


def make_course():
    return SimpleNamespace(
        id="course-db-1",
        course_code="CS301",
        course_name="",
        semester=0,
        credits=0,
        department=None,
        enrolled_students=0,
        created_by="faculty-1",
        syllabus=None,
    )


def make_outcome_rows(prefix, count):
    return [
        SimpleNamespace(
            id=f"{prefix.lower()}-db-{index}",
            code=f"{prefix}{index}",
            statement=f"{prefix} {index} statement",
        )
        for index in range(1, count + 1)
    ]


def make_mapping_result(cos, pos_rows, pso_rows):
    mapping_matrix = {
        f"{co['id']}_{po.code}": 0
        for co in cos
        for po in pos_rows
    }
    flat_mapping = []

    for co_index, co in enumerate(cos):
        for offset in range(6):
            po = pos_rows[((co_index * 2) + offset) % len(pos_rows)]
            key = f"{co['id']}_{po.code}"
            mapping_matrix[key] = 2
            flat_mapping.append(
                {
                    "co_id": co["id"],
                    "po_id": po.code,
                    "correlation": 2,
                    "reason": "aligned topic coverage",
                }
            )

    pso_mapping_matrix = {
        f"{co['id']}_{pso.code}": 2
        for co in cos
        for pso in pso_rows
    }
    flat_pso_mapping = [
        {
            "co_id": co["id"],
            "pso_id": pso.code,
            "correlation": 2,
            "reason": "program specialization alignment",
        }
        for co in cos
        for pso in pso_rows
    ]

    return {
        "mapping_matrix": mapping_matrix,
        "pso_mapping_matrix": pso_mapping_matrix,
        "flat_mapping": flat_mapping,
        "flat_pso_mapping": flat_pso_mapping,
    }


@pytest.mark.asyncio
async def test_message_1_saves_course_fields_and_advances(state_store, monkeypatch):
    session = FakeSession()
    service = make_service(session)
    course = make_course()

    async def fake_resolve_course(validated, state, course_hint):
        return course

    monkeypatch.setattr(service, "_resolve_course", fake_resolve_course)

    result = await service.process_message(
        text=(
            "Course Name: Design and Analysis of Algorithms\n"
            "Course Code: CS301\n"
            "Department: CSE\n"
            "Semester: 5\n"
            "Credits: 4\n"
            "Students: 72\n"
            "Number of COs needed: 5"
        ),
        session_id="session-1",
        message_number=1,
    )

    assert result["status"] == "course_saved"
    assert result["course_id"] == "CS301"
    assert result["db_course_id"] == "course-db-1"
    assert result["next_action"] == "provide_syllabus"
    assert course.course_name == "Design and Analysis of Algorithms"
    assert course.course_code == "CS301"
    assert course.department == "CSE"
    assert course.semester == 5
    assert course.credits == 4
    assert course.enrolled_students == 72
    assert session.commits == 1

    saved_state = state_store[service._session_key("faculty-1", "session-1")]
    assert saved_state["stage"] == "awaiting_syllabus"
    assert saved_state["course_db_id"] == "course-db-1"
    assert saved_state["course_code"] == "CS301"
    assert saved_state["num_cos"] == 5


@pytest.mark.asyncio
async def test_message_2_generates_cos_from_syllabus(state_store, monkeypatch):
    session = FakeSession()
    service = make_service(session)
    course = make_course()
    state_store[service._session_key("faculty-1", "session-1")] = {
        "session_id": "session-1",
        "stage": "awaiting_syllabus",
        "course_db_id": course.id,
        "course_code": course.course_code,
        "num_cos": 5,
        "session_pos": [{"code": "PO1", "statement": "Engineering knowledge"}],
        "session_psos": [],
    }

    async def fake_get_course_from_state(state):
        return course

    monkeypatch.setattr(service, "_get_course_from_state", fake_get_course_from_state)
    async def fake_pos_for_context(*args, **kwargs):
        return []

    async def fake_psos_for_context(*args, **kwargs):
        return []

    monkeypatch.setattr(service, "_load_program_outcomes_for_context", fake_pos_for_context)
    monkeypatch.setattr(service, "_load_program_specific_outcomes_for_context", fake_psos_for_context)

    fake_module = types.ModuleType("app.modules.co_generation.services.co_generation_service")

    class FakeCoGenerationService:
        def __init__(self, current_session):
            self.current_session = current_session

        async def generate_cos_from_syllabus(self, course_id, syllabus, program_outcomes, program_specific_outcomes, num_cos):
            assert course_id == course.id
            assert num_cos == 5
            return {
                "course_outcomes": [
                    SimpleNamespace(
                        id=f"co-db-{index}",
                        code=f"CO{index}",
                        bloom_level="apply",
                        statement=f"Students will be able to apply unit {index} concepts effectively",
                    )
                    for index in range(1, 6)
                ]
            }

    fake_module.CoGenerationService = FakeCoGenerationService
    monkeypatch.setitem(sys.modules, "app.modules.co_generation.services.co_generation_service", fake_module)

    result = await service.process_message(
        text=(
            "Unit 1: Algorithmic foundations\n"
            "Asymptotic notation and recurrence solving\n"
            "Unit 2: Divide and conquer\n"
            "Sorting, searching, and correctness proofs\n"
            "Unit 3: Graph techniques\n"
            "Shortest path and spanning tree algorithms"
        ),
        session_id="session-1",
        message_number=2,
    )

    assert result["status"] == "cos_generated"
    assert result["course_id"] == "CS301"
    assert result["next_action"] == "confirm_or_modify_cos"
    assert len(result["cos"]) == 5
    assert result["cos"][0]["id"] == "CO1"
    assert result["cos"][0]["bt_level"] == "L3"
    assert session.commits == 1

    saved_state = state_store[service._session_key("faculty-1", "session-1")]
    assert saved_state["stage"] == "cos_generated"
    assert len(saved_state["cos"]) == 5
    assert len(saved_state["units"]) == 3


@pytest.mark.asyncio
async def test_message_3_generates_combined_po_pso_density_and_summary(state_store, monkeypatch):
    session = FakeSession()
    service = make_service(session)
    course = make_course()
    cos = [
        {
            "id": "CO1",
            "db_id": "co-db-1",
            "statement": "Explain asymptotic notation for algorithm growth analysis",
        },
        {
            "id": "CO2",
            "db_id": "co-db-2",
            "statement": "Construct recurrence relations for divide and conquer algorithms",
        },
        {
            "id": "CO3",
            "db_id": "co-db-3",
            "statement": "Implement graph traversal methods for connected networks",
        },
        {
            "id": "CO4",
            "db_id": "co-db-4",
            "statement": "Compare greedy strategies with dynamic programming design choices",
        },
        {
            "id": "CO5",
            "db_id": "co-db-5",
            "statement": "Evaluate algorithm correctness and complexity for optimization problems",
        },
    ]
    pos_rows = make_outcome_rows("PO", 12)
    pso_rows = make_outcome_rows("PSO", 2)
    mapping_result = make_mapping_result(cos, pos_rows, pso_rows)
    persisted = {}

    state_store[service._session_key("faculty-1", "session-1")] = {
        "session_id": "session-1",
        "stage": "awaiting_mapping_inputs",
        "course_db_id": course.id,
        "course_code": course.course_code,
        "num_cos": 5,
    }

    async def fake_get_course_from_state(state):
        return course

    async def fake_load_course_cos(course_id):
        assert course_id == course.id
        return cos

    async def fake_resolve_po_sources(text, current_course, incoming_pos, incoming_psos, state):
        return {"pos_rows": pos_rows, "pso_rows": pso_rows}

    async def fake_generate_mapping(current_cos, pos_payload, pso_payload):
        assert len(current_cos) == 5
        assert len(pos_payload) == 12
        assert len(pso_payload) == 2
        return mapping_result

    async def fake_persist_mapping(course_id, current_cos, current_pos_rows, current_pso_rows, current_mapping):
        persisted["course_id"] = course_id
        persisted["mapping"] = current_mapping

    monkeypatch.setattr(service, "_get_course_from_state", fake_get_course_from_state)
    monkeypatch.setattr(service, "_load_course_cos", fake_load_course_cos)
    monkeypatch.setattr(service, "_resolve_po_sources", fake_resolve_po_sources)
    monkeypatch.setattr(service, "_generate_mapping", fake_generate_mapping)
    monkeypatch.setattr(service, "_persist_mapping", fake_persist_mapping)
    async def fake_pos_for_context(*args, **kwargs):
        return pos_rows

    async def fake_psos_for_context(*args, **kwargs):
        return pso_rows

    monkeypatch.setattr(service, "_load_program_outcomes_for_context", fake_pos_for_context)
    monkeypatch.setattr(service, "_load_program_specific_outcomes_for_context", fake_psos_for_context)

    preview = await service.process_message(
        text="Use the current department POs and PSOs for final mapping.",
        session_id="session-1",
        message_number=3,
    )

    assert preview["status"] == "mapping_preview"
    assert preview["can_save"] is True
    assert preview["warnings"] == []
    assert preview["errors"] == []
    assert preview["matrix_density"] == pytest.approx(40 / 70, abs=1e-4)
    assert preview["mapping_summary"].startswith("40 of 70 cells mapped.")
    assert preview["next_action"] == "confirm_or_edit"

    result = await service.process_message(
        text="CONFIRM",
        session_id="session-1",
        message_number=3,
    )

    assert result["status"] == "mapping_generated"
    assert result["can_save"] is True
    assert result["warnings"] == []
    assert result["errors"] == []
    assert result["matrix_density"] == pytest.approx(40 / 70, abs=1e-4)
    assert result["mapping_summary"].startswith("40 of 70 cells mapped.")
    assert result["next_action"] == "exam_configuration"
    assert persisted["course_id"] == course.id
    assert persisted["mapping"] == mapping_result

    saved_state = state_store[service._session_key("faculty-1", "session-1")]
    assert saved_state["stage"] == "awaiting_exam_config"
    assert len(saved_state["session_pos"]) == 12
    assert len(saved_state["session_psos"]) == 2


def test_validate_matrix_blocks_invalid_values_and_unmapped_cos():
    result = validate_matrix(
        cos=[
            {"id": "CO1", "statement": "Explain algorithmic complexity"},
            {"id": "CO2", "statement": "Design graph solutions"},
        ],
        pos=[
            {"id": "PO1", "statement": "Engineering knowledge"},
            {"id": "PO2", "statement": "Problem analysis"},
        ],
        mapping_matrix={
            "CO1_PO1": 4,
            "CO1_PO2": 0,
            "CO2_PO1": 0,
            "CO2_PO2": 0,
        },
    )

    assert result["can_save"] is False
    assert "Invalid correlation 4 at CO1_PO1 - must be 0,1,2,3" in result["errors"]
    assert "CO2 maps to 0 POs - every CO needs >=1 mapping" in result["errors"]


@pytest.mark.asyncio
async def test_plain_english_exam_configuration_accumulates_to_preview(state_store):
    service = make_service(FakeSession())
    state_store[service._session_key("faculty-1", "session-exam")] = {
        "session_id": "session-exam",
        "stage": "awaiting_exam_config",
        "workflow_step": 3,
        "course_db_id": "course-db-1",
        "course_code": "CS301",
        "cos": [{"id": "CO1", "db_id": "co-db-1", "bt_level": "L2"}],
    }

    result_1 = await service.process_message(
        text="I conducted 5 tests and 1 end-semester exam. Tests: T1, T2, T3, T4, T5. End-Sem: 1 exam.",
        session_id="session-exam",
        message_number=3,
    )
    assert result_1["status"] == "exam_config_collecting"

    await service.process_message(
        text="Each test has 5 questions. Each question carries 10 marks. Total marks per test: 50. Exam duration: 1 hour per test.",
        session_id="session-exam",
        message_number=3,
    )
    await service.process_message(
        text="End-sem has 5 questions. Each question carries 20 marks. Total marks: 100. Duration: 3 hours. Internal choice: No.",
        session_id="session-exam",
        message_number=3,
    )
    final_result = await service.process_message(
        text="FA weight: 40%. SA weight: 60%. FA aggregation: Best 3 of 5. Pass threshold: 40%.",
        session_id="session-exam",
        message_number=3,
    )

    assert final_result["status"] == "exam_config_preview"
    assert final_result["exam_config"]["fa_weight"] == 40
    assert final_result["exam_config"]["sa_weight"] == 60
    assert final_result["exam_config"]["fa_best_n"] == 3
    assert len(final_result["exam_config"]["exams"]) == 6
    assert final_result["exam_config_summary"]["fa_count"] == 5
    assert final_result["exam_config_summary"]["sa_count"] == 1


@pytest.mark.asyncio
async def test_shorthand_question_mapping_can_collect_then_preview(state_store):
    service = make_service(FakeSession())
    state_store[service._session_key("faculty-1", "session-qmap")] = {
        "session_id": "session-qmap",
        "stage": "awaiting_question_mapping",
        "workflow_step": 4,
        "course_db_id": "course-db-1",
        "course_code": "CS301",
        "cos": [
            {"id": "CO1", "db_id": "co-db-1", "bt_level": "L2", "statement": "Explain algorithmic complexity"},
            {"id": "CO2", "db_id": "co-db-2", "bt_level": "L3", "statement": "Apply divide and conquer techniques"},
        ],
        "exam_config": {
            "exams": [
                {"exam_id": "T1", "exam_type": "FA", "question_marks": {"Q1": 10, "Q2": 10}},
                {"exam_id": "ENDSEM", "exam_type": "SA", "question_marks": {"Q1": 20}},
            ]
        },
    }

    partial = await service.process_message(
        text="T1: Q1=CO1, Q2=CO2",
        session_id="session-qmap",
        message_number=3,
    )
    assert partial["status"] == "question_mapping_collecting"

    complete = await service.process_message(
        text="ENDSEM: Q1=CO1",
        session_id="session-qmap",
        message_number=3,
    )
    assert complete["status"] == "question_mapping_preview"
    assert len(complete["question_mapping"]) == 3