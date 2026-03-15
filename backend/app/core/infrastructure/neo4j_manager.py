"""
Neo4j Graph Database Implementation
Handles CO-PO-PSO relationship graph with weighted traversal
"""
from typing import Dict, Any, List, Optional, Tuple
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
import asyncio
import json
from datetime import datetime

from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("neo4j_manager")

class Neo4jManager:
    """Neo4j graph database manager for OBE relationships"""
    
    def __init__(self):
        self.settings = get_settings()
        self.driver = None
        self._initialized = False
        
        # Neo4j connection settings
        self.uri = getattr(self.settings, 'neo4j_uri', 'bolt://localhost:7687')
        self.username = getattr(self.settings, 'neo4j_username', 'neo4j')
        self.password = getattr(self.settings, 'neo4j_password', 'password')
    
    async def initialize(self):
        """Initialize Neo4j driver"""
        if self._initialized:
            return
        
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
            
            # Test connection
            await self.driver.verify_connectivity()
            
            # Create constraints and indexes
            await self._create_constraints()
            
            self._initialized = True
            logger.info("Neo4j driver initialized successfully")
            
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Neo4j initialization error: {str(e)}")
            raise
    
    async def _create_constraints(self):
        """Create Neo4j constraints and indexes"""
        constraints = [
            "CREATE CONSTRAINT co_id_unique IF NOT EXISTS FOR (co:CourseOutcome) REQUIRE co.co_id IS UNIQUE",
            "CREATE CONSTRAINT po_id_unique IF NOT EXISTS FOR (po:ProgramOutcome) REQUIRE po.po_id IS UNIQUE",
            "CREATE CONSTRAINT course_id_unique IF NOT EXISTS FOR (c:Course) REQUIRE c.course_id IS UNIQUE",
            "CREATE CONSTRAINT dept_id_unique IF NOT EXISTS FOR (d:Department) REQUIRE d.dept_id IS UNIQUE",
            "CREATE CONSTRAINT ay_id_unique IF NOT EXISTS FOR (ay:AcademicYear) REQUIRE ay.ay_id IS UNIQUE",
            "CREATE INDEX co_course_id IF NOT EXISTS FOR (co:CourseOutcome) ON (co.course_id)",
            "CREATE INDEX po_dept_id IF NOT EXISTS FOR (po:ProgramOutcome) ON (po.dept_id)",
            "CREATE INDEX maps_to_correlation IF NOT EXISTS FOR ()-[r:MAPS_TO]-() ON (r.correlation)"
        ]
        
        async with self.driver.session() as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    logger.debug(f"Constraint/index already exists or failed: {e}")
    
    async def close(self):
        """Close Neo4j driver"""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j driver closed")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # NODE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def create_course_outcome_node(self, co_data: Dict[str, Any]) -> bool:
        """Create CourseOutcome node"""
        query = """
        MERGE (co:CourseOutcome {co_id: $co_id})
        SET co.co_number = $co_number,
            co.bt_level = $bt_level,
            co.course_id = $course_id,
            co.ay_id = $ay_id,
            co.statement = $statement,
            co.created_at = datetime()
        RETURN co
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, **co_data)
                await result.consume()
                logger.debug(f"Created CO node: {co_data['co_id']}")
                return True
            except Exception as e:
                logger.error(f"Failed to create CO node: {e}")
                return False
    
    async def create_program_outcome_node(self, po_data: Dict[str, Any]) -> bool:
        """Create ProgramOutcome node"""
        query = """
        MERGE (po:ProgramOutcome {po_id: $po_id})
        SET po.po_code = $po_code,
            po.po_type = $po_type,
            po.dept_id = $dept_id,
            po.regulation_year = $regulation_year,
            po.statement = $statement,
            po.created_at = datetime()
        RETURN po
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, **po_data)
                await result.consume()
                logger.debug(f"Created PO node: {po_data['po_id']}")
                return True
            except Exception as e:
                logger.error(f"Failed to create PO node: {e}")
                return False
    
    async def create_course_node(self, course_data: Dict[str, Any]) -> bool:
        """Create Course node"""
        query = """
        MERGE (c:Course {course_id: $course_id})
        SET c.course_code = $course_code,
            c.dept_id = $dept_id,
            c.course_name = $course_name,
            c.created_at = datetime()
        RETURN c
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, **course_data)
                await result.consume()
                return True
            except Exception as e:
                logger.error(f"Failed to create Course node: {e}")
                return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIP OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def create_co_po_mapping(self, co_id: str, po_id: str, correlation: int, is_ai_assigned: bool = True) -> bool:
        """Create MAPS_TO relationship between CO and PO"""
        query = """
        MATCH (co:CourseOutcome {co_id: $co_id})
        MATCH (po:ProgramOutcome {po_id: $po_id})
        MERGE (co)-[r:MAPS_TO]->(po)
        SET r.correlation = $correlation,
            r.is_ai_assigned = $is_ai_assigned,
            r.created_at = datetime()
        RETURN r
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, 
                    co_id=co_id, 
                    po_id=po_id, 
                    correlation=correlation, 
                    is_ai_assigned=is_ai_assigned
                )
                await result.consume()
                logger.debug(f"Created CO-PO mapping: {co_id} -> {po_id} (correlation: {correlation})")
                return True
            except Exception as e:
                logger.error(f"Failed to create CO-PO mapping: {e}")
                return False
    
    async def create_co_belongs_to_course(self, co_id: str, course_id: str) -> bool:
        """Create BELONGS_TO relationship between CO and Course"""
        query = """
        MATCH (co:CourseOutcome {co_id: $co_id})
        MATCH (c:Course {course_id: $course_id})
        MERGE (co)-[r:BELONGS_TO]->(c)
        SET r.created_at = datetime()
        RETURN r
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, co_id=co_id, course_id=course_id)
                await result.consume()
                return True
            except Exception as e:
                logger.error(f"Failed to create CO-Course relationship: {e}")
                return False
    
    async def create_attainment_relationship(self, co_id: str, attainment_data: Dict[str, Any]) -> bool:
        """Create HAS_ATTAINMENT relationship"""
        query = """
        MATCH (co:CourseOutcome {co_id: $co_id})
        MERGE (att:Attainment {attainment_id: $attainment_id})
        SET att.final_pct = $final_pct,
            att.level = $level,
            att.ay_id = $ay_id,
            att.computed_at = datetime()
        MERGE (co)-[r:HAS_ATTAINMENT]->(att)
        SET r.ay_id = $ay_id
        RETURN r
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, co_id=co_id, **attainment_data)
                await result.consume()
                return True
            except Exception as e:
                logger.error(f"Failed to create attainment relationship: {e}")
                return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERY OPERATIONS - Key Cypher queries from specification
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def get_po_attainment(self, po_code: str, dept_id: str, ay_code: str) -> Optional[float]:
        """Query 1: PO1 Attainment for a Department"""
        query = """
        MATCH (co:CourseOutcome)-[r:MAPS_TO]->(po:ProgramOutcome {po_code: $po_code})
        -[:BELONGS_TO]->(c:Course)-[:IN_AY]->(ay:AcademicYear {ay_code: $ay_code})
        WHERE c.dept_id = $dept_id
        MATCH (co)-[:HAS_ATTAINMENT]->(att:Attainment)
        RETURN SUM(att.final_pct * r.correlation) / SUM(r.correlation) AS po_attainment
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, 
                    po_code=po_code, 
                    dept_id=dept_id, 
                    ay_code=ay_code
                )
                record = await result.single()
                return record["po_attainment"] if record else None
            except Exception as e:
                logger.error(f"Failed to get PO attainment: {e}")
                return None
    
    async def get_cos_mapped_to_pso(self, pso_code: str, correlation: int = 3) -> List[Dict[str, Any]]:
        """Query 2: All COs Mapped to PSO2 with High Correlation"""
        query = """
        MATCH (co:CourseOutcome)-[r:MAPS_TO {correlation: $correlation}]->(pso:ProgramOutcome {po_code: $pso_code})
        RETURN co.co_id, co.co_number, co.bt_level, co.statement
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, pso_code=pso_code, correlation=correlation)
                records = await result.data()
                return [
                    {
                        "co_id": record["co.co_id"],
                        "co_number": record["co.co_number"],
                        "bt_level": record["co.bt_level"],
                        "statement": record["co.statement"]
                    }
                    for record in records
                ]
            except Exception as e:
                logger.error(f"Failed to get COs mapped to PSO: {e}")
                return []
    
    async def get_co_attainment_trend(self, course_code: str, co_number: int, years: List[str]) -> List[Dict[str, Any]]:
        """Query 3: 3-Year CO1 Attainment Trend for CS301"""
        query = """
        MATCH (co:CourseOutcome {co_number: $co_number})-[:BELONGS_TO]->(c:Course {course_code: $course_code})
        MATCH (co)-[:HAS_ATTAINMENT]->(att:Attainment)
        MATCH (c)-[:IN_AY]->(ay:AcademicYear)
        WHERE ay.ay_code IN $years
        RETURN ay.ay_code, att.final_pct 
        ORDER BY ay.ay_code
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, 
                    co_number=co_number, 
                    course_code=course_code, 
                    years=years
                )
                records = await result.data()
                return [
                    {
                        "academic_year": record["ay.ay_code"],
                        "attainment_percentage": record["att.final_pct"]
                    }
                    for record in records
                ]
            except Exception as e:
                logger.error(f"Failed to get CO attainment trend: {e}")
                return []
    
    async def get_all_po_attainments(self, dept_id: str, ay_code: str) -> List[Dict[str, Any]]:
        """Get all PO attainments for department and academic year"""
        query = """
        MATCH (po:ProgramOutcome)-[:DEFINED_FOR]->(d:Department {dept_id: $dept_id})
        MATCH (co:CourseOutcome)-[r:MAPS_TO]->(po)
        MATCH (co)-[:BELONGS_TO]->(c:Course)-[:IN_AY]->(ay:AcademicYear {ay_code: $ay_code})
        MATCH (co)-[:HAS_ATTAINMENT]->(att:Attainment)
        WITH po, SUM(att.final_pct * r.correlation) / SUM(r.correlation) AS po_attainment
        RETURN po.po_code, po.po_type, po.statement, po_attainment
        ORDER BY po.po_code
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, dept_id=dept_id, ay_code=ay_code)
                records = await result.data()
                return [
                    {
                        "po_code": record["po.po_code"],
                        "po_type": record["po.po_type"],
                        "statement": record["po.statement"],
                        "attainment_percentage": record["po_attainment"]
                    }
                    for record in records
                ]
            except Exception as e:
                logger.error(f"Failed to get all PO attainments: {e}")
                return []
    
    async def get_co_po_correlation_matrix(self, course_id: str) -> Dict[str, Any]:
        """Get CO-PO correlation matrix"""
        query = """
        MATCH (co:CourseOutcome)-[:BELONGS_TO]->(c:Course {course_id: $course_id})
        MATCH (co)-[r:MAPS_TO]->(po:ProgramOutcome)
        RETURN co.co_number, co.co_id, po.po_code, r.correlation
        ORDER BY co.co_number, po.po_code
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, course_id=course_id)
                records = await result.data()
                
                # Build matrix
                matrix = {}
                cos = set()
                pos = set()
                
                for record in records:
                    co_code = f"CO{record['co.co_number']}"
                    po_code = record["po.po_code"]
                    correlation = record["r.correlation"]
                    
                    cos.add(co_code)
                    pos.add(po_code)
                    
                    if co_code not in matrix:
                        matrix[co_code] = {}
                    matrix[co_code][po_code] = correlation
                
                return {
                    "cos": sorted(list(cos)),
                    "pos": sorted(list(pos)),
                    "data": matrix
                }
                
            except Exception as e:
                logger.error(f"Failed to get CO-PO matrix: {e}")
                return {"cos": [], "pos": [], "data": {}}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BULK OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def sync_from_postgresql(self, course_id: str):
        """Sync CO-PO-PSO data from PostgreSQL to Neo4j"""
        from app.core.database.connection_manager import db_manager
        from app.core.database.models import (
            CourseOutcome, ProgramOutcome, ProgramSpecificOutcome,
            co_po_mapping_table, co_pso_mapping_table
        )
        from sqlalchemy import select
        
        session = await db_manager.get_session()
        try:
            # Get COs for course
            cos_result = await session.execute(
                select(CourseOutcome).where(CourseOutcome.course_id == course_id)
            )
            cos = cos_result.scalars().all()
            
            # Create CO nodes
            for co in cos:
                await self.create_course_outcome_node({
                    "co_id": co.id,
                    "co_number": int(co.code.replace("CO", "")),
                    "bt_level": str(co.bloom_level),
                    "course_id": co.course_id,
                    "ay_id": "2024-25",  # Current AY
                    "statement": co.statement
                })
            
            # Get CO-PO mappings
            mappings_result = await session.execute(
                select(
                    co_po_mapping_table.c.course_outcome_id,
                    co_po_mapping_table.c.program_outcome_id,
                    co_po_mapping_table.c.similarity_score
                ).where(
                    co_po_mapping_table.c.course_outcome_id.in_([co.id for co in cos])
                )
            )
            mappings = mappings_result.all()
            
            # Create CO-PO relationships
            for mapping in mappings:
                correlation = 3 if mapping[2] >= 0.75 else (2 if mapping[2] >= 0.50 else 1)
                await self.create_co_po_mapping(
                    mapping[0], mapping[1], correlation, is_ai_assigned=True
                )
            
            logger.info(f"Synced {len(cos)} COs and {len(mappings)} mappings to Neo4j")
            
        finally:
            await session.close()
    
    async def clear_course_data(self, course_id: str):
        """Clear all Neo4j data for a course"""
        query = """
        MATCH (co:CourseOutcome)-[:BELONGS_TO]->(c:Course {course_id: $course_id})
        DETACH DELETE co
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, course_id=course_id)
                summary = await result.consume()
                logger.info(f"Cleared Neo4j data for course {course_id}: {summary.counters}")
            except Exception as e:
                logger.error(f"Failed to clear course data: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYTICS QUERIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def get_department_overview(self, dept_id: str, ay_code: str) -> Dict[str, Any]:
        """Get comprehensive department overview"""
        query = """
        MATCH (d:Department {dept_id: $dept_id})
        MATCH (c:Course)-[:OFFERED_BY]->(d)
        MATCH (c)-[:IN_AY]->(ay:AcademicYear {ay_code: $ay_code})
        MATCH (co:CourseOutcome)-[:BELONGS_TO]->(c)
        MATCH (co)-[:HAS_ATTAINMENT]->(att:Attainment)
        RETURN 
            COUNT(DISTINCT c) AS total_courses,
            COUNT(DISTINCT co) AS total_cos,
            AVG(att.final_pct) AS avg_co_attainment,
            COUNT(CASE WHEN att.level = 3 THEN 1 END) AS level3_cos,
            COUNT(CASE WHEN att.level = 2 THEN 1 END) AS level2_cos,
            COUNT(CASE WHEN att.level = 1 THEN 1 END) AS level1_cos
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, dept_id=dept_id, ay_code=ay_code)
                record = await result.single()
                
                if record:
                    return {
                        "dept_id": dept_id,
                        "academic_year": ay_code,
                        "total_courses": record["total_courses"],
                        "total_cos": record["total_cos"],
                        "avg_co_attainment": record["avg_co_attainment"],
                        "level_distribution": {
                            "level3": record["level3_cos"],
                            "level2": record["level2_cos"],
                            "level1": record["level1_cos"]
                        }
                    }
                return {}
                
            except Exception as e:
                logger.error(f"Failed to get department overview: {e}")
                return {}
    
    async def find_weak_co_po_mappings(self, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Find CO-PO mappings with low correlation"""
        query = """
        MATCH (co:CourseOutcome)-[r:MAPS_TO]->(po:ProgramOutcome)
        WHERE r.correlation <= $threshold
        MATCH (co)-[:BELONGS_TO]->(c:Course)
        RETURN co.co_id, co.co_number, c.course_code, po.po_code, r.correlation
        ORDER BY r.correlation ASC
        """
        
        async with self.driver.session() as session:
            try:
                result = await session.run(query, threshold=threshold)
                records = await result.data()
                return [
                    {
                        "co_id": record["co.co_id"],
                        "co_number": record["co.co_number"],
                        "course_code": record["c.course_code"],
                        "po_code": record["po.po_code"],
                        "correlation": record["r.correlation"]
                    }
                    for record in records
                ]
            except Exception as e:
                logger.error(f"Failed to find weak mappings: {e}")
                return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Neo4j health"""
        try:
            async with self.driver.session() as session:
                start_time = datetime.utcnow()
                result = await session.run("RETURN 1 AS health_check")
                await result.consume()
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Get database info
                db_info = await session.run("CALL dbms.components() YIELD name, versions, edition")
                info_records = await db_info.data()
                
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "database_info": info_records,
                    "driver_version": "5.x"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Global Neo4j manager instance
neo4j_manager = Neo4jManager()

# Convenience functions
async def create_co_node(co_data: Dict[str, Any]) -> bool:
    """Create CourseOutcome node"""
    return await neo4j_manager.create_course_outcome_node(co_data)

async def create_po_node(po_data: Dict[str, Any]) -> bool:
    """Create ProgramOutcome node"""
    return await neo4j_manager.create_program_outcome_node(po_data)

async def map_co_to_po(co_id: str, po_id: str, correlation: int) -> bool:
    """Create CO-PO mapping relationship"""
    return await neo4j_manager.create_co_po_mapping(co_id, po_id, correlation)

async def get_po_attainment_from_graph(po_code: str, dept_id: str, ay_code: str) -> Optional[float]:
    """Get PO attainment using graph traversal"""
    return await neo4j_manager.get_po_attainment(po_code, dept_id, ay_code)