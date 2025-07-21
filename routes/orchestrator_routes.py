# routes/orchestrator_routes.py
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, Optional
from orchestrator.lesson_pipeline import (
    run_pipeline, 
    run_complete_pipeline,
    LessonPipelineRequest,
    LessonPipelineResponse,
    LessonPipeline
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agentic", tags=["Orchestration"])

@router.post("/orchestrate", response_model=Dict[str, Any])
async def orchestrate_agentic_flow(payload: dict):
    """
    Legacy orchestration endpoint for backward compatibility
    Orchestrates Planner → Content → Assessment agents
    """
    try:
        result = await run_pipeline(payload)
        return {"status": "success", "pipeline_result": result}
    except Exception as e:
        logger.error(f"Legacy orchestration error: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.post("/lesson/complete", response_model=LessonPipelineResponse)
async def create_complete_lesson(request: LessonPipelineRequest):
    """
    Create a complete lesson with all components:
    - Lesson Plan (Planner Agent)
    - Educational Content (Content Agent) 
    - Assessment Materials (Assessment Agent)
    - Visual Aids (Visual Aid Agent)
    """
    try:
        pipeline = LessonPipeline()
        result = await pipeline.execute_complete_pipeline(request.dict())
        
        return LessonPipelineResponse(**result)
        
    except Exception as e:
        logger.error(f"Complete lesson creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create complete lesson: {str(e)}"
        )

@router.post("/lesson/plan-only", response_model=Dict[str, Any])
async def create_lesson_plan_only(
    teacher_id: str,
    class_id: str, 
    topic: str,
    grade_level: str = "elementary",
    duration: int = 60,
    curriculum_standards: Optional[list] = None,
    learning_objectives: Optional[list] = None
):
    """
    Create only a lesson plan using the Planner Agent
    """
    try:
        pipeline = LessonPipeline()
        
        request_data = {
            "teacher_id": teacher_id,
            "class_id": class_id,
            "topic": topic,
            "grade_level": grade_level,
            "duration": duration,
            "lesson_type": "planning_only",
            "curriculum_standards": curriculum_standards or [],
            "learning_objectives": learning_objectives or []
        }
        
        result = await pipeline.execute_planning_step(request_data)
        
        return {
            "status": "success",
            "lesson_plan": result,
            "metadata": {
                "pipeline_type": "planning_only",
                "execution_time": "calculated_at_runtime"
            }
        }
        
    except Exception as e:
        logger.error(f"Lesson planning error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lesson plan: {str(e)}"
        )

@router.post("/content/generate", response_model=Dict[str, Any])
async def generate_content_only(
    topic: str,
    grade_level: str = "elementary",
    content_type: str = "comprehensive",
    learning_objectives: Optional[list] = None,
    existing_plan: Optional[Dict[str, Any]] = None
):
    """
    Generate educational content using the Content Agent
    """
    try:
        pipeline = LessonPipeline()
        
        request_data = {
            "topic": topic,
            "grade_level": grade_level,
            "lesson_type": "content_only",
            "content_preferences": {
                "content_type": content_type,
                "include_multimedia": True,
                "interactive_elements": True
            },
            "learning_objectives": learning_objectives or [],
            "existing_lesson_plan": existing_plan
        }
        
        result = await pipeline.execute_content_step(request_data)
        
        return {
            "status": "success", 
            "content": result,
            "metadata": {
                "pipeline_type": "content_only",
                "content_type": content_type
            }
        }
        
    except Exception as e:
        logger.error(f"Content generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate content: {str(e)}"
        )

@router.post("/assessment/create", response_model=Dict[str, Any])
async def create_assessment_only(
    topic: str,
    grade_level: str = "elementary",
    assessment_type: str = "comprehensive",
    existing_plan: Optional[Dict[str, Any]] = None,
    existing_content: Optional[Dict[str, Any]] = None
):
    """
    Create assessment materials using the Assessment Agent
    """
    try:
        pipeline = LessonPipeline()
        
        request_data = {
            "topic": topic,
            "grade_level": grade_level,
            "lesson_type": "assessment_only",
            "assessment_preferences": {
                "assessment_type": assessment_type,
                "include_rubrics": True,
                "adaptive_questions": True
            },
            "existing_lesson_plan": existing_plan,
            "existing_content": existing_content
        }
        
        result = await pipeline.execute_assessment_step(request_data)
        
        return {
            "status": "success",
            "assessment": result,
            "metadata": {
                "pipeline_type": "assessment_only",
                "assessment_type": assessment_type
            }
        }
        
    except Exception as e:
        logger.error(f"Assessment creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create assessment: {str(e)}"
        )

@router.post("/visual-aids/generate", response_model=Dict[str, Any])
async def generate_visual_aids(
    topic: str,
    grade_level: str = "elementary",
    visual_type: str = "comprehensive",
    existing_plan: Optional[Dict[str, Any]] = None,
    existing_content: Optional[Dict[str, Any]] = None
):
    """
    Generate visual aids using the Visual Aid Agent
    """
    try:
        pipeline = LessonPipeline()
        
        request_data = {
            "topic": topic,
            "grade_level": grade_level,
            "visual_preferences": {
                "visual_type": visual_type,
                "accessibility_compliant": True,
                "interactive_elements": True
            },
            "existing_lesson_plan": existing_plan,
            "existing_content": existing_content
        }
        
        result = await pipeline.execute_visual_aids_step(request_data)
        
        return {
            "status": "success",
            "visual_aids": result,
            "metadata": {
                "pipeline_type": "visual_aids_only",
                "visual_type": visual_type
            }
        }
        
    except Exception as e:
        logger.error(f"Visual aids generation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate visual aids: {str(e)}"
        )

@router.get("/pipeline/status")
async def get_pipeline_status():
    """
    Get the current status of the orchestration pipeline
    """
    try:
        from agents.planner_agent import planner_app
        from agents.content_agent import content_app  
        from agents.assessment_agent import assessment_app
        from agents.visual_aid_agent import visual_aid_app
        
        return {
            "status": "operational",
            "agents": {
                "planner": "available",
                "content": "available", 
                "assessment": "available",
                "visual_aid": "available"
            },
            "pipeline_version": "3.0.0",
            "adk_integration": True,
            "orchestration_ready": True
        }
        
    except Exception as e:
        logger.error(f"Pipeline status check error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "agents": {
                "planner": "error",
                "content": "error",
                "assessment": "error", 
                "visual_aid": "error"
            }
        }
