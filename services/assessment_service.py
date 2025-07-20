import os
import sys
import json
import vertexai
from vertexai.generative_models import GenerativeModel

# Add parent directory to path to import config.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Import the new DAO layer
from dao.assessment_dao import assessment_dao
from dao.user_dao import user_dao

# Import centralized error handling
from utils.dao_error_handler import handle_service_dao_errors, ensure_document_id

# Initialize Vertex AI
vertexai.init(project=config.PROJECT_ID, location=config.LOCATION)
model = GenerativeModel(config.GOOGLE_GEMINI_MODEL)

@handle_service_dao_errors("generate_quiz")
async def generate_quiz(grade: int, topic: str, language: str, user_id: str):
    """Generates a personalized, adaptive quiz with MCQs & open-ended questions."""
    try:
        # Get user performance using DAO
        performance_data = assessment_dao.get_user_performance(user_id)
        performance = performance_data.get("performance", {}) if performance_data else {}

        difficulty = recommend_next_difficulty(performance)

        prompt = f"""
        Create a {difficulty}-level quiz in {language} for Grade {grade} on topic "{topic}".
        Include 3 MCQs and 1 open-ended question with rubric.
        Output JSON in this structure:
        {{
          "questions": [
            {{
              "type": "mcq",
              "question": "...",
              "options": ["A", "B", "C", "D"],
              "correct_answer": "B",
              "difficulty": "{difficulty}"
            }},
            {{
              "type": "open-ended",
              "question": "...",
              "rubric": "..."
            }}
          ]
        }}
        """

        ai_response = model.generate_content(prompt)
        raw_text = ai_response.text.strip()

        # Handle potential markdown formatting
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").replace("json", "").strip()

        quiz = json.loads(raw_text)

        # Save assessment using DAO
        assessment_data = {
            "grade": grade,
            "topic": topic,
            "language": language,
            "difficulty": difficulty,
            "quiz": quiz,
            "status": "generated"
        }
        
        assessment_id = assessment_dao.save_assessment(user_id, assessment_data)
        ensure_document_id(assessment_id, "save_assessment")
        
        quiz["assessment_id"] = assessment_id
        return quiz
    except Exception as e:
        raise Exception(f"Error generating quiz: {str(e)}")

@handle_service_dao_errors("score_open_ended")
async def score_open_ended(answer: str, rubric: str):
    """Scores an open-ended response using LLM and rubric."""
    try:
        prompt = f"""
        Score this student's answer against the rubric. Provide a score out of 5 and feedback.
        Answer: {answer}
        Rubric: {rubric}
        Output JSON:
        {{ "score": <int>, "feedback": "<string>" }}
        """

        ai_response = model.generate_content(prompt)
        raw_text = ai_response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").replace("json", "").strip()

        result = json.loads(raw_text)
        return result
    except Exception as e:
        raise Exception(f"Error scoring open-ended question: {str(e)}")

@handle_service_dao_errors("update_user_performance")
async def update_user_performance(user_id: str, correct_count: int, total_questions: int):
    """Updates user performance using DAO."""
    try:
        # Update performance statistics using DAO
        success = assessment_dao.update_user_performance_stats(user_id, correct_count, total_questions)
        
        if not success:
            raise Exception("Failed to update performance statistics in database")
            
        # Get updated performance data
        performance_data = assessment_dao.get_user_performance(user_id)
        if performance_data is None:
            raise Exception("Failed to retrieve updated performance data")
            
        return {
            "status": "updated", 
            "performance": performance_data
        }
            
    except Exception as e:
        raise Exception(f"Error updating user performance: {str(e)}")

def recommend_next_difficulty(performance):
    """Adaptive difficulty based on performance history."""
    if not performance:
        return "easy"
    
    # Check for new performance data structure
    if "average_score" in performance:
        average_score = performance.get("average_score", 50.0)
        if average_score > 80:
            return "hard"
        elif average_score < 40:
            return "easy"
        return "medium"
    else:
        # Legacy support for correct_ratio
        correct_ratio = performance.get("correct_ratio", 0.5)
        if correct_ratio > 0.8:
            return "hard"
        elif correct_ratio < 0.4:
            return "easy"
        return "medium"

async def get_personalized_recommendations(user_id: str):
    """Fetch past performance and suggest next learning path using DAO."""
    try:
        # Get performance data using DAO
        performance_data = assessment_dao.get_user_performance(user_id)
        performance = performance_data if performance_data else {}

        difficulty = recommend_next_difficulty(performance)
        
        # Get recent assessments for more detailed recommendations
        recent_assessments = assessment_dao.get_user_assessments(user_id, limit=5)
        if recent_assessments is None:
            raise Exception("Failed to retrieve recent assessments from database")
        
        return {
            "recommended_difficulty": difficulty,
            "performance": performance,
            "recent_assessments": len(recent_assessments),
            "recommendations": {
                "next_steps": f"Try {difficulty} difficulty questions",
                "focus_areas": "Continue practicing to improve"
            }
        }
    except Exception as e:
        raise Exception(f"Error getting personalized recommendations: {str(e)}")

@handle_service_dao_errors("save_assessment_result")
def save_assessment_result(user_id: str, assessment_data: dict):
    """Save assessment result using DAO"""
    try:
        assessment_id = assessment_dao.save_assessment(user_id, assessment_data)
        ensure_document_id(assessment_id, "save_assessment_result")
        return {"success": True, "assessment_id": assessment_id}
    except Exception as e:
        raise Exception(f"Error saving assessment result: {str(e)}")

@handle_service_dao_errors("get_assessment_history")
def get_assessment_history(user_id: str):
    """Retrieve user's assessment history using DAO"""
    try:
        assessments = assessment_dao.get_user_assessments(user_id)
        return {"success": True, "assessments": assessments}
    except Exception as e:
        raise Exception(f"Error retrieving assessment history: {str(e)}")
