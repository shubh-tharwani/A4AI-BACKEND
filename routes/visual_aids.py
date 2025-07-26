"""
Visual Aid Routes
FastAPI routes for educational visual content generation and management
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, Field, validator

from services.visual_aid_service import (
    generate_visual_aid,
    generate_educational_infographic,
    get_user_visual_aids,
    search_visual_aids,
    delete_visual_aid
)
from auth_middleware import firebase_auth, get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/visual-aids", tags=["Visual Aids"])


# Request Models
class VisualAidRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500, description="Description of the visual aid to generate")
    asset_type: str = Field("image", description="Type of asset ('image' or 'video')")
    grade_level: Optional[int] = Field(None, ge=1, le=12, description="Grade level for age-appropriate content")
    subject: Optional[str] = Field(None, max_length=100, description="Subject area for categorization")
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if not v.strip():
            raise ValueError('Prompt cannot be empty')
        return v.strip()
    
    @validator('asset_type')
    def validate_asset_type(cls, v):
        if v not in ['image', 'video']:
            raise ValueError('Asset type must be "image" or "video"')
        return v
    
    @validator('subject')
    def validate_subject(cls, v):
        if v and not v.strip():
            raise ValueError('Subject cannot be empty if provided')
        return v.strip() if v else None


class InfographicRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200, description="Main topic of the infographic")
    data_points: List[str] = Field(..., min_items=1, max_items=20, description="Key data points to include")
    grade_level: Optional[int] = Field(None, ge=1, le=12, description="Grade level for complexity")
    
    @validator('topic')
    def validate_topic(cls, v):
        if not v.strip():
            raise ValueError('Topic cannot be empty')
        return v.strip()
    
    @validator('data_points')
    def validate_data_points(cls, v):
        if not v:
            raise ValueError('Data points cannot be empty')
        # Clean up data points
        cleaned = [point.strip() for point in v if point.strip()]
        if not cleaned:
            raise ValueError('Must provide at least one valid data point')
        return cleaned


# Response Models
class VisualAidMetadata(BaseModel):
    generation_model: str
    prompt_length: int
    image_size: int
    generated_at: str
    aspect_ratio: Optional[str] = None
    fallback_reason: Optional[str] = None


class VisualAidResponse(BaseModel):
    visual_aid_id: str
    status: str
    prompt: str
    enhanced_prompt: Optional[str] = None
    asset_type: str
    image_url: str
    filename: str
    topic: str
    metadata: VisualAidMetadata


class InfographicResponse(BaseModel):
    visual_aid_id: str
    status: str
    topic: str
    data_points: List[str]
    image_url: str
    filename: str
    complexity: str
    metadata: Dict[str, Any]


class VisualAidSummary(BaseModel):
    visual_aid_id: str
    prompt: str
    asset_type: str
    topic: str
    display_topic: str
    image_url: str
    grade_level: Optional[int] = None
    subject: Optional[str] = None
    created_at: str
    created_date: Optional[str] = None


class DeleteResponse(BaseModel):
    status: str
    visual_aid_id: str
    message: str


# Routes

@router.post("/generate", response_model=VisualAidResponse, dependencies=[Depends(firebase_auth)])
async def create_visual_aid(
    request: VisualAidRequest,
    req: Request
):
    """
    Generate educational visual aid using AI
    
    Creates contextual images or videos for educational content:
    - Age-appropriate content based on grade level
    - Subject-specific visual styling
    - High-quality educational illustrations
    - Classroom-ready visual aids
    """
    try:
        user_id = await get_current_user_id(req)
        
        visual_aid_data = await generate_visual_aid(
            prompt=request.prompt,
            asset_type=request.asset_type,
            user_id=user_id,
            grade_level=request.grade_level,
            subject=request.subject
        )
        
        return VisualAidResponse(**visual_aid_data)
        
    except ValueError as e:
        logger.warning(f"Invalid input for visual aid generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating visual aid: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate visual aid")


@router.post("/infographic", response_model=InfographicResponse, dependencies=[Depends(firebase_auth)])
async def create_infographic(
    request: InfographicRequest,
    req: Request
):
    """
    Generate educational infographic with data visualization
    
    Creates comprehensive infographics featuring:
    - Data visualization and charts
    - Age-appropriate complexity
    - Professional educational design
    - Key information highlighted clearly
    """
    try:
        user_id = await get_current_user_id(req)
        
        infographic_data = await generate_educational_infographic(
            topic=request.topic,
            data_points=request.data_points,
            grade_level=request.grade_level,
            user_id=user_id
        )
        
        return InfographicResponse(**infographic_data)
        
    except ValueError as e:
        logger.warning(f"Invalid input for infographic generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating infographic: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate infographic")


@router.get("/user/{user_id}", response_model=List[VisualAidSummary], dependencies=[Depends(firebase_auth)])
async def get_user_visual_aid_history(
    user_id: str,
    req: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of visual aids to return"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type ('image' or 'video')")
):
    """
    Get visual aid history for a specific user
    
    Parameters:
    - limit: Maximum number of visual aids to return (1-100)
    - asset_type: Optional filter by asset type
    
    Returns visual aids with summary information
    """
    try:
        # Check permissions - users can view their own visual aids, teachers can view any
        current_user_id = await get_current_user_id(req)
        current_user_data = req.state.user
        user_role = current_user_data.get("role", "student")
        
        if user_id != current_user_id and user_role not in ["teacher", "admin"]:
            raise HTTPException(status_code=403, detail="Can only view your own visual aids")
        
        # Validate asset_type if provided
        if asset_type and asset_type not in ["image", "video"]:
            raise HTTPException(status_code=400, detail="Asset type must be 'image' or 'video'")
        
        visual_aids = await get_user_visual_aids(user_id, limit, asset_type)
        
        return [VisualAidSummary(**visual_aid) for visual_aid in visual_aids]
        
    except ValueError as e:
        logger.warning(f"Invalid input for visual aid history: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving user visual aids: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve visual aids")


@router.get("/search", response_model=List[VisualAidSummary], dependencies=[Depends(firebase_auth)])
async def search_visual_aid_library(
    req: Request,
    topic: str = Query(..., min_length=1, max_length=100, description="Topic to search for"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    grade_level: Optional[int] = Query(None, ge=1, le=12, description="Filter by grade level"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results")
):
    """
    Search the visual aid library by topic
    
    Find existing visual aids that match your educational needs:
    - Search by topic keywords
    - Filter by asset type (image/video)
    - Filter by grade level appropriateness
    - Discover reusable educational content
    """
    try:
        # Validate asset_type if provided
        if asset_type and asset_type not in ["image", "video"]:
            raise HTTPException(status_code=400, detail="Asset type must be 'image' or 'video'")
        
        visual_aids = await search_visual_aids(
            topic=topic,
            asset_type=asset_type,
            grade_level=grade_level,
            limit=limit
        )
        
        return [VisualAidSummary(**visual_aid) for visual_aid in visual_aids]
        
    except ValueError as e:
        logger.warning(f"Invalid search parameters: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching visual aids: {e}")
        raise HTTPException(status_code=500, detail="Failed to search visual aids")


@router.delete("/{visual_aid_id}", response_model=DeleteResponse, dependencies=[Depends(firebase_auth)])
async def delete_visual_aid_endpoint(
    visual_aid_id: str,
    req: Request
):
    """
    Delete a visual aid
    
    Removes a visual aid from the library:
    - Only owners can delete their visual aids
    - Teachers/admins have broader deletion permissions
    - Soft delete preserves data integrity
    """
    try:
        user_id = await get_current_user_id(req)
        
        result = await delete_visual_aid(visual_aid_id, user_id)
        
        return DeleteResponse(**result)
        
    except PermissionError as e:
        logger.warning(f"Permission denied for visual aid deletion: {e}")
        raise HTTPException(status_code=403, detail="Not authorized to delete this visual aid")
    except ValueError as e:
        logger.warning(f"Invalid input for visual aid deletion: {e}")
        raise HTTPException(status_code=404, detail="Visual aid not found")
    except Exception as e:
        logger.error(f"Error deleting visual aid: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete visual aid")


@router.get("/my-visual-aids", response_model=List[VisualAidSummary], dependencies=[Depends(firebase_auth)])
async def get_my_visual_aids(
    req: Request,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of visual aids to return"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type")
):
    """
    Get visual aids for the current authenticated user
    
    Convenience endpoint for users to view their own visual aid library
    """
    try:
        user_id = await get_current_user_id(req)
        
        # Validate asset_type if provided
        if asset_type and asset_type not in ["image", "video"]:
            raise HTTPException(status_code=400, detail="Asset type must be 'image' or 'video'")
        
        visual_aids = await get_user_visual_aids(user_id, limit, asset_type)
        
        return [VisualAidSummary(**visual_aid) for visual_aid in visual_aids]
        
    except Exception as e:
        logger.error(f"Error retrieving current user visual aids: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve your visual aids")


# Additional utility endpoints

@router.get("/categories", response_model=List[str], dependencies=[Depends(firebase_auth)])
async def get_visual_aid_categories(req: Request):
    """
    Get available visual aid categories/subjects
    
    Returns list of subject areas and categories for filtering
    """
    try:
        # In a real implementation, this would query the database for actual categories
        categories = [
            "Mathematics",
            "Science", 
            "History",
            "Geography",
            "Literature",
            "Art",
            "Music",
            "Physical Education",
            "Technology",
            "Language Arts",
            "Social Studies",
            "Environmental Science",
            "Biology",
            "Chemistry",
            "Physics"
        ]
        
        return categories
        
    except Exception as e:
        logger.error(f"Error retrieving categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")


@router.get("/stats/{user_id}", response_model=Dict[str, Any], dependencies=[Depends(firebase_auth)])
async def get_user_visual_aid_stats(
    user_id: str,
    req: Request
):
    """
    Get visual aid statistics for a user
    
    Returns usage statistics and analytics
    """
    try:
        # Check permissions
        current_user_id = await get_current_user_id(req)
        user_role = req.state.user.get("role", "student")
        
        if user_id != current_user_id and user_role not in ["teacher", "admin"]:
            raise HTTPException(status_code=403, detail="Can only view your own statistics")
        
        # Get user's visual aids for statistics
        visual_aids = await get_user_visual_aids(user_id, limit=1000)
        
        # Calculate statistics
        total_count = len(visual_aids)
        image_count = len([va for va in visual_aids if va.get("asset_type") == "image"])
        video_count = len([va for va in visual_aids if va.get("asset_type") == "video"])
        
        subjects = {}
        grade_levels = {}
        
        for va in visual_aids:
            subject = va.get("subject", "Other")
            subjects[subject] = subjects.get(subject, 0) + 1
            
            grade = va.get("grade_level")
            if grade:
                grade_levels[f"Grade {grade}"] = grade_levels.get(f"Grade {grade}", 0) + 1
        
        stats = {
            "total_visual_aids": total_count,
            "images_generated": image_count,
            "videos_generated": video_count,
            "subjects_covered": subjects,
            "grade_levels": grade_levels,
            "most_used_subject": max(subjects.items(), key=lambda x: x[1])[0] if subjects else None
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving visual aid stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")
