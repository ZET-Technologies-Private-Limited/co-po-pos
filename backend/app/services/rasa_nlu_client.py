"""
Rasa NLU Client for OBE Chatbot.

Sends user messages to the Rasa NLU server (POST /model/parse) and returns
structured intent + entity data. Falls back to keyword-based detection if
the Rasa server is not reachable.

Environment Variables:
    RASA_URL       – base URL of the Rasa server (default: http://localhost:5005)
    RASA_STRICT    – when "true", do not use keyword fallback
    RASA_FALLBACK  – when "true" (default), allow keyword fallback if Rasa is unavailable
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("rasa_nlu_client")

RASA_URL: str = os.getenv("RASA_URL", "http://localhost:5005")
RASA_STRICT: bool = os.getenv("RASA_STRICT", "false").strip().lower() in {"1", "true", "yes", "on"}
RASA_FALLBACK: bool = os.getenv("RASA_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}

# ── Keyword fallback (identical to the original ChatbotService logic) ─────────
_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "generate_co": [
        "generate co", "create co", "course outcome", "generate outcomes",
        "create outcomes", "suggest co", "auto generate",
    ],
    "map_co_po": [
        "map co", "co-po", "co po mapping", "program outcome mapping",
        "map outcomes", "mapping",
    ],
    "map_co_pso": [
        "map co to pso", "co-pso", "co pso mapping", "program specific outcome mapping",
        "map pso", "map outcomes to pso",
    ],
    "map_question_co": [
        "map question", "question co mapping", "question to co", "questions to co",
        "map questions to co",
    ],
    "configure_exam": [
        "configure exam", "setup exam", "create exam", "exam configuration",
        "define exam", "exam setup",
    ],
    "calculate_attainment": [
        "calculate attainment", "compute attainment", "attainment",
        "co attainment", "exam attainment",
    ],
    "calculate_po_attainment": [
        "po attainment", "pso attainment", "calculate po", "calculate pso",
        "po pso attainment", "program outcome attainment",
    ],
    "detect_bloom": [
        "bloom level", "bloom taxonomy", "cognitive level",
        "detect bloom", "classify question",
    ],
    "generate_report": [
        "generate report", "create report", "download report",
        "export report", "get report", "report",
    ],
    "student_marks": [
        "student marks", "enter marks", "upload marks",
        "input marks", "marks entry",
    ],
    "add_questions": [
        "add questions", "question paper", "add question",
        "enter question",
    ],
    "list_courses": [
        "list courses", "show courses", "my courses",
        "available courses", "course list",
    ],
    "help": [
        "help", "what can you do", "capabilities",
        "features", "how to use",
    ],
}


def _keyword_detect(message: str) -> str:
    """Return best keyword-matched intent or 'general'."""
    text = message.lower()
    best_intent = "general"
    best_score = 0
    for intent, keywords in _INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_intent = intent
    return best_intent


# ── Rasa NLU Client ────────────────────────────────────────────────────────────

class RasaNLUClient:
    """
    Async client that sends text to a running Rasa server for NLU parsing.

    Usage::

        client = RasaNLUClient()
        result = await client.parse("generate course outcomes for CS301")
        intent_name  = result["intent"]["name"]        # e.g. "generate_co"
        confidence   = result["intent"]["confidence"]  # e.g. 0.97
        entities     = result["entities"]
        source       = result["source"]                # "rasa" | "keyword"

    The client reuses an ``httpx.AsyncClient`` for connection pooling.
    Call ``await client.close()`` when shutting down, or use as an async context manager.
    """

    def __init__(self, rasa_url: str = RASA_URL, timeout: float = 5.0):
        self._url = rasa_url.rstrip("/")
        self._http = httpx.AsyncClient(timeout=timeout)
        self._rasa_alive: Optional[bool] = None  # None = untested

    # ── Context manager support ───────────────────────────────────────────────

    async def __aenter__(self) -> "RasaNLUClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._http.aclose()

    # ── Public API ────────────────────────────────────────────────────────────

    async def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse *text* and return a unified NLU result dict::

            {
                "intent":          {"name": str, "confidence": float},
                "entities":        [{"entity": str, "value": str, ...}],
                "intent_ranking":  [{"name": str, "confidence": float}, ...],
                "source":          "rasa" | "keyword" | "error",
            }
        """
        rasa_result = await self._call_rasa(text)
        if rasa_result is not None:
            return {
                "intent": rasa_result.get("intent", {"name": "general", "confidence": 0.0}),
                "entities": rasa_result.get("entities", []),
                "intent_ranking": rasa_result.get("intent_ranking", []),
                "source": "rasa",
            }

        if RASA_STRICT and not RASA_FALLBACK:
            return {
                "intent": {"name": "general", "confidence": 0.0},
                "entities": [],
                "intent_ranking": [],
                "source": "error",
            }

        # Optional keyword fallback
        intent_name = _keyword_detect(text)
        return {
            "intent": {"name": intent_name, "confidence": 1.0},
            "entities": [],
            "intent_ranking": [],
            "source": "keyword",
        }

    async def is_rasa_alive(self) -> bool:
        """Return True if the Rasa server is reachable."""
        try:
            resp = await self._http.get(f"{self._url}/")
            self._rasa_alive = resp.status_code == 200
        except Exception:
            self._rasa_alive = False
        return bool(self._rasa_alive)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _call_rasa(self, text: str) -> Optional[Dict[str, Any]]:
        """POST /model/parse to Rasa. Returns parsed JSON or None on failure."""
        try:
            response = await self._http.post(
                f"{self._url}/model/parse",
                json={"text": text},
            )
            if response.status_code == 200:
                if self._rasa_alive is not True:
                    logger.info(f"Rasa NLU server connected at {self._url}")
                self._rasa_alive = True
                return response.json()

            logger.warning(
                f"Rasa returned HTTP {response.status_code}. Falling back to keyword detection."
            )
            self._rasa_alive = False
            return None

        except httpx.ConnectError:
            if self._rasa_alive is not False:
                logger.warning(
                    f"Rasa server not reachable at {self._url}. "
                    "Using keyword-based intent detection. "
                    "Start Rasa with: cd backend/rasa && rasa run --enable-api"
                )
            self._rasa_alive = False
            return None

        except Exception as exc:
            logger.warning(f"Rasa parse error: {exc}. Falling back to keyword detection.")
            self._rasa_alive = False
            return None


# ── Module-level singleton (reused across requests for connection pooling) ─────
_client: Optional[RasaNLUClient] = None


def get_rasa_client() -> RasaNLUClient:
    """Return (or create) the module-level RasaNLUClient singleton."""
    global _client
    if _client is None:
        _client = RasaNLUClient()
    return _client
