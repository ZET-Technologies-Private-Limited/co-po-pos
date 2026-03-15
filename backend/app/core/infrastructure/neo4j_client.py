"""
Neo4j client for graph database operations
"""
from typing import Optional, Dict, Any, List
from neo4j import AsyncGraphDatabase, AsyncDriver
from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("neo4j_client")
settings = get_settings()

# Global Neo4j driver
_driver: Optional[AsyncDriver] = None


def is_configured() -> bool:
    """Check if Neo4j is configured"""
    return bool(settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password)


async def get_driver() -> AsyncDriver:
    """Get Neo4j driver with connection pooling"""
    global _driver
    
    if not is_configured():
        raise RuntimeError("Neo4j is not configured. Set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
    
    if _driver is None:
        try:
            _driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
            logger.info("Neo4j driver initialized")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            raise
    
    return _driver


async def verify_neo4j() -> bool:
    """Verify Neo4j connectivity"""
    if not is_configured():
        return False
    
    try:
        driver = await get_driver()
        await driver.verify_connectivity()
        return True
    except Exception as e:
        logger.error(f"Neo4j verification failed: {e}")
        return False


async def execute_query(
    query: str,
    parameters: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Execute Cypher query and return results"""
    if not is_configured():
        raise RuntimeError("Neo4j is not configured")
    
    driver = await get_driver()
    db_name = database or settings.neo4j_database
    
    async with driver.session(database=db_name) as session:
        result = await session.run(query, parameters or {})
        records = await result.data()
        return records


async def create_co_node(co_id: str, co_code: str, co_statement: str, course_id: str) -> bool:
    """Create Course Outcome node"""
    query = """
    MERGE (co:CO {id: $co_id})
    SET co.code = $co_code,
        co.statement = $co_statement,
        co.course_id = $course_id,
        co.updated_at = datetime()
    RETURN co
    """
    try:
        await execute_query(query, {
            "co_id": co_id,
            "co_code": co_code,
            "co_statement": co_statement,
            "course_id": course_id
        })
        return True
    except Exception as e:
        logger.error(f"Failed to create CO node: {e}")
        return False


async def create_po_node(po_id: str, po_code: str, po_statement: str, program_id: str) -> bool:
    """Create Program Outcome node"""
    query = """
    MERGE (po:PO {id: $po_id})
    SET po.code = $po_code,
        po.statement = $po_statement,
        po.program_id = $program_id,
        po.updated_at = datetime()
    RETURN po
    """
    try:
        await execute_query(query, {
            "po_id": po_id,
            "po_code": po_code,
            "po_statement": po_statement,
            "program_id": program_id
        })
        return True
    except Exception as e:
        logger.error(f"Failed to create PO node: {e}")
        return False


async def create_co_po_relationship(
    co_id: str,
    po_id: str,
    similarity_score: float,
    mapping_level: int
) -> bool:
    """Create CO-PO mapping relationship"""
    query = """
    MATCH (co:CO {id: $co_id})
    MATCH (po:PO {id: $po_id})
    MERGE (co)-[r:MAPS_TO_PO]->(po)
    SET r.similarity_score = $similarity_score,
        r.mapping_level = $mapping_level,
        r.updated_at = datetime()
    RETURN r
    """
    try:
        await execute_query(query, {
            "co_id": co_id,
            "po_id": po_id,
            "similarity_score": similarity_score,
            "mapping_level": mapping_level
        })
        return True
    except Exception as e:
        logger.error(f"Failed to create CO-PO relationship: {e}")
        return False


async def get_co_po_paths(co_id: str) -> List[Dict[str, Any]]:
    """Get all PO paths from a CO"""
    query = """
    MATCH (co:CO {id: $co_id})-[r:MAPS_TO_PO]->(po:PO)
    RETURN co.code as co_code,
           po.code as po_code,
           r.similarity_score as similarity_score,
           r.mapping_level as mapping_level
    ORDER BY r.similarity_score DESC
    """
    try:
        return await execute_query(query, {"co_id": co_id})
    except Exception as e:
        logger.error(f"Failed to get CO-PO paths: {e}")
        return []


async def get_po_impact_analysis(po_id: str) -> Dict[str, Any]:
    """Analyze impact of a PO across all mapped COs"""
    query = """
    MATCH (po:PO {id: $po_id})<-[r:MAPS_TO_PO]-(co:CO)
    RETURN po.code as po_code,
           po.statement as po_statement,
           count(co) as mapped_cos,
           avg(r.similarity_score) as avg_similarity,
           collect({
               co_code: co.code,
               similarity: r.similarity_score,
               mapping_level: r.mapping_level
           }) as co_mappings
    """
    try:
        results = await execute_query(query, {"po_id": po_id})
        return results[0] if results else {}
    except Exception as e:
        logger.error(f"Failed to get PO impact analysis: {e}")
        return {}


async def find_similar_cos(co_id: str, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """Find COs with similar PO mappings"""
    query = """
    MATCH (co1:CO {id: $co_id})-[r1:MAPS_TO_PO]->(po:PO)<-[r2:MAPS_TO_PO]-(co2:CO)
    WHERE co1 <> co2 AND r2.similarity_score >= $threshold
    RETURN co2.code as similar_co_code,
           co2.statement as similar_co_statement,
           po.code as common_po_code,
           r2.similarity_score as similarity_score
    ORDER BY r2.similarity_score DESC
    LIMIT 10
    """
    try:
        return await execute_query(query, {
            "co_id": co_id,
            "threshold": similarity_threshold
        })
    except Exception as e:
        logger.error(f"Failed to find similar COs: {e}")
        return []


async def get_graph_statistics() -> Dict[str, Any]:
    """Get graph database statistics"""
    queries = {
        "co_count": "MATCH (co:CO) RETURN count(co) as count",
        "po_count": "MATCH (po:PO) RETURN count(po) as count",
        "pso_count": "MATCH (pso:PSO) RETURN count(pso) as count",
        "co_po_relationships": "MATCH ()-[r:MAPS_TO_PO]->() RETURN count(r) as count",
        "co_pso_relationships": "MATCH ()-[r:MAPS_TO_PSO]->() RETURN count(r) as count",
    }
    
    stats = {}
    for key, query in queries.items():
        try:
            result = await execute_query(query)
            stats[key] = result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Failed to get {key}: {e}")
            stats[key] = 0
    
    return stats


async def close_driver():
    """Close Neo4j driver"""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")