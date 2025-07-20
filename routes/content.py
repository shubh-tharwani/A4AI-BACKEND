from fastapi import APIRouter, Depends, HTTPException, Request, Query, Body
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from auth_middleware import firebase_auth, get_current_user_id
from services.content_agent import generate_activity, generate_visual_aid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["Content Generation"])

class ActivityRequest(BaseModel):
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
    concept: str = Field(..., min_length=2, max_length=200, description="Concept for visual aid")
    grade_level: Optional[int] = Field(default=None, ge=1, le=12, description="Target grade level")
    format_type: Optional[str] = Field(default="diagram", description="Type of visual aid (diagram, infographic, chart, etc.)")
    style: Optional[str] = Field(default="educational", description="Visual style preference")
    
    @validator('concept')
    def validate_concept(cls, v):
        if not v.strip():
            raise ValueError('Concept cannot be empty')
        return v.strip()

@router.post("/activity", 
            summary="Generate Educational Activity",
            description="Generate a personalized educational activity based on grade level and topic",
            dependencies=[Depends(firebase_auth)])
async def create_activity(
    request: ActivityRequest,
    user_request: Request
):
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
        
        return {
            "status": "success",
            "message": "Activity generated successfully",
            "activity": activity,
            "metadata": {
                "user_id": user_id,
                "grade": request.grade,
                "topic": request.topic,
                "activity_type": request.activity_type,
                "duration": request.duration,
                "difficulty": request.difficulty,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating activity for user {user_id if 'user_id' in locals() else 'unknown'}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate activity: {str(e)}"
        )

@router.post("/visual-aid",
            summary="Generate Visual Aid",
            description="Generate a visual aid to help explain educational concepts",
            dependencies=[Depends(firebase_auth)])
async def create_visual_aid(
    request: VisualAidRequest,
    user_request: Request
):
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
        
        return {
            "status": "success",
            "message": "Visual aid generated successfully",
            "visual_aid": visual_aid,
            "metadata": {
                "user_id": user_id,
                "concept": request.concept,
                "grade_level": request.grade_level,
                "format_type": request.format_type,
                "style": request.style,
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating visual aid for user {user_id if 'user_id' in locals() else 'unknown'}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate visual aid: {str(e)}"
        )

# Legacy endpoints for backward compatibility
@router.get("/activity",
           summary="Generate Activity (Legacy)",
           description="Legacy endpoint for generating activities (deprecated - use POST /activity)",
           deprecated=True,
           dependencies=[Depends(firebase_auth)])
async def get_activity_legacy(
    grade: int = Query(..., ge=1, le=12),
    topic: str = Query(..., min_length=2, max_length=200),
    user_request: Request = None
):
    """Legacy endpoint - use POST /activity instead"""
    logger.warning("Using deprecated GET /activity endpoint")
    
    request_model = ActivityRequest(grade=grade, topic=topic)
    return await create_activity(request_model, user_request)

@router.get("/visual-aid",
           summary="Generate Visual Aid (Legacy)",
           description="Legacy endpoint for generating visual aids (deprecated - use POST /visual-aid)",
           deprecated=True,
           dependencies=[Depends(firebase_auth)])
async def get_visual_aid_legacy(
    concept: str = Query(..., min_length=2, max_length=200),
    user_request: Request = None
):
    """Legacy endpoint - use POST /visual-aid instead"""
    logger.warning("Using deprecated GET /visual-aid endpoint")
    
    request_model = VisualAidRequest(concept=concept)
    return await create_visual_aid(request_model, user_request)

@router.get("/health", 
           summary="Content Service Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for the content service"""
    return {
        "status": "healthy",
        "service": "content",
        "message": "Content generation service is running properly",
        "features": ["activity_generation", "visual_aid_creation"]
    }
