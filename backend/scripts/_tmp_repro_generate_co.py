import asyncio
from sqlalchemy import select

from app.core.database.connection_manager import db_manager, get_session
from app.core.database.models import Course
from app.modules.co_generation.services.co_generation_service import CoGenerationService


async def main() -> None:
    await db_manager.initialize()
    async for session in get_session():
        course = (await session.execute(select(Course).limit(1))).scalar_one_or_none()
        if not course:
            print("No course found")
            break

        print("Using course:", course.id, course.course_code, course.department)
        svc = CoGenerationService(session)
        payload_pos = [
            {"code": "PO1", "statement": "Engineering knowledge"},
            {"code": "PO2", "statement": "Problem analysis"},
            {"code": "PO3", "statement": "Design and development"},
            {"code": "PO4", "statement": "Complex investigations"},
            {"code": "PO5", "statement": "Modern tool usage"},
            {"code": "PO6", "statement": "Engineer and society"},
            {"code": "PO7", "statement": "Environment sustainability"},
            {"code": "PO8", "statement": "Ethics"},
            {"code": "PO9", "statement": "Team work"},
            {"code": "PO10", "statement": "Communication"},
            {"code": "PO11", "statement": "Project management"},
            {"code": "PO12", "statement": "Life-long learning"},
        ]
        payload_psos = [
            {"code": "PSO1", "statement": "Apply algorithmic thinking"},
            {"code": "PSO2", "statement": "Develop software solutions"},
        ]

        try:
            result = await svc.generate_cos_from_syllabus(
                course_id=str(course.id),
                syllabus=(course.syllabus or "Unit 1 Data structures. Unit 2 Trees. Unit 3 Graphs."),
                program_outcomes=payload_pos,
                program_specific_outcomes=payload_psos,
                num_cos=5,
            )
            print("SUCCESS")
            print("cos:", len(result.get("course_outcomes", [])))
            print("po maps:", len(result.get("co_po_mappings", [])))
            print("pso maps:", len(result.get("co_pso_mappings", [])))
            print("warnings:", result.get("quality_warnings", []))
        except Exception as exc:
            print("FAILED:", type(exc).__name__, str(exc))
            raise
        break

    await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
