"""
Semantic CO-PO/PSO mapping using AI and embeddings
"""
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, delete, select, and_
from app.core.database.models import (
    CourseOutcome, ProgramOutcome, ProgramSpecificOutcome,
    co_po_mapping_table, co_pso_mapping_table, question_co_mapping_table,
    ExamQuestion
)
from app.ai_engine.embeddings.embedding_service import embedding_service
from app.ai_engine.llm.llm_client import llm_client
from app.core.config.constants import (
    SEMANTIC_SIMILARITY_THRESHOLD_HIGH,
    SEMANTIC_SIMILARITY_THRESHOLD_MEDIUM
)
from app.core.logging.system_logger import SystemLogger
from app.communication.events.event_bus import event_bus, EventType, SystemEvent
from app.modules.mapping.services.graph_mapping_service import GraphMappingService
from app.core.infrastructure.neo4j_client import is_configured as neo4j_is_configured
from datetime import datetime
import numpy as np
import re


class SemanticMappingService:
    """Perform semantic CO-PO/PSO mapping using embeddings"""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.logger = SystemLogger("semantic_mapping")
        self.high_threshold = SEMANTIC_SIMILARITY_THRESHOLD_HIGH
        self.medium_threshold = SEMANTIC_SIMILARITY_THRESHOLD_MEDIUM
        self.graph_service = GraphMappingService()

    async def auto_map_cos_to_pos(
        self,
        course_id: str,
        program_id: str,
        threshold: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """Route-compatible wrapper that returns only mappings list."""
        if not self.session:
            raise ValueError("Database session is required")

        self.medium_threshold = threshold
        result = await self.map_cos_to_pos(self.session, course_id, program_id)
        return result.get("mappings", [])
    
    async def map_cos_to_pos(
        self,
        session: AsyncSession,
        course_id: str,
        program_id: str
    ) -> Dict[str, Any]:
        """Map Course Outcomes to Program Outcomes"""
        try:
            self.logger.info("Starting CO-PO mapping", course_id=course_id, program_id=program_id)
            
            # Get COs for course
            cos_result = await session.execute(
                select(CourseOutcome).where(CourseOutcome.course_id == course_id)
            )
            cos = cos_result.scalars().all()
            
            if not cos:
                self.logger.warning("No COs found for course", course_id=course_id)
                return {"success": False, "message": "No COs found"}
            
            # Get POs for program
            pos_result = await session.execute(
                select(ProgramOutcome).where(ProgramOutcome.program == program_id)
            )
            pos = pos_result.scalars().all()
            
            if not pos:
                self.logger.warning("No POs found for program", program_id=program_id)
                return {"success": False, "message": "No POs found"}
            
            # Dynamic mapping selection per CO (no forced minimum levels).
            mappings = []
            for co in cos:
                scored: List[Tuple[ProgramOutcome, float]] = []
                for po in pos:
                    similarity = await self._combined_similarity(co.statement, po.statement)
                    scored.append((po, similarity))

                selected = self._select_dynamic_mappings(scored, self.medium_threshold)
                for po_obj, similarity in selected:
                    mappings.append({
                        "course_outcome_id": co.id,
                        "program_outcome_id": po_obj.id,
                        "similarity_score": float(round(similarity, 4)),
                    })
            
            # Delete existing mappings
            await session.execute(
                delete(co_po_mapping_table).where(
                    co_po_mapping_table.c.course_outcome_id.in_([c.id for c in cos])
                )
            )
            
            # Insert new mappings
            if mappings:
                await session.execute(
                    insert(co_po_mapping_table).values(mappings)
                )
            
            await session.commit()

            if mappings and neo4j_is_configured():
                try:
                    await self.graph_service.sync_co_po_mappings(mappings)
                except Exception as exc:
                    self.logger.warning("Neo4j sync skipped for CO-PO mappings", error=str(exc))

            try:
                await event_bus.publish(SystemEvent(
                    event_type=EventType.CO_MAPPED,
                    timestamp=datetime.utcnow(),
                    source_module="semantic_mapping_service",
                    data={
                        "course_id": course_id,
                        "program_id": program_id,
                        "mapping_type": "co_po",
                        "mapping_count": len(mappings),
                    },
                ))
            except Exception as exc:
                self.logger.warning("Event publish skipped for CO-PO mappings", error=str(exc))
            
            self.logger.info(
                "CO-PO mapping completed",
                course_id=course_id,
                mapping_count=len(mappings)
            )
            
            return {
                "success": True,
                "course_id": course_id,
                "program_id": program_id,
                "mapping_count": len(mappings),
                "mappings": mappings
            }
        
        except Exception as e:
            self.logger.error("CO-PO mapping failed", error=str(e))
            await session.rollback()
            return {"success": False, "error": str(e)}
    
    async def map_cos_to_psos(
        self,
        session: AsyncSession,
        course_id: str,
        program_id: str,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Map Course Outcomes to Program Specific Outcomes"""
        try:
            self.logger.info("Starting CO-PSO mapping", course_id=course_id, program_id=program_id)
            if threshold is not None:
                self.medium_threshold = threshold
            
            # Get COs
            cos_result = await session.execute(
                select(CourseOutcome).where(CourseOutcome.course_id == course_id)
            )
            cos = cos_result.scalars().all()
            
            # Get PSOs
            psos_result = await session.execute(
                select(ProgramSpecificOutcome).where(ProgramSpecificOutcome.program == program_id)
            )
            psos = psos_result.scalars().all()
            
            if not cos or not psos:
                return {"success": False, "message": "Missing COs or PSOs"}
            
            # Dynamic mapping selection per CO with adaptive thresholds
            mappings = []
            for co in cos:
                scored: List[Tuple[ProgramSpecificOutcome, float]] = []
                for pso in psos:
                    similarity = await self._combined_similarity(co.statement, pso.statement)
                    scored.append((pso, similarity))

                selected = self._select_dynamic_mappings(scored, self.medium_threshold)
                for pso_obj, similarity in selected:
                    mappings.append({
                        "course_outcome_id": co.id,
                        "program_specific_outcome_id": pso_obj.id,
                        "similarity_score": float(round(similarity, 4)),
                    })
            
            # Update mappings
            await session.execute(
                delete(co_pso_mapping_table).where(
                    co_pso_mapping_table.c.course_outcome_id.in_([c.id for c in cos])
                )
            )
            
            if mappings:
                await session.execute(
                    insert(co_pso_mapping_table).values(mappings)
                )
            
            await session.commit()

            if mappings and neo4j_is_configured():
                try:
                    await self.graph_service.sync_co_pso_mappings(mappings)
                except Exception as exc:
                    self.logger.warning("Neo4j sync skipped for CO-PSO mappings", error=str(exc))

            try:
                await event_bus.publish(SystemEvent(
                    event_type=EventType.CO_MAPPED,
                    timestamp=datetime.utcnow(),
                    source_module="semantic_mapping_service",
                    data={
                        "course_id": course_id,
                        "program_id": program_id,
                        "mapping_type": "co_pso",
                        "mapping_count": len(mappings),
                    },
                ))
            except Exception as exc:
                self.logger.warning("Event publish skipped for CO-PSO mappings", error=str(exc))
            
            return {
                "success": True,
                "course_id": course_id,
                "program_id": program_id,
                "mapping_count": len(mappings),
                "mappings": mappings
            }
        
        except Exception as e:
            self.logger.error("CO-PSO mapping failed", error=str(e))
            await session.rollback()
            return {"success": False, "error": str(e)}
    
    async def map_questions_to_cos(
        self,
        session: AsyncSession,
        exam_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """Map exam questions to course outcomes"""
        try:
            self.logger.info("Starting question-CO mapping", exam_id=exam_id)
            
            # Get questions
            questions_result = await session.execute(
                select(ExamQuestion).where(ExamQuestion.exam_id == exam_id)
            )
            questions = questions_result.unique().scalars().all()
            
            # Get COs
            cos_result = await session.execute(
                select(CourseOutcome).where(CourseOutcome.course_id == course_id)
            )
            cos = cos_result.scalars().all()
            
            if not questions or not cos:
                return {"success": False, "message": "Missing questions or COs"}
            
            # Calculate similarities
            mappings = []
            for question in questions:
                for co in cos:
                    # Use both semantic and keyword-based matching
                    semantic_sim = await self._calculate_similarity(
                        question.question_text, co.statement
                    )
                    keyword_sim = self._keyword_similarity(question.question_text, co.statement)
                    combined_sim = (semantic_sim * 0.7) + (keyword_sim * 0.3)
                    
                    if combined_sim >= self.medium_threshold:
                        mappings.append({
                            "question_id": question.id,
                            "course_outcome_id": co.id,
                            "similarity_score": combined_sim,
                            "confidence_score": semantic_sim
                        })
            
            # Update mappings
            question_ids = [q.id for q in questions]
            await session.execute(
                delete(question_co_mapping_table).where(
                    question_co_mapping_table.c.question_id.in_(question_ids)
                )
            )
            
            if mappings:
                await session.execute(
                    insert(question_co_mapping_table).values(mappings)
                )
            
            await session.commit()
            
            return {
                "success": True,
                "exam_id": exam_id,
                "mapping_count": len(mappings),
                "mappings": mappings
            }
        
        except Exception as e:
            self.logger.error("Question-CO mapping failed", error=str(e))
            await session.rollback()
            return {"success": False, "error": str(e)}
    
    async def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts using embeddings, with keyword fallback."""
        try:
            embedding1 = await embedding_service.embed_text(text1)
            embedding2 = await embedding_service.embed_text(text2)
            
            if not embedding1 or not embedding2:
                # embeddings unavailable — fall back to keyword similarity
                return self._keyword_similarity(text1, text2)
            
            dot_product = np.dot(embedding1, embedding2)
            magnitude1 = np.linalg.norm(embedding1)
            magnitude2 = np.linalg.norm(embedding2)
            
            if magnitude1 == 0 or magnitude2 == 0:
                return self._keyword_similarity(text1, text2)
            
            similarity = dot_product / (magnitude1 * magnitude2)
            return float(np.clip(similarity, 0, 1))
        
        except Exception as e:
            self.logger.error("Similarity calculation failed", error=str(e))
            return self._keyword_similarity(text1, text2)

    async def _combined_similarity(self, text1: str, text2: str) -> float:
        """Blend semantic and lexical signals with graceful fallback."""
        semantic_sim = await self._calculate_similarity(text1, text2)
        keyword_sim = self._keyword_similarity(text1, text2)

        if semantic_sim <= 0:
            return float(np.clip(keyword_sim, 0.0, 1.0))

        combined = (semantic_sim * 0.8) + (keyword_sim * 0.2)
        return float(np.clip(combined, 0.0, 1.0))

    def _select_dynamic_mappings(
        self,
        scored: List[Tuple[Any, float]],
        base_threshold: float,
    ) -> List[Tuple[Any, float]]:
        """
        Select mappings for one CO using adaptive logic:
        - keep candidates above adaptive cutoff near top score
        - cap to top-2 strongest links to reduce noisy over-mapping
        - if nothing passes but best score is reasonably close, keep top-1 fallback
        """
        if not scored:
            return []

        ranked = sorted(scored, key=lambda x: x[1], reverse=True)
        top_score = ranked[0][1]
        adaptive_cutoff = max(base_threshold, min(top_score * 0.85, top_score - 0.05))

        selected = [(obj, score) for obj, score in ranked if score >= adaptive_cutoff]
        selected = selected[:2]

        fallback_floor = max(base_threshold * 0.5, 0.12)
        if not selected and top_score >= fallback_floor:
            selected = [ranked[0]]

        return selected
    
    def _keyword_similarity(self, text1: str, text2: str) -> float:
        """Calculate lexical overlap similarity (token Jaccard) with stop-word filtering."""
        stop_words = {
            "the", "and", "for", "with", "to", "of", "in", "on", "a", "an", "is", "are",
            "be", "by", "using", "use", "from", "that", "this", "will", "can", "students",
        }

        def _norm(token: str) -> str:
            t = token.lower()
            for suffix in ("ing", "ed", "es", "s"):
                if len(t) > 4 and t.endswith(suffix):
                    return t[: -len(suffix)]
            return t

        t1 = {_norm(t) for t in re.findall(r"[a-zA-Z0-9]+", (text1 or "").lower()) if len(t) > 2 and t not in stop_words}
        t2 = {_norm(t) for t in re.findall(r"[a-zA-Z0-9]+", (text2 or "").lower()) if len(t) > 2 and t not in stop_words}

        if not t1 or not t2:
            return 0.0

        inter = len(t1 & t2)
        union = len(t1 | t2)
        min_len = min(len(t1), len(t2))
        if union == 0 or min_len == 0:
            return 0.0
        jaccard = inter / union
        overlap = inter / min_len
        # Blend broad overlap (jaccard) and focused overlap (coefficient).
        return float(np.clip((jaccard * 0.6) + (overlap * 0.4), 0.0, 1.0))
    
    async def get_mapping_statistics(
        self,
        session: AsyncSession,
        course_id: str
    ) -> Dict[str, Any]:
        """Get statistics about mappings"""
        try:
            # Count CO-PO mappings
            co_po_result = await session.execute(
                select(CourseOutcome).where(CourseOutcome.course_id == course_id)
            )
            cos = co_po_result.scalars().all()
            
            total_co_po = 0
            for co in cos:
                for po in co.program_outcomes:
                    total_co_po += 1
            
            # Count question mappings
            from sqlalchemy import func
            question_result = await session.execute(
                select(func.count()).select_from(question_co_mapping_table).join(
                    ExamQuestion,
                    question_co_mapping_table.c.question_id == ExamQuestion.id
                ).where(ExamQuestion.exam_id == course_id)
            )
            total_questions_mapped = question_result.scalar() or 0
            
            return {
                "course_id": course_id,
                "co_po_mappings": total_co_po,
                "question_mappings": total_questions_mapped,
                "total_cos": len(cos)
            }
        
        except Exception as e:
            self.logger.error("Error getting mapping statistics", error=str(e))
            return {}
