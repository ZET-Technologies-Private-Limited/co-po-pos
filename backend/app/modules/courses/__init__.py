"""Course management module"""
from app.modules.courses.repositories.course_repository import (
    CourseRepository,
    CourseOutcomeRepository,
    ExamRepository
)

__all__ = [
    "CourseRepository",
    "CourseOutcomeRepository",
    "ExamRepository"
]
