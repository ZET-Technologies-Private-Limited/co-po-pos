"""
Service router for request routing to appropriate modules
"""
from typing import Dict, Any, Optional, Callable
from enum import Enum
from app.core.logging.system_logger import SystemLogger


class ServiceType(str, Enum):
    """Available service types"""
    AUTHENTICATION = "authentication"
    COURSE_MANAGEMENT = "course_management"
    CO_GENERATION = "co_generation"
    CO_PO_MAPPING = "co_po_mapping"
    EXAM_MANAGEMENT = "exam_management"
    QUESTION_ANALYSIS = "question_analysis"
    MARKS_PROCESSING = "marks_processing"
    ATTAINMENT_ENGINE = "attainment_engine"
    REPORTING = "reporting"


class ServiceRouter:
    """Routes service requests to appropriate modules"""
    
    def __init__(self):
        self.logger = SystemLogger("router")
        self.services: Dict[ServiceType, Dict[str, Callable]] = {}
    
    def register_service(
        self,
        service_type: ServiceType,
        operations: Dict[str, Callable]
    ):
        """Register service with its operations"""
        self.services[service_type] = operations
        self.logger.info(
            "Service registered",
            service_type=service_type.value,
            operations=list(operations.keys())
        )
    
    async def route_request(
        self,
        service_type: ServiceType,
        operation: str,
        **kwargs
    ) -> Optional[Any]:
        """Route request to appropriate service operation"""
        if service_type not in self.services:
            self.logger.error(
                "Service not found",
                service_type=service_type.value
            )
            return None
        
        service_ops = self.services[service_type]
        
        if operation not in service_ops:
            self.logger.error(
                "Operation not found",
                service_type=service_type.value,
                operation=operation
            )
            return None
        
        try:
            handler = service_ops[operation]
            result = await handler(**kwargs) if hasattr(handler, '__await__') else handler(**kwargs)
            
            self.logger.info(
                "Request processed",
                service_type=service_type.value,
                operation=operation
            )
            
            return result
        
        except Exception as e:
            self.logger.error(
                "Request failed",
                service_type=service_type.value,
                operation=operation,
                error=str(e)
            )
            raise
    
    def get_available_services(self) -> Dict[str, list]:
        """Get list of available services and operations"""
        return {
            service_type.value: list(ops.keys())
            for service_type, ops in self.services.items()
        }


# Global router instance
service_router = ServiceRouter()
