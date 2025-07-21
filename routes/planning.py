"""
Planning Routes
FastAPI routes for AI-powered lesson planning, curriculum development, and educational scheduling
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator

from services.planning_service import (
    generate_lesson_plan,
    generate_detailed_curriculum_plan,
    get_lesson_plan,
    get_class_lesson_plans,
    update_lesson_plan,
    delete_lesson_plan
)
from auth_middleware import firebase_auth, get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/planning", tags=["Planning"])


# Request Models
class LessonPlanRequest(BaseModel):
    class_id: str = Field(..., min_length=1, description="Class identifier")
    plan_type: str = Field("weekly", description="Type of plan ('daily', 'weekly', 'monthly')")
    duration: int = Field(7, ge=1, le=365, description="Duration in days")
    curriculum_standards: Optional[List[str]] = Field(None, description="Relevant curriculum standards")
    learning_objectives: Optional[List[str]] = Field(None, description="Specific learning objectives")
    
    @field_validator('class_id')
    @classmethod
    def validate_class_id(cls, v):
        if not v.strip():
            raise ValueError('Class ID cannot be empty')
        return v.strip()
    
    @field_validator('plan_type')
    @classmethod
    def validate_plan_type(cls, v):
        if v not in ['daily', 'weekly', 'monthly']:
            raise ValueError('Plan type must be "daily", "weekly", or "monthly"')
        return v
    
    @field_validator('curriculum_standards', 'learning_objectives')
    @classmethod
    def validate_lists(cls, v):
        if v is not None:
            return [item.strip() for item in v if item.strip()]
        return v


class CurriculumPlanRequest(BaseModel):
    class_id: str = Field(..., min_length=1, description="Class identifier")
    subject: str = Field(..., min_length=1, description="Subject area")
    grade_level: int = Field(..., ge=1, le=12, description="Grade level (1-12)")
    semester_duration: int = Field(90, ge=30, le=365, description="Duration in days (default 90 days)")
    
    @field_validator('class_id', 'subject')
    @classmethod
    def validate_strings(cls, v):
        if not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


class LessonPlanUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="Plan title")
    description: Optional[str] = Field(None, max_length=1000, description="Plan description")
    content: Optional[Dict[str, Any]] = Field(None, description="Updated plan content")
    notes: Optional[str] = Field(None, max_length=2000, description="Additional notes")
    
    @field_validator('title', 'description', 'notes')
    @classmethod
    def validate_optional_strings(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Field cannot be empty if provided')
        return v.strip() if v else None


# Response Models
class PlanOverview(BaseModel):
    title: str
    description: str
    total_days: int
    subjects_covered: Optional[List[str]] = None
    key_themes: Optional[List[str]] = None
    learning_outcomes: Optional[List[str]] = None


class Activity(BaseModel):
    time: str
    subject: str
    topic: str
    activity_type: Optional[str] = None
    description: str
    materials_needed: Optional[List[str]] = None
    learning_objective: Optional[str] = None
    assessment_method: Optional[str] = None


class DailySchedule(BaseModel):
    day: int
    date: str
    is_holiday: Optional[bool] = False
    activities: List[Activity]
    homework: Optional[str] = None
    notes: Optional[str] = None


class AssessmentPlan(BaseModel):
    formative_assessments: Optional[List[str]] = None
    summative_assessments: Optional[List[str]] = None
    grading_criteria: Optional[List[str]] = None


class Resources(BaseModel):
    required_materials: Optional[List[str]] = None
    digital_tools: Optional[List[str]] = None
    reference_books: Optional[List[str]] = None


class Differentiation(BaseModel):
    advanced_learners: Optional[List[str]] = None
    struggling_learners: Optional[List[str]] = None
    english_language_learners: Optional[List[str]] = None


class LessonPlanContent(BaseModel):
    plan_overview: PlanOverview
    daily_schedule: List[DailySchedule]
    assessment_plan: Optional[AssessmentPlan] = None
    resources: Optional[Resources] = None
    differentiation: Optional[Differentiation] = None


class LessonPlanResponse(BaseModel):
    status: str
    plan_id: str
    lesson_plan: LessonPlanContent
    metadata: Dict[str, Any]
    class_info: Optional[Dict[str, str]] = None


class CurriculumOverview(BaseModel):
    subject: str
    grade_level: int
    duration_days: int
    learning_outcomes: List[str]
    key_concepts: Optional[List[str]] = None


class CurriculumUnit(BaseModel):
    unit_number: int
    title: str
    duration_days: int
    learning_objectives: List[str]
    key_topics: List[str]
    activities: List[str]
    assessments: List[str]
    resources: List[str]


class CurriculumPlanContent(BaseModel):
    curriculum_overview: CurriculumOverview
    units: List[CurriculumUnit]
    assessment_strategy: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None


class CurriculumPlanResponse(BaseModel):
    status: str
    plan_id: str
    curriculum_plan: CurriculumPlanContent
    metadata: Dict[str, Any]


class PlanSummary(BaseModel):
    plan_id: str
    display_title: str
    summary: str
    plan_type: str
    duration: int
    class_id: str
    created_at: str
    created_date: Optional[str] = None
    user_id: Optional[str] = None


class UpdateResponse(BaseModel):
    status: str
    plan_id: str
    message: str


class DeleteResponse(BaseModel):
    status: str
    plan_id: str
    message: str


# Routes

@router.post("/lesson-plan", response_model=LessonPlanResponse, dependencies=[Depends(firebase_auth)])
async def create_lesson_plan(
    request: LessonPlanRequest,
    req: Request
):
    """
    Generate comprehensive AI-powered lesson plan
    
    Creates detailed lesson plans with:
    - Daily activity schedules
    - Assessment strategies
    - Resource requirements
    - Differentiation strategies
    - Integration with holidays and engagement data
    """
    try:
        user_id = await get_current_user_id(req)
        
        lesson_plan_data = await generate_lesson_plan(
            class_id=request.class_id,
            plan_type=request.plan_type,
            duration=request.duration,
            user_id=user_id,
            curriculum_standards=request.curriculum_standards,
            learning_objectives=request.learning_objectives
        )
        
        return LessonPlanResponse(**lesson_plan_data)
        
    except ValueError as e:
        logger.warning(f"Invalid input for lesson plan generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating lesson plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate lesson plan")


@router.post("/curriculum-plan", response_model=CurriculumPlanResponse, dependencies=[Depends(firebase_auth)])
async def create_curriculum_plan(
    request: CurriculumPlanRequest,
    req: Request
):
    """
    Generate comprehensive curriculum plan for a subject
    
    Creates detailed semester-long curriculum including:
    - Unit progression and pacing
    - Learning objectives and outcomes
    - Assessment strategies
    - Resource recommendations
    - Standards alignment
    """
    try:
        user_id = await get_current_user_id(req)
        
        curriculum_data = await generate_detailed_curriculum_plan(
            class_id=request.class_id,
            subject=request.subject,
            grade_level=request.grade_level,
            semester_duration=request.semester_duration,
            user_id=user_id
        )
        
        return CurriculumPlanResponse(**curriculum_data)
        
    except ValueError as e:
        logger.warning(f"Invalid input for curriculum plan generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating curriculum plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate curriculum plan")


@router.get("/lesson-plan/{plan_id}", dependencies=[Depends(firebase_auth)])
async def get_lesson_plan_details(
    plan_id: str,
    req: Request
):
    """
    Retrieve detailed lesson plan by ID
    
    Returns complete lesson plan with all content,
    metadata, and associated resources
    """
    try:
        user_id = await get_current_user_id(req)
        
        plan_data = await get_lesson_plan(plan_id, user_id)
        
        return plan_data
        
    except ValueError as e:
        logger.warning(f"Invalid input for lesson plan retrieval: {e}")
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    except Exception as e:
        logger.error(f"Error retrieving lesson plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve lesson plan")


@router.get("/class/{class_id}/plans", response_model=List[PlanSummary], dependencies=[Depends(firebase_auth)])
async def get_class_plan_history(
    class_id: str,
    req: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of plans to return"),
    plan_type: Optional[str] = Query(None, description="Filter by plan type")
):
    """
    Get lesson plan history for a class
    
    Parameters:
    - limit: Maximum number of plans to return (1-100)
    - plan_type: Optional filter by plan type ('daily', 'weekly', 'monthly')
    
    Returns summarized list of lesson plans for the class
    """
    try:
        user_id = await get_current_user_id(req)
        
        # Validate plan_type if provided
        if plan_type and plan_type not in ["daily", "weekly", "monthly", "curriculum"]:
            raise HTTPException(status_code=400, detail="Plan type must be 'daily', 'weekly', 'monthly', or 'curriculum'")
        
        plans = await get_class_lesson_plans(class_id, limit, plan_type, user_id)
        
        return [PlanSummary(**plan) for plan in plans]
        
    except ValueError as e:
        logger.warning(f"Invalid input for class plans retrieval: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving class plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve class plans")


@router.put("/lesson-plan/{plan_id}", response_model=UpdateResponse, dependencies=[Depends(firebase_auth)])
async def update_lesson_plan_endpoint(
    plan_id: str,
    request: LessonPlanUpdateRequest,
    req: Request
):
    """
    Update lesson plan
    
    Allows modification of:
    - Plan title and description
    - Plan content and structure
    - Additional notes and metadata
    """
    try:
        user_id = await get_current_user_id(req)
        
        # Convert request to dictionary, excluding None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        result = await update_lesson_plan(plan_id, updates, user_id)
        
        return UpdateResponse(**result)
        
    except PermissionError as e:
        logger.warning(f"Permission denied for lesson plan update: {e}")
        raise HTTPException(status_code=403, detail="Not authorized to update this lesson plan")
    except ValueError as e:
        logger.warning(f"Invalid input for lesson plan update: {e}")
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    except Exception as e:
        logger.error(f"Error updating lesson plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to update lesson plan")


@router.delete("/lesson-plan/{plan_id}", response_model=DeleteResponse, dependencies=[Depends(firebase_auth)])
async def delete_lesson_plan_endpoint(
    plan_id: str,
    req: Request
):
    """
    Delete lesson plan
    
    Removes lesson plan from the system:
    - Only plan creators can delete their plans
    - Teachers/admins may have broader deletion permissions
    - Soft delete preserves data integrity
    """
    try:
        user_id = await get_current_user_id(req)
        
        result = await delete_lesson_plan(plan_id, user_id)
        
        return DeleteResponse(**result)
        
    except PermissionError as e:
        logger.warning(f"Permission denied for lesson plan deletion: {e}")
        raise HTTPException(status_code=403, detail="Not authorized to delete this lesson plan")
    except ValueError as e:
        logger.warning(f"Invalid input for lesson plan deletion: {e}")
        raise HTTPException(status_code=404, detail="Lesson plan not found")
    except Exception as e:
        logger.error(f"Error deleting lesson plan: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete lesson plan")


@router.get("/my-plans", response_model=List[PlanSummary], dependencies=[Depends(firebase_auth)])
async def get_my_lesson_plans(
    req: Request,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of plans to return"),
    plan_type: Optional[str] = Query(None, description="Filter by plan type")
):
    """
    Get lesson plans created by the current user
    
    Convenience endpoint for users to view their own planning history
    across all classes they manage
    """
    try:
        user_id = await get_current_user_id(req)
        
        # Validate plan_type if provided
        if plan_type and plan_type not in ["daily", "weekly", "monthly", "curriculum"]:
            raise HTTPException(status_code=400, detail="Plan type must be 'daily', 'weekly', 'monthly', or 'curriculum'")
        
        # In a real implementation, this would query for plans by user_id
        # For now, we'll return an empty list as this requires additional DAO methods
        plans = []  # await get_user_lesson_plans(user_id, limit, plan_type)
        
        return [PlanSummary(**plan) for plan in plans]
        
    except Exception as e:
        logger.error(f"Error retrieving current user plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve your plans")


# Additional utility endpoints

@router.get("/templates", response_model=List[Dict[str, Any]], dependencies=[Depends(firebase_auth)])
async def get_planning_templates(
    req: Request,
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get available lesson plan templates
    
    Returns list of reusable templates for quick plan creation
    """
    try:
        # In a real implementation, this would use planning_dao.get_plan_templates()
        templates = [
            {
                "template_id": "weekly_elementary",
                "name": "Elementary Weekly Plan",
                "description": "Standard weekly plan template for elementary grades",
                "category": "elementary",
                "subjects": ["Math", "English", "Science", "Social Studies"],
                "duration_days": 5
            },
            {
                "template_id": "monthly_secondary",
                "name": "Secondary Monthly Plan",
                "description": "Comprehensive monthly plan for secondary education",
                "category": "secondary", 
                "subjects": ["Multiple"],
                "duration_days": 30
            }
        ]
        
        if category:
            templates = [t for t in templates if t.get("category") == category]
        
        return templates
        
    except Exception as e:
        logger.error(f"Error retrieving planning templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve templates")


@router.get("/subjects", response_model=List[str], dependencies=[Depends(firebase_auth)])
async def get_available_subjects(req: Request):
    """
    Get list of available subjects for planning
    
    Returns comprehensive list of subject areas for curriculum planning
    """
    try:
        subjects = [
            "Mathematics",
            "English Language Arts",
            "Science",
            "Social Studies",
            "History",
            "Geography",
            "Biology",
            "Chemistry",
            "Physics",
            "Art",
            "Music",
            "Physical Education",
            "Technology",
            "Foreign Languages",
            "Computer Science",
            "Health Education",
            "Career Education",
            "Environmental Science"
        ]
        
        return subjects
        
    except Exception as e:
        logger.error(f"Error retrieving subjects: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve subjects")


@router.get("/plan-types", response_model=List[Dict[str, str]], dependencies=[Depends(firebase_auth)])
async def get_plan_types(req: Request):
    """
    Get available lesson plan types
    
    Returns list of supported plan types with descriptions
    """
    try:
        plan_types = [
            {
                "type": "daily",
                "name": "Daily Plan",
                "description": "Detailed plan for a single day of instruction"
            },
            {
                "type": "weekly", 
                "name": "Weekly Plan",
                "description": "Comprehensive plan covering a full week of instruction"
            },
            {
                "type": "monthly",
                "name": "Monthly Plan", 
                "description": "Long-term planning for an entire month"
            },
            {
                "type": "curriculum",
                "name": "Curriculum Plan",
                "description": "Semester or year-long curriculum planning"
            }
        ]
        
        return plan_types
        
    except Exception as e:
        logger.error(f"Error retrieving plan types: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve plan types")
