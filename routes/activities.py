"""
Activities Routes
FastAPI routes for interactive activities, stories, AR/VR content, and badges
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, validator

from services.activities_service import (
    generate_interactive_story,
    generate_ar_scene,
    assign_badge,
    get_user_badges,
    get_user_activities
)
from auth_middleware import firebase_auth, get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/activities", tags=["Activities"])


# Request Models
class InteractiveStoryRequest(BaseModel):
    grade: int = Field(..., ge=1, le=12, description="Grade level (1-12)")
    topic: str = Field(..., min_length=1, max_length=200, description="Educational topic")
    language: str = Field(..., description="Language for the story")
    
    @validator('topic')
    def validate_topic(cls, v):
        if not v.strip():
            raise ValueError('Topic cannot be empty')
        return v.strip()


class ARSceneRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200, description="Educational topic for AR scene")
    grade_level: Optional[int] = Field(None, ge=1, le=12, description="Grade level for age-appropriate content")
    
    @validator('topic')
    def validate_topic(cls, v):
        if not v.strip():
            raise ValueError('Topic cannot be empty')
        return v.strip()


class BadgeAssignmentRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="User ID to assign badge to")
    badge_name: str = Field(..., min_length=1, max_length=100, description="Name of the badge")
    criteria_met: Optional[Dict[str, Any]] = Field(None, description="Criteria that were met")
    
    @validator('user_id', 'badge_name')
    def validate_strings(cls, v):
        if not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()


# Response Models
class InteractiveStoryResponse(BaseModel):
    story_id: str
    title: str
    story_text: str
    think_about_it: str
    what_you_learn: str
    learning_objectives: List[str]
    vocabulary_words: List[str]
    audio_filename: str
    grade_level: int
    topic: str
    language: str
    subject: str


class AREnvironment(BaseModel):
    setting: str
    lighting: Optional[str] = None
    atmosphere: Optional[str] = None
    size_scale: Optional[str] = None


class ARObject(BaseModel):
    name: str
    description: str
    interactions: List[str]
    learning_purpose: str


class ARInteraction(BaseModel):
    type: str
    description: str
    learning_outcome: str
    feedback_mechanism: str


class ARSceneResponse(BaseModel):
    scene_id: str
    scene_name: str
    educational_objective: str
    environment: AREnvironment
    objects: List[ARObject]
    interactions: List[ARInteraction]
    technical_requirements: Optional[List[str]] = None
    assessment_opportunities: Optional[List[str]] = None
    grade_level: Optional[int] = None
    subject_area: Optional[str] = None


class BadgeResponse(BaseModel):
    status: str
    badge_id: Optional[str] = None
    badge: str
    points_earned: Optional[int] = None
    message: str


class UserBadge(BaseModel):
    badge_id: str
    badge: str
    assigned_at: str
    badge_type: str
    points_earned: int
    description: str
    rarity: str
    display_name: str
    icon_url: str
    achievement_date: Optional[str] = None


class ActivitySummary(BaseModel):
    activity_id: str
    title: str
    type: str
    created_at: str
    grade_level: Optional[int] = None
    topic: Optional[str] = None


# Routes

@router.post("/interactive-story", response_model=InteractiveStoryResponse, dependencies=[Depends(firebase_auth)])
async def create_interactive_story(
    request: InteractiveStoryRequest,
    req: Request
):
    """
    Generate an interactive educational story with audio in specified language
    
    Creates a voice-enabled story with:
    - Age-appropriate content for specified grade level
    - 500-word educational narrative
    - "Think about it" reflection section
    - "What you'll learn" summary section
    - Generated audio narration
    - Learning objectives and vocabulary
    - Complete localization in requested language
    """
    try:
        user_id = await get_current_user_id(req)
        
        story_data = await generate_interactive_story(
            grade=request.grade,
            topic=request.topic,
            language=request.language,
            user_id=user_id
        )
        
        return InteractiveStoryResponse(**story_data)
        
    except ValueError as e:
        logger.warning(f"Invalid input for interactive story: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating interactive story: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate interactive story")


@router.post("/ar-scene", response_model=ARSceneResponse, dependencies=[Depends(firebase_auth)])
async def create_ar_scene(
    request: ARSceneRequest,
    req: Request
):
    """
    Generate AR/VR scene configuration for educational content
    
    Creates detailed scene specifications for:
    - Unity/WebXR implementation
    - Interactive 3D objects and environments
    - Educational activities and assessments
    - Age-appropriate complexity
    """
    try:
        user_id = await get_current_user_id(req)
        
        scene_data = await generate_ar_scene(
            topic=request.topic,
            grade_level=request.grade_level,
            user_id=user_id
        )
        
        return ARSceneResponse(**scene_data)
        
    except ValueError as e:
        logger.warning(f"Invalid input for AR scene: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating AR scene: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate AR scene")


@router.post("/assign-badge", response_model=BadgeResponse, dependencies=[Depends(firebase_auth)])
async def assign_user_badge(
    request: BadgeAssignmentRequest,
    req: Request
):
    """
    Assign a badge to a user with tracking and metadata
    
    Features:
    - Duplicate prevention
    - Point calculation
    - Badge type classification
    - Detailed tracking
    """
    try:
        # Check if user has permission to assign badges (e.g., teacher role)
        user_role = req.state.user.get("role", "student")
        if user_role not in ["teacher", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions to assign badges")
        
        badge_result = await assign_badge(
            user_id=request.user_id,
            badge_name=request.badge_name,
            criteria_met=request.criteria_met
        )
        
        return BadgeResponse(**badge_result)
        
    except ValueError as e:
        logger.warning(f"Invalid input for badge assignment: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error assigning badge: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign badge")


@router.get("/badges/{user_id}", response_model=List[UserBadge], dependencies=[Depends(firebase_auth)])
async def get_user_badge_list(
    user_id: str,
    req: Request
):
    """
    Get all badges for a specific user
    
    Returns detailed badge information including:
    - Badge metadata and descriptions
    - Points earned and rarity
    - Achievement dates
    - Display formatting
    """
    try:
        # Check permissions - users can view their own badges, teachers can view any
        current_user_id = await get_current_user_id(req)
        user_role = req.state.user.get("role", "student")
        
        if user_id != current_user_id and user_role not in ["teacher", "admin"]:
            raise HTTPException(status_code=403, detail="Can only view your own badges")
        
        badges = await get_user_badges(user_id)
        
        return [UserBadge(**badge) for badge in badges]
        
    except ValueError as e:
        logger.warning(f"Invalid input for badge retrieval: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving user badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve badges")


@router.get("/user/{user_id}", response_model=List[ActivitySummary], dependencies=[Depends(firebase_auth)])
async def get_user_activity_history(
    user_id: str,
    req: Request,
    limit: int = 10,
    activity_type: Optional[str] = None
):
    """
    Get activity history for a user
    
    Parameters:
    - limit: Maximum number of activities to return (default: 10)
    - activity_type: Filter by specific activity type (optional)
    
    Returns activities with summary information
    """
    try:
        # Check permissions - users can view their own activities, teachers can view any
        current_user_id = await get_current_user_id(req)
        user_role = req.state.user.get("role", "student")
        
        if user_id != current_user_id and user_role not in ["teacher", "admin"]:
            raise HTTPException(status_code=403, detail="Can only view your own activities")
        
        # Validate limit
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        activities = await get_user_activities(user_id, limit, activity_type)
        
        return [ActivitySummary(**activity) for activity in activities]
        
    except ValueError as e:
        logger.warning(f"Invalid input for activity history: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving user activities: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve activities")


@router.get("/my-badges", response_model=List[UserBadge], dependencies=[Depends(firebase_auth)])
async def get_my_badges(req: Request):
    """
    Get badges for the current authenticated user
    
    Convenience endpoint for users to view their own badges
    """
    try:
        user_id = await get_current_user_id(req)
        badges = await get_user_badges(user_id)
        
        return [UserBadge(**badge) for badge in badges]
        
    except Exception as e:
        logger.error(f"Error retrieving current user badges: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve your badges")


@router.get("/my-activities", response_model=List[ActivitySummary], dependencies=[Depends(firebase_auth)])
async def get_my_activities(
    req: Request,
    limit: int = 10,
    activity_type: Optional[str] = None
):
    """
    Get activity history for the current authenticated user
    
    Convenience endpoint for users to view their own activity history
    """
    try:
        user_id = await get_current_user_id(req)
        
        # Validate limit
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        activities = await get_user_activities(user_id, limit, activity_type)
        
        return [ActivitySummary(**activity) for activity in activities]
        
    except Exception as e:
        logger.error(f"Error retrieving current user activities: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve your activities")
