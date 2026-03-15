"""
Central orchestrator for academic workflow coordination
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from app.core.logging.system_logger import SystemLogger


class WorkflowState(str, Enum):
    """Workflow execution states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowContext:
    """Context for workflow execution"""
    workflow_id: str
    state: WorkflowState
    current_step: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[str] = None


class AcademicWorkflowOrchestrator:
    """Orchestrates academic workflows across all modules"""
    
    def __init__(self):
        self.logger = SystemLogger("orchestrator")
        self.workflows: Dict[str, WorkflowContext] = {}
    
    async def start_workflow(
        self,
        workflow_id: str,
        initial_data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> WorkflowContext:
        """Start a new workflow"""
        context = WorkflowContext(
            workflow_id=workflow_id,
            state=WorkflowState.PENDING,
            current_step="initialization",
            data=initial_data,
            metadata=metadata or {},
            start_time=datetime.utcnow(),
        )
        
        self.workflows[workflow_id] = context
        self.logger.info(
            "Workflow started",
            workflow_id=workflow_id,
            step="initialization"
        )
        
        return context
    
    async def update_workflow_state(
        self,
        workflow_id: str,
        new_state: WorkflowState,
        step: str,
        data_update: Dict[str, Any] = None
    ) -> Optional[WorkflowContext]:
        """Update workflow state and progress"""
        if workflow_id not in self.workflows:
            self.logger.error(
                "Workflow not found",
                workflow_id=workflow_id
            )
            return None
        
        context = self.workflows[workflow_id]
        context.state = new_state
        context.current_step = step
        
        if data_update:
            context.data.update(data_update)
        
        self.logger.info(
            "Workflow state updated",
            workflow_id=workflow_id,
            state=new_state.value,
            step=step
        )
        
        return context
    
    async def complete_workflow(
        self,
        workflow_id: str,
        final_data: Dict[str, Any] = None
    ) -> Optional[WorkflowContext]:
        """Mark workflow as completed"""
        if workflow_id not in self.workflows:
            return None
        
        context = self.workflows[workflow_id]
        context.state = WorkflowState.COMPLETED
        context.end_time = datetime.utcnow()
        
        if final_data:
            context.data.update(final_data)
        
        duration = (context.end_time - context.start_time).total_seconds()
        self.logger.info(
            "Workflow completed",
            workflow_id=workflow_id,
            duration_seconds=duration
        )
        
        return context
    
    async def fail_workflow(
        self,
        workflow_id: str,
        error: str
    ) -> Optional[WorkflowContext]:
        """Mark workflow as failed"""
        if workflow_id not in self.workflows:
            return None
        
        context = self.workflows[workflow_id]
        context.state = WorkflowState.FAILED
        context.error = error
        context.end_time = datetime.utcnow()
        
        self.logger.error(
            "Workflow failed",
            workflow_id=workflow_id,
            error=error
        )
        
        return context
    
    def get_workflow_context(self, workflow_id: str) -> Optional[WorkflowContext]:
        """Get workflow context by ID"""
        return self.workflows.get(workflow_id)
    
    def get_active_workflows(self) -> Dict[str, WorkflowContext]:
        """Get all active workflows"""
        return {
            wid: ctx for wid, ctx in self.workflows.items()
            if ctx.state == WorkflowState.IN_PROGRESS
        }


# Global orchestrator instance
orchestrator = AcademicWorkflowOrchestrator()
