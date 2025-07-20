from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from auth_middleware import firebase_auth, get_current_user_id
from services.planning_agent import generate_lesson_plan

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planning", tags=["Lesson Planning"])

class LessonPlanRequest(BaseModel):
    grades: List[int] = Field(..., description="List of grade levels (1-12)")
    topics: List[str] = Field(..., min_items=1, max_items=10, description="List of topics to cover")
    duration: Optional[int] = Field(default=60, ge=15, le=180, description="Lesson duration in minutes")
    subject: Optional[str] = Field(default="General", max_length=100, description="Subject area")
    learning_objectives: Optional[List[str]] = Field(default=None, description="Specific learning objectives")
    teaching_style: Optional[str] = Field(default="balanced", pattern="^(visual|auditory|kinesthetic|balanced)$", description="Teaching style preference")
    difficulty_level: Optional[str] = Field(default="medium", pattern="^(easy|medium|hard|mixed)$", description="Difficulty level")
    include_activities: Optional[bool] = Field(default=True, description="Include hands-on activities")
    include_assessment: Optional[bool] = Field(default=True, description="Include assessment methods")
    
    @validator('grades')
    def validate_grades(cls, v):
        if not v:
            raise ValueError('At least one grade level is required')
        for grade in v:
            if grade < 1 or grade > 12:
                raise ValueError('Grade levels must be between 1 and 12')
        return sorted(list(set(v)))  # Remove duplicates and sort
    
    @validator('topics')
    def validate_topics(cls, v):
        if not v:
            raise ValueError('At least one topic is required')
        return [topic.strip() for topic in v if topic.strip()]

class LessonPlanResponse(BaseModel):
    status: str
    lesson_plan: Dict[str, Any]
    metadata: Dict[str, Any]

@router.post("/lesson-plan",
            summary="Generate Comprehensive Lesson Plan",
            description="Generate a detailed lesson plan with activities, assessments, and teaching materials",
            response_model=LessonPlanResponse,
            dependencies=[Depends(firebase_auth)])
async def create_lesson_plan(
    request: LessonPlanRequest,
    user_request: Request
):
    """
    Generate a comprehensive lesson plan
    
    - **grades**: List of target grade levels (1-12)
    - **topics**: List of topics to cover in the lesson
    - **duration**: Lesson duration in minutes (15-180)
    - **subject**: Subject area (optional)
    - **learning_objectives**: Specific learning objectives (optional)
    - **teaching_style**: Teaching style preference (visual/auditory/kinesthetic/balanced)
    - **difficulty_level**: Difficulty level (easy/medium/hard/mixed)
    - **include_activities**: Include hands-on activities
    - **include_assessment**: Include assessment methods
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        logger.info(f"Generating lesson plan for user {user_id}: Grades {request.grades}, Topics: {request.topics}")
        
        # Generate lesson plan using the service
        lesson_plan = generate_lesson_plan(
            grades=request.grades,
            topics=request.topics,
            duration=request.duration,
            subject=request.subject,
            learning_objectives=request.learning_objectives,
            teaching_style=request.teaching_style,
            difficulty_level=request.difficulty_level,
            include_activities=request.include_activities,
            include_assessment=request.include_assessment
        )
        
        logger.info(f"Successfully generated lesson plan for user {user_id}")
        
        return LessonPlanResponse(
            status="success",
            lesson_plan=lesson_plan,
            metadata={
                "user_id": user_id,
                "grades": request.grades,
                "topics": request.topics,
                "duration": request.duration,
                "subject": request.subject,
                "teaching_style": request.teaching_style,
                "difficulty_level": request.difficulty_level,
                "generated_at": datetime.utcnow().isoformat(),
                "includes_activities": request.include_activities,
                "includes_assessment": request.include_assessment
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating lesson plan for user {user_id if 'user_id' in locals() else 'unknown'}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate lesson plan: {str(e)}"
        )

@router.get("/templates",
           summary="Get Lesson Plan Templates",
           description="Get available lesson plan templates and formats",
           dependencies=[Depends(firebase_auth)])
async def get_lesson_plan_templates():
    """Get available lesson plan templates"""
    return {
        "status": "success",
        "templates": {
            "basic": {
                "name": "Basic Lesson Plan",
                "description": "Simple lesson structure with intro, main content, and conclusion",
                "duration_range": "30-60 minutes",
                "components": ["introduction", "main_content", "activities", "conclusion", "homework"]
            },
            "detailed": {
                "name": "Detailed Lesson Plan",
                "description": "Comprehensive lesson with multiple activities and assessments",
                "duration_range": "60-90 minutes",
                "components": ["warm_up", "introduction", "main_content", "guided_practice", "independent_practice", "assessment", "wrap_up"]
            },
            "project_based": {
                "name": "Project-Based Learning",
                "description": "Project-centered lesson plan with collaborative activities",
                "duration_range": "90-180 minutes",
                "components": ["project_introduction", "research_phase", "collaboration", "creation", "presentation", "reflection"]
            },
            "differentiated": {
                "name": "Differentiated Instruction",
                "description": "Multi-level lesson accommodating different learning styles",
                "duration_range": "45-75 minutes",
                "components": ["universal_intro", "tiered_activities", "choice_options", "flexible_grouping", "varied_assessment"]
            }
        },
        "teaching_styles": ["visual", "auditory", "kinesthetic", "balanced"],
        "difficulty_levels": ["easy", "medium", "hard", "mixed"],
        "supported_grades": list(range(1, 13)),
        "max_topics": 10
    }

# Legacy endpoint for backward compatibility
@router.get("/lesson-plan",
           summary="Generate Lesson Plan (Legacy)",
           description="Legacy endpoint for generating lesson plans (deprecated - use POST /lesson-plan)",
           deprecated=True,
           dependencies=[Depends(firebase_auth)])
async def get_lesson_plan_legacy(
    grades: str = Query(..., description="Comma-separated grade levels"),
    topics: str = Query(..., description="Comma-separated topics"),
    user_request: Request = None
):
    """Legacy endpoint - use POST /lesson-plan instead"""
    logger.warning("Using deprecated GET /lesson-plan endpoint")
    
    try:
        # Parse comma-separated grades and topics
        grade_list = [int(g.strip()) for g in grades.split(',') if g.strip().isdigit()]
        topic_list = [t.strip() for t in topics.split(',') if t.strip()]
        
        request_model = LessonPlanRequest(grades=grade_list, topics=topic_list)
        response = await create_lesson_plan(request_model, user_request)
        
        # Return legacy format
        return {"lesson_plan": response.lesson_plan}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input format: {str(e)}")

@router.get("/health",
           summary="Planning Service Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for the planning service"""
    return {
        "status": "healthy",
        "service": "planning",
        "message": "Lesson planning service is running properly",
        "features": ["lesson_plan_generation", "template_management"],
        "supported_grades": list(range(1, 13)),
        "max_topics_per_plan": 10
    }
