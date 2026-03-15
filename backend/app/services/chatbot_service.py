"""
OBE Chatbot Service – thin entry point that delegates every message to the
LangGraph + Rasa NLU workflow defined in ``app.agents.langgraph_workflow``.

The full intent detection (Rasa NLU with keyword fallback) and all workflow
logic live in the LangGraph graph.  This class exists only to provide the
session-bound ``process_message`` API that the REST route expects.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.langgraph_workflow import run_obe_workflow
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("chatbot_service")


class ChatbotService:
    """Session-aware thin wrapper around the LangGraph OBE workflow."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_message(
        self,
        message: str,
        course_id: Optional[str],
        session_id: Optional[str],
        user_id: Optional[str] = None,
        force_node: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the Rasa NLU + LangGraph OBE workflow for *message* and return a
        unified response dict::

            {
                "reply":          str,
                "intent":         str,
                "nlu_confidence": float,
                "nlu_source":     str,   # "rasa" | "keyword"
                "data":           dict | None,
                "session_id":     str,
            }
        """
        session_id = session_id or str(uuid.uuid4())
        logger.info(f"process_message: {message[:80]!r}", course_id=course_id)

        return await run_obe_workflow(
            message=message,
            course_id=course_id,
            session_id=session_id,
            db_session=self.session,
            user_id=user_id,
            force_node=force_node,
        )
