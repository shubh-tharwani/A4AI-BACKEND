from fastapi import APIRouter, Query, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from auth_middleware import firebase_auth
from services.assessment_service import (
    generate_quiz, score_open_ended, update_user_performance, get_personalized_recommendations
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Response models for better API documentation
class BaseResponse(BaseModel):
    """Base response model"""
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")

class QuizResponse(BaseResponse):
    """Response model for quiz generation"""
    quiz: Dict[str, Any] = Field(..., description="Generated quiz data")
    metadata: Dict[str, Any] = Field(..., description="Generation metadata")

class ScoreResponse(BaseResponse):
    """Response model for scoring"""
    result: Dict[str, Any] = Field(..., description="Scoring results")
    metadata: Dict[str, Any] = Field(..., description="Scoring metadata")

class PerformanceResponse(BaseResponse):
    """Response model for performance updates"""
    result: Dict[str, Any] = Field(..., description="Performance update results")
    metadata: Dict[str, Any] = Field(..., description="Performance metadata")

class RecommendationResponse(BaseResponse):
    """Response model for personalized recommendations"""
    data: Dict[str, Any] = Field(..., description="Recommendation data")
    metadata: Dict[str, Any] = Field(..., description="Recommendation metadata")

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    message: str = Field(..., description="Health status message")

router = APIRouter(
    prefix="/assessment", 
    tags=["Assessment"], 
    dependencies=[Depends(firebase_auth)],
    responses={
        500: {"description": "Internal server error"},
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden"}
    }
)

class OpenEndedRequest(BaseModel):
    """Request model for scoring open-ended questions"""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    answer: str = Field(..., min_length=1, max_length=5000, description="Student's answer to the open-ended question")
    rubric: str = Field(..., min_length=10, max_length=2000, description="Scoring rubric for the question")
    
    @field_validator('answer')
    @classmethod
    def validate_answer(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Answer cannot be empty or whitespace only')
        return v.strip()

class UpdatePerformanceRequest(BaseModel):
    """Request model for updating user performance metrics"""
    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)
    
    user_id: str = Field(..., min_length=1, max_length=100, description="Unique user identifier")
    correct_count: int = Field(..., ge=0, description="Number of correct answers")
    total_questions: int = Field(..., gt=0, description="Total number of questions")
    
    @field_validator('correct_count')
    @classmethod
    def validate_correct_count(cls, v: int, info) -> int:
        if hasattr(info, 'data') and 'total_questions' in info.data and v > info.data['total_questions']:
            raise ValueError('Correct count cannot exceed total questions')
        return v

class QuizGenerationRequest(BaseModel):
    """Request model for generating personalized quizzes"""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, use_enum_values=True)
    
    grade: int = Field(..., ge=1, le=12, description="Grade level (1-12)")
    topic: str = Field(..., min_length=2, max_length=200, description="Topic for the quiz")
    language: str = Field(default="English", min_length=2, max_length=50, description="Language for the quiz")
    difficulty: Optional[str] = Field(default=None, pattern=r"^(easy|medium|hard)$", description="Optional difficulty override")
    question_count: Optional[int] = Field(default=4, ge=1, le=20, description="Number of questions to generate")
    
    @field_validator('topic')
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Topic cannot be empty or whitespace only')
        return v.strip()

@router.post(
    "/generate", 
    summary="Generate Personalized Quiz", 
    description="Creates a personalized quiz based on student's grade, topic, and performance history",
    response_model=QuizResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Quiz generated successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Quiz generation failed"}
    }
)
async def generate_assessment(
    request: QuizGenerationRequest,
    user_request: Request
) -> QuizResponse:
    """
    Generate a personalized quiz for a student
    
    - **grade**: Student's grade level (1-12)
    - **topic**: Subject topic for the quiz
    - **language**: Language for the quiz (default: English)
    - **difficulty**: Optional difficulty override (easy/medium/hard)
    - **question_count**: Number of questions to generate (1-20)
    """
    user_id = None
    try:
        # Get user ID from authenticated request
        user_id = user_request.state.user.get("uid", "")
        if not user_id:
            logger.warning("Generate quiz attempt without user ID in token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="User ID not found in authentication token"
            )
        
        logger.info(
            f"Quiz generation request from user {user_id}: "
            f"Grade {request.grade}, Topic: {request.topic}, "
            f"Language: {request.language}, Difficulty: {request.difficulty}"
        )
        
        # Generate quiz using the service
        quiz = await generate_quiz(
            grade=request.grade,
            topic=request.topic,
            language=request.language,
            user_id=user_id
        )
        
        # Validate quiz structure
        if not quiz or not quiz.get('questions'):
            logger.error(f"Quiz generation returned invalid structure for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Quiz generation returned invalid structure"
            )
        
        logger.info(f"Successfully generated quiz for user {user_id} with {len(quiz.get('questions', []))} questions")
        
        return QuizResponse(
            status="success",
            message="Quiz generated successfully",
            quiz=quiz,
            metadata={
                "grade": request.grade,
                "topic": request.topic,
                "language": request.language,
                "user_id": user_id,
                "question_count": len(quiz.get('questions', [])),
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error during quiz generation: {str(e)}"
        logger.error(f"Error generating quiz for user {user_id or 'unknown'}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@router.post(
    "/score", 
    summary="Score Open-Ended Answer", 
    description="Score a student's open-ended answer using AI and provided rubric",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Answer scored successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Scoring failed"}
    }
)
async def score_open_ended_api(request: OpenEndedRequest, user_request: Request) -> ScoreResponse:
    """
    Score an open-ended answer using AI evaluation
    
    - **answer**: Student's written answer
    - **rubric**: Scoring criteria and rubric
    """
    user_id = None
    try:
        user_id = user_request.state.user.get("uid", "")
        if not user_id:
            logger.warning("Score attempt without user ID in token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID not found in authentication token"
            )
            
        logger.info(f"Scoring open-ended answer for user {user_id} (answer length: {len(request.answer)} chars)")
        
        result = await score_open_ended(request.answer, request.rubric)
        
        # Validate result structure
        if not result or "score" not in result:
            logger.error(f"Scoring returned invalid structure for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Answer scoring returned invalid structure"
            )
        
        logger.info(f"Successfully scored answer for user {user_id} - Score: {result.get('score', 'N/A')}")
        
        return ScoreResponse(
            status="success",
            message="Answer scored successfully",
            result=result,
            metadata={
                "user_id": user_id,
                "answer_length": len(request.answer),
                "rubric_length": len(request.rubric),
                "scored_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error during scoring: {str(e)}"
        logger.error(f"Error scoring answer for user {user_id or 'unknown'}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@router.post(
    "/update-performance", 
    summary="Update User Performance", 
    description="Update student's performance metrics after completing an assessment",
    response_model=PerformanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Performance updated successfully"},
        400: {"description": "Invalid request parameters"},
        403: {"description": "Cannot update performance for another user"},
        500: {"description": "Performance update failed"}
    }
)
async def update_performance_api(request: UpdatePerformanceRequest, user_request: Request) -> PerformanceResponse:
    """
    Update student's performance metrics
    
    - **user_id**: Student's unique identifier
    - **correct_count**: Number of questions answered correctly
    - **total_questions**: Total number of questions in the assessment
    """
    authenticated_user_id = None
    try:
        authenticated_user_id = user_request.state.user.get("uid", "")
        if not authenticated_user_id:
            logger.warning("Performance update attempt without user ID in token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID not found in authentication token"
            )
        
        # Ensure user can only update their own performance or is an admin
        if request.user_id != authenticated_user_id:
            user_role = user_request.state.user.get("role", "student")
            if user_role not in ["admin", "teacher"]:
                logger.warning(
                    f"User {authenticated_user_id} (role: {user_role}) attempted to update "
                    f"performance for user {request.user_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Cannot update performance for another user"
                )
        
        accuracy = round((request.correct_count / request.total_questions) * 100, 2)
        logger.info(
            f"Updating performance for user {request.user_id}: "
            f"{request.correct_count}/{request.total_questions} ({accuracy}%)"
        )
        
        result = await update_user_performance(
            request.user_id, 
            request.correct_count, 
            request.total_questions
        )
        
        # Validate result structure
        if not result or "status" not in result:
            logger.error(f"Performance update returned invalid structure for user {request.user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Performance update returned invalid structure"
            )
        
        logger.info(f"Successfully updated performance for user {request.user_id}")
        
        return PerformanceResponse(
            status="success",
            message="Performance updated successfully",
            result=result,
            metadata={
                "user_id": request.user_id,
                "accuracy": accuracy,
                "correct_count": request.correct_count,
                "total_questions": request.total_questions,
                "updated_by": authenticated_user_id,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error during performance update: {str(e)}"
        logger.error(f"Error updating performance for user {request.user_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@router.get(
    "/personalized", 
    summary="Get Personalized Recommendations", 
    description="Get AI-powered learning recommendations based on student's performance history",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Recommendations generated successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Recommendation generation failed"}
    }
)
async def personalized_learning(user_request: Request) -> RecommendationResponse:
    """
    Get personalized learning recommendations for the authenticated student
    
    Returns recommendations based on performance history, strengths, and areas for improvement
    """
    user_id = None
    try:
        user_id = user_request.state.user.get("uid", "")
        if not user_id:
            logger.warning("Personalized recommendations request without user ID in token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="User ID not found in authentication token"
            )
        
        logger.info(f"Generating personalized recommendations for user {user_id}")
        
        result = await get_personalized_recommendations(user_id)
        
        # Validate result structure
        if not result or "recommended_difficulty" not in result:
            logger.error(f"Recommendation generation returned invalid structure for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Recommendation generation returned invalid structure"
            )
        
        logger.info(f"Successfully generated recommendations for user {user_id}")
        
        return RecommendationResponse(
            status="success",
            message="Personalized recommendations generated successfully",
            data=result,
            metadata={
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "recommendation_type": "performance_based"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error during recommendation generation: {str(e)}"
        logger.error(f"Error getting recommendations for user {user_id or 'unknown'}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@router.get(
    "/health", 
    summary="Assessment Service Health Check", 
    description="Health check endpoint for the assessment service",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[], 
    tags=["Health"]
)
async def health_check() -> HealthResponse:
    """Health check endpoint for the assessment service"""
    return HealthResponse(
        status="healthy",
        service="assessment",
        message="Assessment service is running properly"
    )

@router.get(
    "/analytics",
    summary="Get User Assessment Analytics",
    description="Get comprehensive analytics for user's assessment performance",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Analytics retrieved successfully"},
        400: {"description": "Invalid request parameters"},
        500: {"description": "Analytics retrieval failed"}
    }
)
async def get_user_analytics(
    user_request: Request,
    days: Optional[int] = Query(default=30, ge=1, le=365, description="Number of days to analyze")
) -> Dict[str, Any]:
    """
    Get comprehensive assessment analytics for the authenticated user
    
    - **days**: Number of days to include in analytics (default: 30)
    """
    user_id = None
    try:
        user_id = user_request.state.user.get("uid", "")
        if not user_id:
            logger.warning("Analytics request without user ID in token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID not found in authentication token"
            )
        
        logger.info(f"Generating analytics for user {user_id} (last {days} days)")
        
        # This would be implemented in the assessment service
        # For now, return a placeholder structure
        analytics_data = {
            "user_id": user_id,
            "period": f"last_{days}_days",
            "total_assessments": 0,
            "average_score": 0.0,
            "improvement_trend": "stable",
            "subject_performance": {},
            "difficulty_distribution": {
                "easy": 0,
                "medium": 0,
                "hard": 0
            },
            "time_spent_minutes": 0,
            "completion_rate": 0.0
        }
        
        return {
            "status": "success",
            "message": f"Analytics retrieved for last {days} days",
            "data": analytics_data,
            "metadata": {
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "period_days": days
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error during analytics generation: {str(e)}"
        logger.error(f"Error getting analytics for user {user_id or 'unknown'}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
