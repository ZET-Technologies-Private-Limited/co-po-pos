"""
Background tasks for heavy attainment calculations.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

from app.core.database.connection_manager import db_manager
from app.core.infrastructure.celery_app import celery_app
from app.modules.attainment_engine.services.attainment_service import AttainmentService


async def _run_pipeline_async(course_id: str, program_id: str, threshold_pct: float) -> Dict[str, Any]:
    await db_manager.initialize()
    session = await db_manager.get_session()
    try:
        service = AttainmentService(session)
        result = await service.run_full_attainment_pipeline(course_id, program_id, threshold_pct)
        return result
    finally:
        await session.close()
        await db_manager.close()


@celery_app.task(name="attainment.run_full_pipeline")
def run_full_pipeline_task(course_id: str, program_id: str, threshold_pct: float = 0.60) -> Dict[str, Any]:
    return asyncio.run(_run_pipeline_async(course_id, program_id, threshold_pct))
