"""
Microservices Architecture Implementation
Separates monolithic FastAPI into microservices
"""
from fastapi import FastAPI, Depends, HTTPException
from typing import Dict, Any, List
import httpx
import asyncio
from app.core.logging.system_logger import SystemLogger

logger = SystemLogger("microservices")

# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class ServiceRegistry:
    """Service discovery and health checking"""
    
    def __init__(self):
        self.services = {
            "auth-service": "http://localhost:8001",
            "rasa-server": "http://localhost:5005",
            "action-server": "http://localhost:5055",
            "langgraph-engine": "http://localhost:8002",
            "fastapi-core": "http://localhost:8000",
            "attainment-service": "http://localhost:8003",
            "report-service": "http://localhost:8004",
            "file-service": "http://localhost:8005",
            "notification-service": "http://localhost:8006"
        }
        self.health_status = {}
    
    async def get_service_url(self, service_name: str) -> str:
        """Get service URL with health check"""
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")
        
        url = self.services[service_name]
        
        # Check health if not recently checked
        if service_name not in self.health_status:
            await self.check_service_health(service_name)
        
        return url
    
    async def check_service_health(self, service_name: str) -> bool:
        """Check if service is healthy"""
        try:
            url = self.services[service_name]
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/health")
                healthy = response.status_code == 200
                self.health_status[service_name] = healthy
                return healthy
        except Exception as e:
            logger.warning(f"Health check failed for {service_name}: {e}")
            self.health_status[service_name] = False
            return False
    
    async def check_all_services(self) -> Dict[str, bool]:
        """Check health of all services"""
        tasks = [
            self.check_service_health(service_name) 
            for service_name in self.services.keys()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            service_name: result if isinstance(result, bool) else False
            for service_name, result in zip(self.services.keys(), results)
        }

service_registry = ServiceRegistry()

# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE CLIENTS
# ═══════════════════════════════════════════════════════════════════════════════

class ServiceClient:
    """Base class for service communication"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.registry = service_registry
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get HTTP client with service URL"""
        base_url = await self.registry.get_service_url(self.service_name)
        return httpx.AsyncClient(base_url=base_url, timeout=30.0)
    
    async def call_service(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make service call with error handling"""
        try:
            async with await self.get_client() as client:
                response = await client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Service call failed: {self.service_name}{endpoint} - {e}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            logger.error(f"Service communication error: {self.service_name} - {e}")
            raise HTTPException(status_code=503, detail=f"Service {self.service_name} unavailable")

class AuthServiceClient(ServiceClient):
    """Authentication service client"""
    
    def __init__(self):
        super().__init__("auth-service")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token"""
        return await self.call_service(
            "POST", "/validate-token",
            json={"token": token}
        )
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions"""
        result = await self.call_service("GET", f"/users/{user_id}/permissions")
        return result.get("permissions", [])

class RasaServiceClient(ServiceClient):
    """Rasa NLU service client"""
    
    def __init__(self):
        super().__init__("rasa-server")
    
    async def parse_message(self, message: str, sender_id: str = "default") -> Dict[str, Any]:
        """Parse message with Rasa NLU"""
        return await self.call_service(
            "POST", "/model/parse",
            json={"text": message, "message_id": sender_id}
        )
    
    async def send_message(self, message: str, sender_id: str) -> Dict[str, Any]:
        """Send message to Rasa and get response"""
        return await self.call_service(
            "POST", f"/webhooks/rest/webhook",
            json={"sender": sender_id, "message": message}
        )

class LangGraphServiceClient(ServiceClient):
    """LangGraph workflow engine client"""
    
    def __init__(self):
        super().__init__("langgraph-engine")
    
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LangGraph workflow"""
        return await self.call_service(
            "POST", f"/workflows/{workflow_name}",
            json=input_data
        )
    
    async def parse_syllabus(self, course_id: str, syllabus_text: str) -> Dict[str, Any]:
        """Parse syllabus workflow"""
        return await self.execute_workflow("parse_syllabus", {
            "course_id": course_id,
            "syllabus_text": syllabus_text
        })
    
    async def generate_cos(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate COs workflow"""
        return await self.execute_workflow("generate_cos", payload)
    
    async def analyze_question(self, question_text: str, course_id: str) -> Dict[str, Any]:
        """Analyze question workflow"""
        return await self.execute_workflow("analyze_question", {
            "question_text": question_text,
            "course_id": course_id
        })
    
    async def explain_attainment(self, course_id: str, co_number: int) -> Dict[str, Any]:
        """Explain attainment workflow"""
        return await self.execute_workflow("explain_attainment", {
            "course_id": course_id,
            "co_number": co_number
        })

class AttainmentServiceClient(ServiceClient):
    """Attainment calculation service client"""
    
    def __init__(self):
        super().__init__("attainment-service")
    
    async def calculate_co_attainment(self, course_id: str, exam_id: str, threshold_pct: float = 0.60) -> Dict[str, Any]:
        """Calculate CO attainment"""
        return await self.call_service(
            "POST", "/calculate-co",
            json={
                "course_id": course_id,
                "exam_id": exam_id,
                "threshold_pct": threshold_pct
            }
        )
    
    async def calculate_po_attainment(self, course_id: str, program_id: str) -> Dict[str, Any]:
        """Calculate PO attainment"""
        return await self.call_service(
            "POST", "/calculate-po",
            json={
                "course_id": course_id,
                "program_id": program_id
            }
        )
    
    async def get_attainment_summary(self, course_id: str) -> Dict[str, Any]:
        """Get attainment summary"""
        return await self.call_service("GET", f"/summary/{course_id}")

class ReportServiceClient(ServiceClient):
    """Report generation service client"""
    
    def __init__(self):
        super().__init__("report-service")
    
    async def generate_report(self, course_id: str, report_type: str, format: str = "pdf") -> Dict[str, Any]:
        """Generate report"""
        return await self.call_service(
            "POST", "/generate",
            json={
                "course_id": course_id,
                "report_type": report_type,
                "format": format
            }
        )
    
    async def get_report_status(self, job_id: str) -> Dict[str, Any]:
        """Get report generation status"""
        return await self.call_service("GET", f"/status/{job_id}")

class FileServiceClient(ServiceClient):
    """File processing service client"""
    
    def __init__(self):
        super().__init__("file-service")
    
    async def upload_marks_file(self, exam_id: str, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Upload and process marks file"""
        return await self.call_service(
            "POST", f"/upload-marks/{exam_id}",
            files={"file": (filename, file_content)},
            data={"filename": filename}
        )
    
    async def get_upload_status(self, job_id: str) -> Dict[str, Any]:
        """Get file upload processing status"""
        return await self.call_service("GET", f"/upload-status/{job_id}")

class NotificationServiceClient(ServiceClient):
    """Notification service client"""
    
    def __init__(self):
        super().__init__("notification-service")
    
    async def send_notification(self, user_id: str, message: str, notification_type: str = "info") -> Dict[str, Any]:
        """Send in-app notification"""
        return await self.call_service(
            "POST", "/send",
            json={
                "user_id": user_id,
                "message": message,
                "type": notification_type
            }
        )
    
    async def send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email notification"""
        return await self.call_service(
            "POST", "/send-email",
            json={
                "to_email": to_email,
                "subject": subject,
                "body": body
            }
        )

# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

auth_service = AuthServiceClient()
rasa_service = RasaServiceClient()
langgraph_service = LangGraphServiceClient()
attainment_service = AttainmentServiceClient()
report_service = ReportServiceClient()
file_service = FileServiceClient()
notification_service = NotificationServiceClient()

# ═══════════════════════════════════════════════════════════════════════════════
# API GATEWAY FUNCTIONALITY
# ═══════════════════════════════════════════════════════════════════════════════

class APIGateway:
    """API Gateway for routing and load balancing"""
    
    def __init__(self):
        self.registry = service_registry
        self.rate_limits = {}
    
    async def route_request(self, service_name: str, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Route request to appropriate service"""
        # Check rate limiting
        client_ip = kwargs.get('client_ip', 'unknown')
        if not await self.check_rate_limit(client_ip, endpoint):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Route to service
        client_class = {
            "auth": AuthServiceClient,
            "rasa": RasaServiceClient,
            "langgraph": LangGraphServiceClient,
            "attainment": AttainmentServiceClient,
            "report": ReportServiceClient,
            "file": FileServiceClient,
            "notification": NotificationServiceClient
        }.get(service_name)
        
        if not client_class:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        
        client = client_class()
        return await client.call_service(method, endpoint, **kwargs)
    
    async def check_rate_limit(self, client_ip: str, endpoint: str, limit: int = 100, window: int = 60) -> bool:
        """Check rate limiting"""
        from app.core.infrastructure.redis_manager import redis_manager
        return await redis_manager.check_rate_limit(client_ip, endpoint, limit, window)
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Health check all services"""
        health_status = await self.registry.check_all_services()
        
        overall_health = "healthy" if all(health_status.values()) else "degraded"
        
        return {
            "status": overall_health,
            "services": health_status,
            "timestamp": "2024-03-14T12:00:00Z"
        }

api_gateway = APIGateway()

# ═══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER PATTERN
# ═══════════════════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """Circuit breaker for service resilience"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = {}
        self.last_failure_time = {}
        self.state = {}  # 'closed', 'open', 'half-open'
    
    async def call_with_circuit_breaker(self, service_name: str, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        current_state = self.state.get(service_name, 'closed')
        
        if current_state == 'open':
            # Check if recovery timeout has passed
            last_failure = self.last_failure_time.get(service_name, 0)
            if (datetime.utcnow().timestamp() - last_failure) > self.recovery_timeout:
                self.state[service_name] = 'half-open'
            else:
                raise HTTPException(status_code=503, detail=f"Service {service_name} circuit breaker open")
        
        try:
            result = await func(*args, **kwargs)
            
            # Reset on success
            if current_state == 'half-open':
                self.state[service_name] = 'closed'
                self.failure_count[service_name] = 0
            
            return result
            
        except Exception as e:
            # Increment failure count
            self.failure_count[service_name] = self.failure_count.get(service_name, 0) + 1
            self.last_failure_time[service_name] = datetime.utcnow().timestamp()
            
            # Open circuit if threshold exceeded
            if self.failure_count[service_name] >= self.failure_threshold:
                self.state[service_name] = 'open'
                logger.warning(f"Circuit breaker opened for {service_name}")
            
            raise

circuit_breaker = CircuitBreaker()

# ═══════════════════════════════════════════════════════════════════════════════
# SERVICE MESH COMMUNICATION
# ═══════════════════════════════════════════════════════════════════════════════

async def call_service_with_resilience(service_name: str, func, *args, **kwargs):
    """Call service with circuit breaker and retry logic"""
    return await circuit_breaker.call_with_circuit_breaker(service_name, func, *args, **kwargs)