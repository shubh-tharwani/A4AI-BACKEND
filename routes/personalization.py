"""
Personalization Routes
Handles personalized learning recommendations and teacher dashboards
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import Dict, Any
from datetime import datetime
import logging

from auth_middleware import firebase_auth, get_current_user_id
from services.personalization_service import (
    get_student_dashboard,
    get_teacher_summary,
    get_user_recommendations
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/personalization", tags=["Personalization"])

# ===== REQUEST MODELS =====

class TeacherSummaryRequest(BaseModel):
    """Request model for teacher class summary"""
    class_id: str = Field(..., min_length=1, max_length=100, description="Class ID")
    
    @validator('class_id')
    def validate_class_id(cls, v):
        if not v.strip():
            raise ValueError('Class ID cannot be empty')
        return v.strip()

# ===== RESPONSE MODELS =====

class PersonalizationResponse(BaseModel):
    """Base response model for personalization endpoints"""
    status: str
    message: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]

# ===== ENDPOINTS =====

@router.get("/dashboard",
           summary="Get Student Dashboard",
           description="Get personalized learning dashboard with AI-powered recommendations",
           response_model=PersonalizationResponse,
           dependencies=[Depends(firebase_auth)])
async def get_dashboard(
    user_request: Request
) -> PersonalizationResponse:
    """
    Get personalized student dashboard with recommendations
    
    Returns AI-generated learning recommendations based on performance data
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        logger.info(f"Dashboard request from user: {user_id}")
        
        # Generate personalized dashboard
        dashboard_data = await get_student_dashboard(user_id)
        
        logger.info(f"Successfully generated dashboard for user: {user_id}")
        
        return PersonalizationResponse(
            status="success",
            message="Dashboard generated successfully",
            data=dashboard_data,
            metadata={
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "feature": "student_dashboard"
            }
        )
        
    except ValueError as e:
        logger.error(f"Validation error in dashboard generation: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating dashboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dashboard: {str(e)}"
        )

@router.get("/recommendations",
           summary="Get User Recommendations",
           description="Get existing personalized recommendations for a user",
           response_model=PersonalizationResponse,
           dependencies=[Depends(firebase_auth)])
async def get_recommendations(
    user_request: Request
) -> PersonalizationResponse:
    """
    Get existing personalized recommendations for the authenticated user
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        logger.info(f"Recommendations request from user: {user_id}")
        
        # Get existing recommendations
        recommendations = await get_user_recommendations(user_id)
        
        logger.info(f"Successfully retrieved recommendations for user: {user_id}")
        
        return PersonalizationResponse(
            status="success",
            message="Recommendations retrieved successfully",
            data=recommendations,
            metadata={
                "user_id": user_id,
                "retrieved_at": datetime.utcnow().isoformat(),
                "feature": "user_recommendations"
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting recommendations for user: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
        )

@router.post("/teacher-summary",
            summary="Get Teacher Class Summary",
            description="Get AI-powered class performance summary with intervention suggestions",
            response_model=PersonalizationResponse,
            dependencies=[Depends(firebase_auth)])
async def get_class_summary(
    request: TeacherSummaryRequest,
    user_request: Request
) -> PersonalizationResponse:
    """
    Get comprehensive class summary for teachers
    
    - **class_id**: ID of the class to analyze
    
    Returns AI-generated insights about class performance and suggested interventions
    """
    try:
        user_id = await get_current_user_id(user_request)
        user_role = user_request.state.user.get("role", "student")
        
        # Check if user has teacher/admin permissions
        if user_role not in ["teacher", "admin"]:
            logger.warning(f"User {user_id} (role: {user_role}) attempted to access teacher summary")
            raise HTTPException(
                status_code=403,
                detail="Teacher or admin role required to access class summaries"
            )
        
        logger.info(f"Teacher summary request for class {request.class_id} from user {user_id}")
        
        # Generate teacher summary
        summary_data = await get_teacher_summary(request.class_id)
        
        logger.info(f"Successfully generated teacher summary for class: {request.class_id}")
        
        return PersonalizationResponse(
            status="success",
            message="Teacher summary generated successfully",
            data=summary_data,
            metadata={
                "class_id": request.class_id,
                "requested_by": user_id,
                "user_role": user_role,
                "generated_at": datetime.utcnow().isoformat(),
                "feature": "teacher_summary"
            }
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in teacher summary: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating teacher summary for class {request.class_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate teacher summary: {str(e)}"
        )

@router.get("/health",
           summary="Personalization Service Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for the personalization service"""
    return {
        "status": "healthy",
        "service": "personalization",
        "message": "Personalization service is running properly",
        "features": [
            "student_dashboard",
            "teacher_summary",
            "ai_recommendations",
            "learning_insights"
        ],
        "endpoints": ["/dashboard", "/recommendations", "/teacher-summary"]
    }
