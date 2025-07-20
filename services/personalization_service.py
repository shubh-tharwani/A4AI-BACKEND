"""
Personalization Service
Provides personalized learning recommendations and dashboard functionality
"""
import json
import logging
from typing import Dict, Any, List, Optional

from services.vertex_ai import vertex_ai_service
from dao.personalization_dao import personalization_dao
from utils.dao_error_handler import handle_service_dao_errors, ensure_document_id

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@handle_service_dao_errors("get_student_dashboard")
async def get_student_dashboard(user_id: str) -> Dict[str, Any]:
    """
    Generate personalized student dashboard with AI-powered recommendations
    
    Args:
        user_id (str): Student user ID
        
    Returns:
        Dict[str, Any]: Dashboard data with recommendations and motivation
        
    Raises:
        Exception: If user data not found or AI processing fails
    """
    if not user_id or not user_id.strip():
        raise ValueError("User ID is required and cannot be empty")
    
    logger.info(f"Generating student dashboard for user: {user_id}")
    
    # Fetch performance data using DAO
    performance_data = personalization_dao.get_user_performance(user_id)
    if not performance_data:
        raise Exception(f"User performance data not found for user: {user_id}")
    
    # Get user profile for additional context
    user_profile = personalization_dao.get_user_profile(user_id)
    
    # Prepare AI prompt with comprehensive context
    context_data = {
        "performance": performance_data,
        "profile": user_profile or {},
        "user_id": user_id
    }
    
    prompt = f"""
    Analyze the following student data and provide personalized learning recommendations:
    
    Student Data:
    {json.dumps(context_data, indent=2)}
    
    Provide a JSON response with:
    {{
      "recommendations": [
        {{
          "title": "Specific Activity Name",
          "description": "Detailed description of what the student should do",
          "type": "visual|audio|text|interactive",
          "difficulty": "easy|medium|hard",
          "estimated_time": "time in minutes",
          "subject": "subject area"
        }}
      ],
      "motivation_message": "Personalized encouraging message based on their progress",
      "learning_insights": [
        "Key insight about their learning pattern",
        "Another insight about strengths or areas to improve"
      ],
      "next_goals": [
        "Specific achievable goal",
        "Another goal to work towards"
      ]
    }}
    
    Make recommendations specific to their performance data and learning gaps.
    """
    
    # Get AI model and generate recommendations
    ai_response_text = vertex_ai_service.generate_educational_content(prompt, "recommendations")
    
    try:
        # Parse AI response
        response_text = ai_response_text.strip()
        # Clean up potential markdown formatting
        if response_text.startswith("```"):
            response_text = response_text.strip("`").replace("json", "").strip()
        
        structured_output = json.loads(response_text)
        logger.info(f"Generated AI recommendations for user: {user_id}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response for user {user_id}: {e}")
        # Provide fallback response
        structured_output = {
            "recommendations": [
                {
                    "title": "Continue Learning",
                    "description": "Keep practicing to improve your skills",
                    "type": "text",
                    "difficulty": "medium",
                    "estimated_time": "30",
                    "subject": "General"
                }
            ],
            "motivation_message": "Keep up the great work! Every step forward is progress.",
            "learning_insights": ["You're making steady progress"],
            "next_goals": ["Continue practicing regularly"]
        }
    
    # Save recommendations to database
    recommendation_id = personalization_dao.save_recommendations(user_id, structured_output)
    ensure_document_id(recommendation_id, "save_recommendations")
    
    # Add metadata
    structured_output["metadata"] = {
        "user_id": user_id,
        "generated_at": performance_data.get("updated_at", "unknown"),
        "recommendation_id": recommendation_id
    }
    
    logger.info(f"Successfully generated dashboard for user: {user_id}")
    return structured_output

@handle_service_dao_errors("get_teacher_summary")
async def get_teacher_summary(class_id: str) -> Dict[str, Any]:
    """
    Generate teacher summary for class performance with AI insights
    
    Args:
        class_id (str): Class ID
        
    Returns:
        Dict[str, Any]: Class summary with insights and intervention suggestions
        
    Raises:
        Exception: If class data not found or AI processing fails
    """
    if not class_id or not class_id.strip():
        raise ValueError("Class ID is required and cannot be empty")
    
    logger.info(f"Generating teacher summary for class: {class_id}")
    
    # Fetch class performance data using DAO
    class_data = personalization_dao.get_class_performance(class_id)
    if not class_data:
        raise Exception(f"No student data found for class: {class_id}")
    
    prompt = f"""
    Analyze this class performance data and provide teacher insights:
    
    Class Data ({len(class_data)} students):
    {json.dumps(class_data, indent=2)}
    
    Provide a JSON response with:
    {{
      "class_summary": "Overall class performance summary",
      "student_count": {len(class_data)},
      "average_performance": "percentage or description",
      "top_performing_students": ["student_id1", "student_id2"],
      "struggling_students": ["student_id1", "student_id2"],
      "top_struggling_topics": ["topic1", "topic2", "topic3"],
      "class_strengths": ["strength1", "strength2"],
      "intervention_suggestions": [
        {{
          "strategy": "Intervention strategy name",
          "description": "Detailed description",
          "target_students": "all|struggling|specific",
          "estimated_impact": "high|medium|low"
        }}
      ],
      "recommended_activities": [
        {{
          "activity": "Activity name",
          "topic": "Subject area",
          "difficulty": "easy|medium|hard",
          "group_size": "individual|small|large"
        }}
      ]
    }}
    
    Focus on actionable insights and specific recommendations for the teacher.
    """
    
    # Get AI model and generate summary
    ai_response_text = vertex_ai_service.generate_educational_content(prompt, "summary")
    
    try:
        # Parse AI response
        response_text = ai_response_text.strip()
        if response_text.startswith("```"):
            response_text = response_text.strip("`").replace("json", "").strip()
        
        structured_output = json.loads(response_text)
        logger.info(f"Generated AI teacher summary for class: {class_id}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response for class {class_id}: {e}")
        # Provide fallback response
        structured_output = {
            "class_summary": f"Class analysis for {len(class_data)} students",
            "student_count": len(class_data),
            "average_performance": "Data analysis in progress",
            "top_performing_students": [],
            "struggling_students": [],
            "top_struggling_topics": ["Analysis pending"],
            "class_strengths": ["Diverse learning styles"],
            "intervention_suggestions": [
                {
                    "strategy": "Individual Assessment",
                    "description": "Review individual student performance",
                    "target_students": "all",
                    "estimated_impact": "medium"
                }
            ],
            "recommended_activities": [
                {
                    "activity": "Review Session",
                    "topic": "General",
                    "difficulty": "medium",
                    "group_size": "large"
                }
            ]
        }
    
    # Add metadata
    structured_output["metadata"] = {
        "class_id": class_id,
        "analysis_date": "2025-07-20",
        "data_points": len(class_data)
    }
    
    logger.info(f"Successfully generated teacher summary for class: {class_id}")
    return structured_output

@handle_service_dao_errors("get_user_recommendations")
async def get_user_recommendations(user_id: str) -> Dict[str, Any]:
    """
    Get existing recommendations for a user
    
    Args:
        user_id (str): User ID
        
    Returns:
        Dict[str, Any]: Existing recommendations or empty structure
    """
    if not user_id or not user_id.strip():
        raise ValueError("User ID is required and cannot be empty")
    
    logger.info(f"Retrieving recommendations for user: {user_id}")
    
    recommendations = personalization_dao.get_user_recommendations(user_id)
    if not recommendations:
        logger.info(f"No existing recommendations found for user: {user_id}")
        return {
            "recommendations": [],
            "motivation_message": "Welcome! Complete some assessments to get personalized recommendations.",
            "learning_insights": [],
            "next_goals": [],
            "metadata": {
                "user_id": user_id,
                "status": "no_data"
            }
        }
    
    logger.info(f"Retrieved existing recommendations for user: {user_id}")
    return recommendations
