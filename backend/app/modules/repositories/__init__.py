"""Repositories module"""
from app.modules.repositories.base_repository import BaseRepository
from app.modules.repositories.course_repository import CourseRepository
from app.modules.repositories.co_repository import CourseOutcomeRepository
from app.modules.repositories.exam_repository import ExamRepository, ExamQuestionRepository, StudentMarksRepository

__all__ = [
    "BaseRepository",
    "CourseRepository",
    "CourseOutcomeRepository",
    "ExamRepository",
    "ExamQuestionRepository",
    "StudentMarksRepository"
]
