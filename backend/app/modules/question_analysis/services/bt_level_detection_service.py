"""
Bloom's Taxonomy level detection for exam questions
"""
from typing import Dict, List, Optional, Tuple
import re
from app.ai_engine.llm.llm_client import llm_client
from app.ai_engine.embeddings.embedding_service import embedding_service
from app.core.config.constants import BloomTaxonomyLevel, BLOOM_KEYWORDS
from app.core.logging.system_logger import SystemLogger


class BTLevelDetectionService:
    """Detect Bloom's Taxonomy level of exam questions"""
    
    def __init__(self):
        self.logger = SystemLogger("bt_detection")
        self.bloom_keywords = BLOOM_KEYWORDS
    
    async def detect_question_bloom_level(
        self,
        question_text: str,
        question_type: str = None
    ) -> Dict[str, any]:
        """
        Detect Bloom's Taxonomy level for a question using multiple strategies:
        1. Keyword matching
        2. AI-based analysis
        3. Semantic analysis
        """
        try:
            self.logger.info(
                "Detecting Bloom level",
                question_type=question_type
            )
            
            # Strategy 1: Keyword matching
            keyword_level, keyword_confidence = await self._keyword_based_detection(question_text)
            
            # Strategy 2: AI analysis
            ai_level, ai_confidence = await self._ai_based_detection(question_text)
            
            # Combine results
            final_level, confidence = self._combine_results(
                keyword_level, keyword_confidence,
                ai_level, ai_confidence
            )
            
            return {
                "bloom_level": final_level,
                "confidence": confidence,
                "keyword_level": keyword_level,
                "keyword_confidence": keyword_confidence,
                "ai_level": ai_level,
                "ai_confidence": ai_confidence
            }
        
        except Exception as e:
            self.logger.error("Bloom level detection failed", error=str(e))
            return {
                "bloom_level": BloomTaxonomyLevel.UNDERSTAND.value,
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _keyword_based_detection(
        self,
        question_text: str
    ) -> Tuple[str, float]:
        """Keyword-based Bloom level detection"""
        question_lower = question_text.lower()
        scores = {}
        
        for level, keywords in self.bloom_keywords.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            scores[level] = score
        
        if max(scores.values()) == 0:
            return BloomTaxonomyLevel.UNDERSTAND.value, 0.5
        
        best_level = max(scores, key=scores.get)
        confidence = scores[best_level] / max(sum(scores.values()), 1)
        
        return best_level.value, round(confidence, 3)
    
    async def _ai_based_detection(
        self,
        question_text: str
    ) -> Tuple[str, float]:
        """AI-based Bloom level detection using LLM"""
        prompt = f"""Analyze this exam question and determine its Bloom's Taxonomy level.

Question: {question_text}

Possible levels: Remember, Understand, Apply, Analyze, Evaluate, Create

Consider:
- Action verbs used
- Complexity of cognitive skill required
- Type of answer expected

Respond with: {{"level": "...", "confidence": 0-1, "reasoning": "..."}}"""
        
        result = await llm_client.extract_json(
            prompt,
            system_prompt="You are an expert in curriculum design and Bloom's Taxonomy. Determine the cognitive level required to answer questions."
        )
        
        if result:
            level = result.get("level", "").lower()
            confidence = result.get("confidence", 0.5)
            
            # Normalize level name
            for bloom_level in BloomTaxonomyLevel:
                if bloom_level.value.lower() == level:
                    return bloom_level.value, confidence
            
            return BloomTaxonomyLevel.UNDERSTAND.value, 0.3
        
        return BloomTaxonomyLevel.UNDERSTAND.value, 0.0
    
    def _combine_results(
        self,
        keyword_level: str,
        keyword_conf: float,
        ai_level: str,
        ai_conf: float
    ) -> Tuple[str, float]:
        """Combine keyword and AI results"""
        if keyword_level == ai_level:
            # Agreement increases confidence
            combined_confidence = (keyword_conf + ai_conf) / 2 * 1.1
            return keyword_level, min(combined_confidence, 1.0)
        
        # Disagreement: weight by confidence
        if keyword_conf > ai_conf:
            return keyword_level, (keyword_conf + ai_conf * 0.5) / 1.5
        else:
            return ai_level, (ai_conf + keyword_conf * 0.5) / 1.5
    
    async def batch_detect_bloom_levels(
        self,
        questions: List[Dict[str, str]]
    ) -> List[Dict[str, any]]:
        """Detect Bloom levels for multiple questions"""
        results = []
        
        for question in questions:
            result = await self.detect_question_bloom_level(
                question.get("text", ""),
                question.get("type")
            )
            results.append({
                "question_id": question.get("id"),
                **result
            })
        
        return results


# Global service instance
bt_detection_service = BTLevelDetectionService()


class BloomsTaxonomyDetector(BTLevelDetectionService):
    """Backward-compatible alias for older imports."""

    pass
