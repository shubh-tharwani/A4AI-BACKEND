"""
Assessment Routes
FastAPI routes for AI-powered quiz generation, scoring, and personalized learning recommendations
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from services.assessment_service import (
    generate_quiz,
    score_open_ended,
    update_user_performance,
    get_personalized_recommendations
)
from auth_middleware import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assessment", tags=["Assessment"])


# Request Models
class QuizRequest(BaseModel):
    grade: int = Field(..., ge=1, le=12, description="Grade level (1-12)")
    topic: str = Field(..., min_length=1, description="Quiz topic")
    language: str = Field("English", description="Language for the quiz")


class ScoreRequest(BaseModel):
    answer: str = Field(..., min_length=1, description="Student's answer")
    rubric: str = Field(..., min_length=1, description="Scoring rubric")


class PerformanceUpdateRequest(BaseModel):
    correct_count: int = Field(..., ge=0, description="Number of correct answers")
    total_questions: int = Field(..., ge=1, description="Total number of questions")


# Routes

@router.post("/quiz")
async def create_quiz(
    request: QuizRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate AI-powered quiz with MCQs and open-ended questions
    
    Creates personalized quizzes based on:
    - Grade level
    - Topic area
    - Language preference
    - User's learning history
    """
    try:
        user_id = current_user.get("uid")
        
        quiz_data = await generate_quiz(
            grade=request.grade,
            topic=request.topic,
            language=request.language,
            user_id=user_id
        )
        
        return quiz_data
        
    except ValueError as e:
        logger.warning(f"Invalid input for quiz generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate quiz")


@router.post("/score")
async def score_answer(request: ScoreRequest):
    """
    Score open-ended answers using AI
    
    Provides intelligent scoring for open-ended responses based on:
    - Answer content analysis
    - Rubric compliance
    - Context understanding
    """
    try:
        score_result = await score_open_ended(
            answer=request.answer,
            rubric=request.rubric
        )
        
        return score_result
        
    except ValueError as e:
        logger.warning(f"Invalid input for answer scoring: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error scoring answer: {e}")
        raise HTTPException(status_code=500, detail="Failed to score answer")


@router.post("/performance")
async def update_performance(
    request: PerformanceUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update user performance metrics
    
    Tracks learning progress by:
    - Recording quiz scores
    - Updating performance analytics
    - Enabling personalized recommendations
    """
    try:
        user_id = current_user.get("uid")
        
        result = await update_user_performance(
            user_id=user_id,
            correct_count=request.correct_count,
            total_questions=request.total_questions
        )
        
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid input for performance update: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to update performance")


@router.get("/recommendations")
async def get_recommendations(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get personalized learning recommendations
    
    Provides AI-powered suggestions based on:
    - Performance history
    - Learning patterns
    - Knowledge gaps
    - Strength areas
    """
    try:
        user_id = current_user.get("uid")
        
        recommendations = await get_personalized_recommendations(user_id)
        
        return recommendations
        
    except ValueError as e:
        logger.warning(f"Invalid input for recommendations: {e}")
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")
