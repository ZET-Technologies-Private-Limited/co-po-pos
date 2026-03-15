"""
LangGraph-based workflow management for AI agent orchestration
"""
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
from app.core.logging.system_logger import SystemLogger


class AgentType(str, Enum):
    """Types of AI agents in the workflow"""
    CO_GENERATION = "co_generation"
    MAPPING = "mapping"
    EXAM_ANALYSIS = "exam_analysis"
    QUESTION_CLASSIFICATION = "question_classification"
    ATTAINMENT_CALCULATION = "attainment_calculation"
    REPORTING = "reporting"


@dataclass
class AgentNode:
    """Node in the workflow graph"""
    agent_type: AgentType
    name: str
    handler: Callable
    dependencies: List[str] = None


class LangGraphWorkflowManager:
    """Manages LangGraph-based AI workflows"""
    
    def __init__(self):
        self.logger = SystemLogger("workflow_manager")
        self.workflow_graph: Dict[str, AgentNode] = {}
        self.execution_order: List[str] = []
    
    def register_agent(
        self,
        agent_type: AgentType,
        name: str,
        handler: Callable,
        dependencies: List[str] = None
    ):
        """Register an AI agent in the workflow"""
        node = AgentNode(
            agent_type=agent_type,
            name=name,
            handler=handler,
            dependencies=dependencies or []
        )
        
        self.workflow_graph[name] = node
        self.logger.info(
            "Agent registered",
            agent_type=agent_type.value,
            agent_name=name,
            dependencies=dependencies or []
        )
    
    async def execute_workflow(
        self,
        workflow_data: Dict[str, Any],
        start_node: str = None
    ) -> Dict[str, Any]:
        """Execute the workflow graph"""
        execution_result = {
            "workflow_data": workflow_data,
            "agent_outputs": {},
            "errors": []
        }
        
        # Determine execution order using topological sort
        order = self._topological_sort(start_node)
        
        if not order:
            self.logger.error("No executable nodes found in workflow")
            return execution_result
        
        # Execute agents in order
        for node_name in order:
            node = self.workflow_graph.get(node_name)
            
            if not node:
                continue
            
            try:
                self.logger.info(f"Executing agent: {node.agent_type.value}")
                
                result = await node.handler(workflow_data)
                execution_result["agent_outputs"][node_name] = result
                workflow_data.update(result)
                
                self.logger.info(
                    "Agent completed",
                    agent=node_name,
                    agent_type=node.agent_type.value
                )
            
            except Exception as e:
                self.logger.error(
                    "Agent execution failed",
                    agent=node_name,
                    error=str(e)
                )
                execution_result["errors"].append({
                    "agent": node_name,
                    "error": str(e)
                })
        
        return execution_result
    
    def _topological_sort(self, start_node: str = None) -> List[str]:
        """Topological sort of workflow graph"""
        visited = set()
        stack = []
        
        if start_node:
            if start_node in self.workflow_graph:
                self._dfs(start_node, visited, stack)
        else:
            # Start from all nodes with no dependencies
            for node_name, node in self.workflow_graph.items():
                if not node.dependencies and node_name not in visited:
                    self._dfs(node_name, visited, stack)
        
        return stack
    
    def _dfs(self, node: str, visited: set, stack: list):
        """Depth-first search for topological sort"""
        visited.add(node)
        
        # Visit all dependencies first
        if node in self.workflow_graph:
            for dep in self.workflow_graph[node].dependencies:
                if dep not in visited:
                    self._dfs(dep, visited, stack)
        
        stack.append(node)
    
    def get_workflow_structure(self) -> Dict[str, Any]:
        """Get the workflow graph structure"""
        return {
            node_name: {
                "agent_type": node.agent_type.value,
                "dependencies": node.dependencies
            }
            for node_name, node in self.workflow_graph.items()
        }


# Global workflow manager instance
workflow_manager = LangGraphWorkflowManager()
