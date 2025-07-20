from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from auth_middleware import firebase_auth, get_current_user_id
from services.content_agent import generate_activity, generate_visual_aid
from services.planning_agent import generate_lesson_plan

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/education", tags=["Education"])

# ===== REQUEST MODELS =====

class ActivityRequest(BaseModel):
    """Request model for generating educational activities"""
    grade: int = Field(..., ge=1, le=12, description="Grade level (1-12)")
    topic: str = Field(..., min_length=2, max_length=200, description="Topic for the activity")
    activity_type: Optional[str] = Field(default="general", description="Type of activity (worksheet, project, game, etc.)")
    duration: Optional[int] = Field(default=30, ge=5, le=180, description="Duration in minutes")
    difficulty: Optional[str] = Field(default="medium", pattern="^(easy|medium|hard)$", description="Difficulty level")
    
    @validator('topic')
    def validate_topic(cls, v):
        if not v.strip():
            raise ValueError('Topic cannot be empty')
        return v.strip()

class VisualAidRequest(BaseModel):
    """Request model for generating visual aids"""
    concept: str = Field(..., min_length=2, max_length=200, description="Concept for visual aid")
    grade_level: Optional[int] = Field(default=None, ge=1, le=12, description="Target grade level")
    format_type: Optional[str] = Field(default="diagram", description="Type of visual aid (diagram, infographic, chart, etc.)")
    style: Optional[str] = Field(default="educational", description="Visual style preference")
    
    @validator('concept')
    def validate_concept(cls, v):
        if not v.strip():
            raise ValueError('Concept cannot be empty')
        return v.strip()

class LessonPlanRequest(BaseModel):
    """Request model for generating lesson plans"""
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

# ===== RESPONSE MODELS =====

class EducationResponse(BaseModel):
    """Base response model for education endpoints"""
    status: str
    message: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]

# ===== ENDPOINTS =====

@router.post("/activities",
            summary="Generate Educational Activity",
            description="Generate a personalized educational activity based on grade level and topic",
            response_model=EducationResponse,
            dependencies=[Depends(firebase_auth)])
async def create_activity(
    request: ActivityRequest,
    user_request: Request
) -> EducationResponse:
    """
    Generate a personalized educational activity
    
    - **grade**: Grade level (1-12)
    - **topic**: Subject topic for the activity
    - **activity_type**: Type of activity (worksheet, project, game, etc.)
    - **duration**: Duration in minutes (5-180)
    - **difficulty**: Difficulty level (easy/medium/hard)
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        logger.info(f"Generating activity for user {user_id}: Grade {request.grade}, Topic: {request.topic}")
        
        # Generate activity using the service
        activity = generate_activity(
            grade=request.grade,
            topic=request.topic,
            activity_type=request.activity_type,
            duration=request.duration,
            difficulty=request.difficulty
        )
        
        logger.info(f"Successfully generated activity for user {user_id}")
        
        return EducationResponse(
            status="success",
            message="Activity generated successfully",
            data={"activity": activity},
            metadata={
                "user_id": user_id,
                "grade": request.grade,
                "topic": request.topic,
                "activity_type": request.activity_type,
                "duration": request.duration,
                "difficulty": request.difficulty,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating activity for user {user_id if 'user_id' in locals() else 'unknown'}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate activity: {str(e)}"
        )

@router.post("/visual-aids",
            summary="Generate Visual Aid",
            description="Generate a visual aid to help explain educational concepts",
            response_model=EducationResponse,
            dependencies=[Depends(firebase_auth)])
async def create_visual_aid(
    request: VisualAidRequest,
    user_request: Request
) -> EducationResponse:
    """
    Generate a visual aid for educational concepts
    
    - **concept**: The concept to visualize
    - **grade_level**: Target grade level (optional)
    - **format_type**: Type of visual aid (diagram, infographic, chart, etc.)
    - **style**: Visual style preference
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        logger.info(f"Generating visual aid for user {user_id}: Concept: {request.concept}")
        
        # Generate visual aid using the service
        visual_aid = generate_visual_aid(
            concept=request.concept,
            grade_level=request.grade_level,
            format_type=request.format_type,
            style=request.style
        )
        
        logger.info(f"Successfully generated visual aid for user {user_id}")
        
        return EducationResponse(
            status="success",
            message="Visual aid generated successfully",
            data={"visual_aid": visual_aid},
            metadata={
                "user_id": user_id,
                "concept": request.concept,
                "grade_level": request.grade_level,
                "format_type": request.format_type,
                "style": request.style,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating visual aid for user {user_id if 'user_id' in locals() else 'unknown'}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate visual aid: {str(e)}"
        )

@router.post("/lesson-plans",
            summary="Generate Comprehensive Lesson Plan",
            description="Generate a detailed lesson plan with activities, assessments, and teaching materials",
            response_model=EducationResponse,
            dependencies=[Depends(firebase_auth)])
async def create_lesson_plan(
    request: LessonPlanRequest,
    user_request: Request
) -> EducationResponse:
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
        
        return EducationResponse(
            status="success",
            message="Lesson plan generated successfully",
            data={"lesson_plan": lesson_plan},
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
           summary="Get Educational Templates",
           description="Get available templates for lesson plans and activities",
           dependencies=[Depends(firebase_auth)])
async def get_templates():
    """Get available educational templates"""
    return {
        "status": "success",
        "message": "Educational templates retrieved successfully",
        "data": {
            "lesson_plan_templates": {
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
            "activity_types": [
                "worksheet", "project", "game", "experiment", "presentation", 
                "group_work", "individual_study", "creative_writing", "problem_solving"
            ],
            "visual_aid_formats": [
                "diagram", "infographic", "chart", "mind_map", "flowchart", 
                "timeline", "comparison_table", "concept_map"
            ],
            "teaching_styles": ["visual", "auditory", "kinesthetic", "balanced"],
            "difficulty_levels": ["easy", "medium", "hard", "mixed"],
            "supported_grades": list(range(1, 13))
        },
        "metadata": {
            "retrieved_at": datetime.utcnow().isoformat()
        }
    }

@router.get("/health",
           summary="Education Service Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for the education service"""
    return {
        "status": "healthy",
        "service": "education",
        "message": "Education service is running properly",
        "features": [
            "activity_generation",
            "visual_aid_creation", 
            "lesson_plan_generation",
            "template_management"
        ],
        "supported_grades": list(range(1, 13)),
        "endpoints": ["/activities", "/visual-aids", "/lesson-plans", "/templates"]
    }
