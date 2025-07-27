"""
AI4AI Agents Package
Advanced educational AI agents with Google ADK integration
"""

from .planner_agent import (
    PlannerAgent, 
    PlannerRequest, 
    PlannerResponse, 
    planner_agent, 
    planner_app,
    handle_plan
)

from .content_agent import (
    ContentAgent,
    ContentRequest,
    ContentResponse,
    content_agent,
    content_app,
    handle_content
)

from .assessment_agent import (
    AssessmentAgent,
    AssessmentRequest,
    AssessmentResponse,
    assessment_agent,
    assessment_app,
    handle_assessment
)

from .visual_aid_agent import (
    VisualAidAgent,
    VisualAidRequest,
    VisualAidResponse,
    visual_aid_agent,
    visual_aid_app,
    handle_visual_aid
)

from .orchestrator_agent import (
    OrchestratorAgent,
    OrchestrationRequest,
    OrchestrationResponse,
    orchestrator_agent,
    orchestrator_app,
    handle_orchestration
)

__all__ = [
    # Planner Agent
    "PlannerAgent", "PlannerRequest", "PlannerResponse", 
    "planner_agent", "planner_app", "handle_plan",
    
    # Content Agent
    "ContentAgent", "ContentRequest", "ContentResponse",
    "content_agent", "content_app", "handle_content",
    
    # Assessment Agent
    "AssessmentAgent", "AssessmentRequest", "AssessmentResponse",
    "assessment_agent", "assessment_app", "handle_assessment",
    
    # Visual Aid Agent
    "VisualAidAgent", "VisualAidRequest", "VisualAidResponse",
    "visual_aid_agent", "visual_aid_app", "handle_visual_aid",
    
    # Orchestrator Agent
    "OrchestratorAgent", "OrchestrationRequest", "OrchestrationResponse",
    "orchestrator_agent", "orchestrator_app", "handle_orchestration"
]

# Version info
__version__ = "3.0.0"
__author__ = "AI4AI Team"
__description__ = "Advanced educational AI agents with Google ADK integration"

# Agent registry for easy access
AGENTS = {
    "planner": planner_agent,
    "content": content_agent,
    "assessment": assessment_agent,
    "visual_aid": visual_aid_agent,
    "orchestrator": orchestrator_agent
}

# ADK Apps registry
ADK_APPS = {
    "planner": planner_app,
    "content": content_app,
    "assessment": assessment_app,
    "visual_aid": visual_aid_app,
    "orchestrator": orchestrator_app
}

def get_agent(agent_name: str):
    """Get an agent instance by name"""
    return AGENTS.get(agent_name)

def get_adk_app(agent_name: str):
    """Get an ADK app instance by name"""
    return ADK_APPS.get(agent_name)

def list_agents():
    """List all available agents"""
    return list(AGENTS.keys())
