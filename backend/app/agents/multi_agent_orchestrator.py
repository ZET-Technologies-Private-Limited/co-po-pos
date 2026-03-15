"""
LangGraph-based multi-agent orchestration system for CO-PO-PSO mapping
"""
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel
import json
import uuid
from app.ai_engine.llm.llm_client import llm_client
from app.modules.repositories.course_repository import CourseRepository
from app.modules.repositories.co_repository import CourseOutcomeRepository
from app.modules.repositories.exam_repository import ExamRepository, ExamQuestionRepository
from app.modules.mapping.services.semantic_mapping_service import SemanticMappingService
from app.modules.attainment_engine.analytics.attainment_calculator import AttainmentCalculator
from app.core.logging.system_logger import SystemLogger
from sqlalchemy.ext.asyncio import AsyncSession


# State models
class ConversationState(BaseModel):
    """State maintained across conversation"""
    conversation_id: str
    user_id: str
    course_id: Optional[str] = None
    current_agent: str
    messages: List[Dict[str, str]] = []
    context: Dict[str, Any] = {}
    last_updated: datetime = None
    
    class Config:
        arbitrary_types_allowed = True


class AgentMessage(BaseModel):
    """Message structure for agent communication"""
    agent_name: str
    action: str
    input_data: Dict[str, Any]
    timestamp: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.utcnow()


class COGenerationAgent:
    """Agent for generating course outcomes from syllabus"""
    
    def __init__(self):
        self.logger = SystemLogger("co_generation_agent")
        self.name = "COGenerationAgent"
    
    async def execute(
        self,
        session: AsyncSession,
        syllabus_text: str,
        course_code: str,
        course_name: str
    ) -> Dict[str, Any]:
        """Generate COs using AI"""
        try:
            self.logger.info(f"Executing CO generation for {course_code}")
            
            prompt = f"""Generate 4-6 measurable Course Outcomes (COs) for the following course:

Course Code: {course_code}
Course Name: {course_name}

Syllabus:
{syllabus_text}

Requirements:
1. Each CO must start with "Students will be able to..."
2. Assign a Bloom's Taxonomy level to each CO
3. Make them specific, measurable, and achievable
4. Cover main topics from syllabus

Format as JSON:
{{
    "outcomes": [
        {{
            "code": "CO1",
            "statement": "...",
            "bloom_level": "remember|understand|apply|analyze|evaluate|create"
        }}
    ]
}}"""
            
            response = await llm_client.generate_structured(prompt)
            
            if not response:
                return {"success": False, "error": "LLM failed to generate"}

            outcomes = response if isinstance(response, dict) else json.loads(response)
            self.logger.info(f"Generated {len(outcomes.get('outcomes', []))} COs")
            
            return {
                "success": True,
                "agent": self.name,
                "action": "generate_cos",
                "course_outcomes": outcomes['outcomes']
            }
        
        except Exception as e:
            self.logger.error(f"CO generation failed: {str(e)}")
            return {"success": False, "error": str(e)}


class BloomTaxonomyAgent:
    """Agent for detecting Bloom's taxonomy levels in questions"""
    
    def __init__(self):
        self.logger = SystemLogger("bloom_taxonomy_agent")
        self.name = "BloomTaxonomyAgent"
    
    async def execute(
        self,
        session: AsyncSession,
        question_text: str,
        exam_id: str
    ) -> Dict[str, Any]:
        """Detect Bloom's level for a question"""
        try:
            self.logger.info(f"Detecting Bloom level for question in exam {exam_id}")
            
            prompt = f"""Analyze this exam question and determine its Bloom's Taxonomy level.

Question: {question_text}

Classify it as one of: Remember, Understand, Apply, Analyze, Evaluate, Create

Explain your reasoning in 1-2 sentences.

Format as JSON:
{{
    "bloom_level": "...",
    "confidence": 0.0-1.0,
    "reasoning": "..."
}}"""
            
            response = await llm_client.generate_structured(prompt)
            
            if not response:
                return {"success": False, "error": "LLM failed"}

            result = response if isinstance(response, dict) else json.loads(response)
            
            return {
                "success": True,
                "agent": self.name,
                "action": "detect_bloom_level",
                "exam_id": exam_id,
                "bloom_level": result['bloom_level'],
                "confidence": result.get('confidence', 0.0),
                "reasoning": result.get('reasoning', '')
            }
        
        except Exception as e:
            self.logger.error(f"Bloom level detection failed: {str(e)}")
            return {"success": False, "error": str(e)}


class SemanticMappingAgent:
    """Agent for CO-PO/PSO mapping"""
    
    def __init__(self):
        self.logger = SystemLogger("semantic_mapping_agent")
        self.name = "SemanticMappingAgent"
        self.mapping_service = SemanticMappingService()
    
    async def execute(
        self,
        session: AsyncSession,
        course_id: str,
        program_id: str,
        mapping_type: Literal["CO-PO", "CO-PSO", "Question-CO"]
    ) -> Dict[str, Any]:
        """Perform semantic mapping"""
        try:
            self.logger.info(f"Executing {mapping_type} mapping for course {course_id}")
            
            if mapping_type == "CO-PO":
                result = await self.mapping_service.map_cos_to_pos(
                    session, course_id, program_id
                )
            elif mapping_type == "CO-PSO":
                result = await self.mapping_service.map_cos_to_psos(
                    session, course_id, program_id
                )
            elif mapping_type == "Question-CO":
                result = await self.mapping_service.map_questions_to_cos(
                    session, course_id, program_id
                )
            else:
                return {"success": False, "error": "Unknown mapping type"}
            
            return {
                "success": result.get("success", False),
                "agent": self.name,
                "action": f"map_{mapping_type.lower().replace('-', '_')}",
                **result
            }
        
        except Exception as e:
            self.logger.error(f"Mapping failed: {str(e)}")
            return {"success": False, "error": str(e)}


class AttainmentCalculationAgent:
    """Agent for calculating attainment"""
    
    def __init__(self):
        self.logger = SystemLogger("attainment_agent")
        self.name = "AttainmentCalculationAgent"
    
    async def execute(
        self,
        session: AsyncSession,
        course_id: str,
        exam_id: str
    ) -> Dict[str, Any]:
        """Calculate attainments for exam"""
        try:
            self.logger.info(f"Calculating attainments for exam {exam_id}")
            
            # Get COs
            co_repo = CourseOutcomeRepository()
            cos = await co_repo.get_by_course(session, course_id)
            
            attainments = []
            for co in cos:
                result = await AttainmentCalculator.calculate_co_attainment_db(
                    session, co.id, exam_id, course_id
                )
                if result:
                    await AttainmentCalculator.save_co_attainment(session, result)
                    attainments.append(result)
            
            await session.commit()
            
            return {
                "success": True,
                "agent": self.name,
                "action": "calculate_attainments",
                "exam_id": exam_id,
                "course_id": course_id,
                "attainments_calculated": len(attainments),
                "attainments": attainments
            }
        
        except Exception as e:
            self.logger.error(f"Attainment calculation failed: {str(e)}")
            await session.rollback()
            return {"success": False, "error": str(e)}


class ReportingAgent:
    """Agent for generating reports"""
    
    def __init__(self):
        self.logger = SystemLogger("reporting_agent")
        self.name = "ReportingAgent"
    
    async def execute(
        self,
        session: AsyncSession,
        course_id: str,
        report_type: Literal["comprehensive", "summary", "detailed"]
    ) -> Dict[str, Any]:
        """Generate reports"""
        try:
            self.logger.info(f"Generating {report_type} report for course {course_id}")
            
            report = await AttainmentCalculator.generate_comprehensive_report(
                session, course_id
            )
            
            if not report:
                return {"success": False, "error": "Failed to generate report"}
            
            return {
                "success": True,
                "agent": self.name,
                "action": "generate_report",
                "report_type": report_type,
                "report": report
            }
        
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return {"success": False, "error": str(e)}


class MultiAgentOrchestrator:
    """Orchestrates multi-agent workflow"""
    
    def __init__(self):
        self.logger = SystemLogger("multi_agent_orchestrator")
        
        # Initialize agents
        self.co_generation_agent = COGenerationAgent()
        self.bloom_taxonomy_agent = BloomTaxonomyAgent()
        self.semantic_mapping_agent = SemanticMappingAgent()
        self.attainment_agent = AttainmentCalculationAgent()
        self.reporting_agent = ReportingAgent()
        
        # Agent registry
        self.agents = {
            "co_generation": self.co_generation_agent,
            "bloom_taxonomy": self.bloom_taxonomy_agent,
            "semantic_mapping": self.semantic_mapping_agent,
            "attainment": self.attainment_agent,
            "reporting": self.reporting_agent
        }
    
    async def process_conversation(
        self,
        session: AsyncSession,
        user_query: str,
        state: ConversationState
    ) -> Dict[str, Any]:
        """Process user query through appropriate agent(s)"""
        try:
            self.logger.info(f"Processing query: {user_query[:100]}...")
            
            # Determine intent and route to appropriate agent
            intent = await self._detect_intent(user_query)
            
            self.logger.info(f"Detected intent: {intent}")
            
            result = None
            
            if "generate_co" in intent:
                result = await self.co_generation_agent.execute(
                    session, 
                    state.context.get("syllabus", ""),
                    state.context.get("course_code", ""),
                    state.context.get("course_name", "")
                )
            
            elif "detect_bloom" in intent:
                result = await self.bloom_taxonomy_agent.execute(
                    session,
                    state.context.get("question_text", ""),
                    state.context.get("exam_id", "")
                )
            
            elif "map" in intent:
                mapping_type = self._extract_mapping_type(user_query)
                result = await self.semantic_mapping_agent.execute(
                    session,
                    state.course_id or "",
                    state.context.get("program_id", ""),
                    mapping_type
                )
            
            elif "attainment" in intent or "calculate" in intent:
                result = await self.attainment_agent.execute(
                    session,
                    state.course_id or "",
                    state.context.get("exam_id", "")
                )
            
            elif "report" in intent:
                result = await self.reporting_agent.execute(
                    session,
                    state.course_id or "",
                    "comprehensive"
                )
            
            if result:
                # Update state
                state.messages.append({
                    "role": "assistant",
                    "content": str(result),
                    "timestamp": datetime.utcnow().isoformat()
                })
                state.last_updated = datetime.utcnow()
                
                return {
                    "success": result.get("success", False),
                    "agent_response": result,
                    "state": state
                }
            
            return {
                "success": False,
                "error": "No matching agent for query"
            }
        
        except Exception as e:
            self.logger.error(f"Orchestration failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _detect_intent(self, query: str) -> List[str]:
        """Detect user intent from query"""
        query_lower = query.lower()
        intents = []
        
        if any(word in query_lower for word in ["generate", "create", "create co"]):
            intents.append("generate_co")
        
        if any(word in query_lower for word in ["bloom", "taxonomy", "level", "detect"]):
            intents.append("detect_bloom")
        
        if any(word in query_lower for word in ["map", "mapping", "associate"]):
            intents.append("map")
        
        if any(word in query_lower for word in ["attainment", "calculate", "assess"]):
            intents.append("attainment")
        
        if any(word in query_lower for word in ["report", "summary", "analytics"]):
            intents.append("report")
        
        return intents if intents else ["general"]
    
    def _extract_mapping_type(self, query: str) -> str:
        """Extract mapping type from query"""
        query_lower = query.lower()
        
        if "pso" in query_lower or "specific outcome" in query_lower:
            return "CO-PSO"
        elif "program outcome" in query_lower or "po" in query_lower:
            return "CO-PO"
        elif "question" in query_lower:
            return "Question-CO"
        
        return "CO-PO"  # Default
