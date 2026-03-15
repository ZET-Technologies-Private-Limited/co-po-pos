"""
Service Orchestrator
Coordinates all microservices, LangGraph workflows, Rasa NLU, and infrastructure
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from app.core.infrastructure.redis_manager import redis_manager
from app.core.infrastructure.neo4j_manager import neo4j_manager
from app.core.infrastructure.microservices import (
    ServiceRegistry, RasaServiceClient, LangGraphServiceClient,
    AttainmentServiceClient, ReportServiceClient
)
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("service_orchestrator")

class ServiceOrchestrator:
    """Orchestrates all services and workflows"""
    
    def __init__(self):
        self.registry = ServiceRegistry()
        self.rasa_client = RasaServiceClient()
        self.langgraph_client = LangGraphServiceClient()
        self.attainment_client = AttainmentServiceClient()
        self.report_client = ReportServiceClient()
        self._initialized = False
    
    async def initialize(self):
        """Initialize all services"""
        if self._initialized:
            return
        
        try:
            # Initialize infrastructure
            await redis_manager.initialize()
            await neo4j_manager.initialize()
            
            # Check service health
            health_status = await self.registry.check_all_services()
            logger.info(f"Service health check: {health_status}")
            
            self._initialized = True
            logger.info("Service orchestrator initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPLETE CO GENERATION WORKFLOW
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def complete_co_generation_workflow(self, course_id: str, syllabus_text: str, 
                                            co_count: int = 5) -> Dict[str, Any]:
        """Complete CO generation workflow using all services"""
        try:
            logger.info(f"Starting complete CO generation for course {course_id}")
            
            # Step 1: Parse syllabus using LangGraph
            syllabus_result = await self.langgraph_client.parse_syllabus(course_id, syllabus_text)
            
            # Step 2: Generate COs using LangGraph
            co_generation_payload = {
                "course_id": course_id,
                "syllabus": syllabus_result.get("parsed_syllabus"),
                "num_cos": co_count
            }
            cos_result = await self.langgraph_client.generate_cos(co_generation_payload)
            
            # Step 3: Sync to Neo4j graph database
            await neo4j_manager.sync_from_postgresql(course_id)
            
            # Step 4: Cache results
            await redis_manager.set_co_library(
                course_code=cos_result.get("course_code", ""),
                regulation="2021",
                cos_data=cos_result.get("course_outcomes", [])
            )
            
            # Step 5: Publish event
            await redis_manager.publish_event("co.generated", {
                "course_id": course_id,
                "co_count": len(cos_result.get("course_outcomes", [])),
                "generated_at": datetime.utcnow().isoformat()
            })
            
            return {
                "status": "success",
                "course_id": course_id,
                "syllabus_analysis": syllabus_result,
                "generated_cos": cos_result,
                "workflow_completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"CO generation workflow failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "course_id": course_id
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPLETE ATTAINMENT CALCULATION WORKFLOW
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def complete_attainment_workflow(self, course_id: str, exam_id: str) -> Dict[str, Any]:
        """Complete attainment calculation workflow"""
        try:
            logger.info(f"Starting attainment calculation for course {course_id}, exam {exam_id}")
            
            # Step 1: Calculate CO attainment
            co_result = await self.attainment_client.calculate_co_attainment(course_id, exam_id)
            
            # Step 2: Calculate PO attainment using Neo4j traversal
            po_attainments = await neo4j_manager.get_all_po_attainments(
                dept_id="CSE", 
                ay_code="2024-25"
            )
            
            # Step 3: Cache results
            await redis_manager.set_po_attainment(
                dept_id="CSE",
                ay_id="2024-25", 
                attainment_data={
                    "co_attainments": co_result.get("attainments", []),
                    "po_attainments": po_attainments
                }
            )
            
            # Step 4: Check for Level 1 COs and notify
            level1_cos = [
                att for att in co_result.get("attainments", [])
                if att.get("attainment_level") == 1
            ]
            
            if level1_cos:
                for co_att in level1_cos:
                    await redis_manager.publish_level1_co_detected(
                        co_id=co_att["co_id"],
                        course_id=course_id,
                        user_ids=["faculty1@university.edu"]
                    )
            
            return {
                "status": "success",
                "course_id": course_id,
                "exam_id": exam_id,
                "co_attainments": co_result.get("attainments", []),
                "po_attainments": po_attainments,
                "level1_cos_detected": len(level1_cos),
                "workflow_completed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Attainment calculation workflow failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "course_id": course_id,
                "exam_id": exam_id
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHATBOT CONVERSATION WORKFLOW
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def handle_chatbot_conversation(self, message: str, user_id: str, 
                                        context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle complete chatbot conversation using Rasa + LangGraph"""
        try:
            # Step 1: Parse message with Rasa NLU
            rasa_result = await self.rasa_client.parse_message(message, user_id)
            
            intent = rasa_result.get("intent", {}).get("name")
            entities = rasa_result.get("entities", [])
            confidence = rasa_result.get("intent", {}).get("confidence", 0.0)
            
            logger.info(f"Rasa parsed - Intent: {intent}, Confidence: {confidence:.2f}")
            
            # Step 2: Route to appropriate LangGraph workflow based on intent
            if intent == "start_co_generation":
                course_id = next((e["value"] for e in entities if e["entity"] == "course_code"), None)
                if course_id:
                    workflow_result = await self.langgraph_client.generate_cos({
                        "course_id": course_id,
                        "trigger": "chatbot_request"
                    })
                    response_text = f"I'll help you generate COs for {course_id}. Please provide the syllabus."
                else:
                    response_text = "Which course would you like to generate COs for?"
            
            elif intent == "explain_attainment":
                co_number = next((e["value"] for e in entities if e["entity"] == "co_number"), None)
                course_id = context.get("course_id") if context else None
                
                if co_number and course_id:
                    explanation = await self.langgraph_client.explain_attainment(course_id, int(co_number))
                    response_text = explanation.get("explanation", "Unable to explain attainment.")
                else:
                    response_text = "Please specify which CO you'd like me to explain."
            
            elif intent == "analyse_question":
                question_text = next((e["value"] for e in entities if e["entity"] == "question_text"), None)
                course_id = context.get("course_id") if context else None
                
                if question_text and course_id:
                    analysis = await self.langgraph_client.analyze_question(question_text, course_id)
                    bt_level = analysis.get("bt_level", "Unknown")
                    suggested_co = analysis.get("suggested_co", "Unknown")
                    response_text = f"Question Analysis:\nBloom's Level: {bt_level}\nSuggested CO: {suggested_co}"
                else:
                    response_text = "Please provide the question text you'd like me to analyze."
            
            else:
                # Send to Rasa for conversation handling
                rasa_response = await self.rasa_client.send_message(message, user_id)
                response_text = rasa_response[0].get("text", "I didn't understand that.") if rasa_response else "Sorry, I'm having trouble responding."
            
            # Step 3: Cache conversation context
            await redis_manager.set_session(user_id, {
                "last_intent": intent,
                "last_entities": entities,
                "conversation_context": context or {},
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {
                "response": response_text,
                "intent": intent,
                "confidence": confidence,
                "entities": entities,
                "processed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Chatbot conversation failed: {e}")
            return {
                "response": "I'm sorry, I encountered an error. Please try again.",
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REPORT GENERATION WORKFLOW
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def generate_comprehensive_report(self, course_id: str, report_type: str, 
                                          user_id: str) -> Dict[str, Any]:
        """Generate comprehensive report using all data sources"""
        try:
            # Step 1: Get attainment summary
            attainment_summary = await self.attainment_client.get_attainment_summary(course_id)
            
            # Step 2: Get CO-PO matrix from Neo4j
            co_po_matrix = await neo4j_manager.get_co_po_correlation_matrix(course_id)
            
            # Step 3: Generate report via service
            report_result = await self.report_client.generate_report(course_id, report_type)
            
            # Step 4: Cache report job status
            job_id = report_result.get("job_id")
            if job_id:
                await redis_manager.set_report_job(job_id, {
                    "status": "processing",
                    "course_id": course_id,
                    "report_type": report_type,
                    "user_id": user_id,
                    "started_at": datetime.utcnow().isoformat()
                })
            
            return {
                "status": "success",
                "job_id": job_id,
                "report_type": report_type,
                "course_id": course_id,
                "estimated_completion": "5-10 minutes"
            }
            
        except Exception as e:
            logger.error(f"Report generation workflow failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "course_id": course_id
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH CHECK
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all services"""
        try:
            # Check all services
            service_health = await self.registry.check_all_services()
            
            # Check infrastructure
            redis_health = await redis_manager.health_check()
            neo4j_health = await neo4j_manager.health_check()
            
            # Overall status
            all_healthy = (
                all(service_health.values()) and
                redis_health.get("status") == "healthy" and
                neo4j_health.get("status") == "healthy"
            )
            
            return {
                "status": "healthy" if all_healthy else "degraded",
                "services": service_health,
                "infrastructure": {
                    "redis": redis_health,
                    "neo4j": neo4j_health
                },
                "checked_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Close all connections"""
        await redis_manager.close()
        await neo4j_manager.close()
        logger.info("Service orchestrator closed")

# Global orchestrator instance
orchestrator = ServiceOrchestrator()