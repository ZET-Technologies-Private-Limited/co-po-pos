"""
Elasticsearch client for question bank indexing and search.
"""
from __future__ import annotations

import importlib
from typing import Any, Dict, List

from app.core.config.settings import get_settings

settings = get_settings()


def is_configured() -> bool:
    return bool(settings.elasticsearch_url)


def _client():
    if not is_configured():
        raise RuntimeError("ELASTICSEARCH_URL is not configured")

    es_module = importlib.import_module("elasticsearch")
    Elasticsearch = es_module.Elasticsearch

    kwargs: Dict[str, Any] = {"hosts": [settings.elasticsearch_url]}
    if settings.elasticsearch_user and settings.elasticsearch_password:
        kwargs["basic_auth"] = (settings.elasticsearch_user, settings.elasticsearch_password)
    return Elasticsearch(**kwargs)


def index_question(document_id: str, payload: Dict[str, Any]) -> None:
    client = _client()
    client.index(index=settings.elasticsearch_index_questions, id=document_id, document=payload)


def search_questions(query_text: str, size: int = 20) -> List[Dict[str, Any]]:
    client = _client()
    result = client.search(
        index=settings.elasticsearch_index_questions,
        size=size,
        query={
            "multi_match": {
                "query": query_text,
                "fields": ["question_text^3", "course_id", "exam_id", "bloom_level", "co_codes"],
            }
        },
    )
    hits = result.get("hits", {}).get("hits", [])
    return [
        {
            "id": h.get("_id"),
            "score": h.get("_score"),
            "source": h.get("_source", {}),
        }
        for h in hits
    ]
