"""
Neo4j-backed graph service for CO/PO/PSO relationship persistence and traversal.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.infrastructure.neo4j_client import get_driver, is_configured
from app.core.config.settings import get_settings


class GraphMappingService:
    def __init__(self):
        self.settings = get_settings()

    async def sync_co_po_mappings(self, mappings: List[Dict[str, Any]]) -> None:
        if not mappings:
            return
        if not is_configured():
            raise RuntimeError("Neo4j is not configured")

        driver = await get_driver()
        query = """
        UNWIND $rows AS row
        MERGE (co:CO {id: row.course_outcome_id})
        MERGE (po:PO {id: row.program_outcome_id})
        MERGE (co)-[r:MAPS_TO_PO]->(po)
        SET r.similarity_score = row.similarity_score,
            r.updated_at = datetime()
        """
        async with driver.session(database=self.settings.neo4j_database) as session:
            await session.run(query, rows=mappings)

    async def sync_co_pso_mappings(self, mappings: List[Dict[str, Any]]) -> None:
        if not mappings:
            return
        if not is_configured():
            raise RuntimeError("Neo4j is not configured")

        driver = await get_driver()
        query = """
        UNWIND $rows AS row
        MERGE (co:CO {id: row.course_outcome_id})
        MERGE (pso:PSO {id: row.program_specific_outcome_id})
        MERGE (co)-[r:MAPS_TO_PSO]->(pso)
        SET r.similarity_score = row.similarity_score,
            r.updated_at = datetime()
        """
        async with driver.session(database=self.settings.neo4j_database) as session:
            await session.run(query, rows=mappings)

    async def get_po_impact_path(self, co_id: str) -> List[Dict[str, Any]]:
        if not is_configured():
            raise RuntimeError("Neo4j is not configured")

        driver = await get_driver()
        query = """
        MATCH (co:CO {id: $co_id})-[r:MAPS_TO_PO]->(po:PO)
        RETURN co.id AS co_id, po.id AS po_id, r.similarity_score AS similarity_score
        ORDER BY r.similarity_score DESC
        """
        async with driver.session(database=self.settings.neo4j_database) as session:
            result = await session.run(query, co_id=co_id)
            rows = await result.data()
        return rows
