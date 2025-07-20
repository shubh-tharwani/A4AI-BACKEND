"""
Activities Service
Handles generation of interactive stories, AR/VR content, and badge management
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from google.cloud import texttospeech

from dao.activities_dao import activities_dao
from services.vertex_ai import vertex_ai_service
from utils.dao_error_handler import handle_service_dao_errors, ensure_document_id
from config import PROJECT_ID

logger = logging.getLogger(__name__)

# Initialize TTS client
tts_client = texttospeech.TextToSpeechClient()

# Audio files directory configuration
AUDIO_FILES_DIR = os.path.join(os.getcwd(), "activities_audio")
os.makedirs(AUDIO_FILES_DIR, exist_ok=True)


@handle_service_dao_errors("generate_interactive_story")
async def generate_interactive_story(grade: int, topic: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a voice-enabled interactive story with embedded quizzes
    
    Args:
        grade (int): Grade level for the story
        topic (str): Educational topic for the story
        user_id (str, optional): User ID for tracking
        
    Returns:
        Dict[str, Any]: Generated story data with audio file information
        
    Raises:
        ServiceError: If story generation fails
        DAOError: If database operations fail
    """
    logger.info(f"Generating interactive story for grade {grade}, topic: {topic}")
    
    # Validate inputs
    if not isinstance(grade, int) or grade < 1 or grade > 12:
        raise ValueError("Grade must be an integer between 1 and 12")
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty")
    
    try:
        # Enhanced prompt with better structure and educational guidelines
        prompt = f"""
        Create an engaging educational interactive story for grade {grade} students about '{topic}'.
        
        Requirements:
        - Age-appropriate language and content for grade {grade}
        - Educational value aligned with curriculum standards
        - Interactive elements that encourage participation
        - Clear learning objectives
        
        Story Structure:
        - Compelling introduction with relatable characters
        - Educational content seamlessly integrated into narrative
        - 2-3 interactive quiz questions at natural story points
        - Encouraging and positive tone throughout
        - Maximum 500 words for optimal attention span
        
        Format as valid JSON:
        {{
          "title": "Engaging story title",
          "learning_objectives": ["objective 1", "objective 2"],
          "story_text": "Complete story narrative with natural quiz insertion points",
          "quizzes": [
            {{
              "question": "Clear, grade-appropriate question",
              "options": ["Option A", "Option B", "Option C"],
              "answer": "A",
              "explanation": "Why this answer is correct"
            }}
          ],
          "vocabulary_words": ["word1", "word2"],
          "grade_level": {grade},
          "subject": "Primary subject area"
        }}
        """
        
        # Use centralized Vertex AI service
        response = await vertex_ai_service.generate_content(prompt)
        
        # Parse and validate response
        story_data = _parse_story_response(response, grade, topic)
        
        # Generate audio file
        audio_filename = await _generate_story_audio(story_data["story_text"])
        
        # Prepare data for database storage
        activity_data = {
            "title": story_data["title"],
            "story_text": story_data["story_text"],
            "quizzes": story_data["quizzes"],
            "learning_objectives": story_data.get("learning_objectives", []),
            "vocabulary_words": story_data.get("vocabulary_words", []),
            "audio_file": audio_filename,
            "grade_level": grade,
            "topic": topic,
            "subject": story_data.get("subject", topic),
            "type": "interactive_story",
            "user_id": user_id
        }
        
        # Save to database using DAO
        story_id = activities_dao.save_interactive_story(activity_data)
        
        # Return response with generated content
        result = {
            "story_id": story_id,
            "title": story_data["title"],
            "story_text": story_data["story_text"],
            "quizzes": story_data["quizzes"],
            "learning_objectives": story_data.get("learning_objectives", []),
            "vocabulary_words": story_data.get("vocabulary_words", []),
            "audio_filename": audio_filename,
            "grade_level": grade,
            "topic": topic
        }
        
        logger.info(f"Successfully generated interactive story: {story_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating interactive story: {e}")
        # Return fallback response
        fallback_story = _create_fallback_story(grade, topic)
        return fallback_story


@handle_service_dao_errors("generate_ar_prompt")
async def generate_ar_scene(topic: str, grade_level: Optional[int] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate AR/VR scene description for Unity or WebXR
    
    Args:
        topic (str): Educational topic for AR scene
        grade_level (int, optional): Grade level for age-appropriate content
        user_id (str, optional): User ID for tracking
        
    Returns:
        Dict[str, Any]: AR scene configuration data
        
    Raises:
        ServiceError: If scene generation fails
        DAOError: If database operations fail
    """
    logger.info(f"Generating AR scene for topic: {topic}, grade: {grade_level}")
    
    # Validate inputs
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty")
    
    try:
        # Enhanced prompt for AR/VR scene generation
        grade_context = f" for grade {grade_level} students" if grade_level else ""
        
        prompt = f"""
        Create a detailed AR/VR educational scene concept for teaching '{topic}'{grade_context}.
        
        Requirements:
        - Immersive 3D environment that enhances learning
        - Interactive elements that encourage exploration
        - Age-appropriate complexity and safety considerations
        - Clear educational objectives and outcomes
        - Technical feasibility for Unity/WebXR implementation
        
        Include:
        - Detailed environment description with lighting and atmosphere
        - Specific 3D objects, models, and assets needed
        - Interactive mechanics and user interactions
        - Learning activities and challenges within the scene
        - Assessment opportunities embedded in interactions
        - Accessibility considerations
        
        Format as valid JSON:
        {{
          "scene_name": "Descriptive scene name",
          "educational_objective": "Clear learning goal",
          "environment": {{
            "setting": "Detailed environment description",
            "lighting": "Lighting setup description",
            "atmosphere": "Mood and ambiance details",
            "size_scale": "Recommended scene dimensions"
          }},
          "objects": [
            {{
              "name": "Object name",
              "description": "Detailed description",
              "interactions": ["possible interactions"],
              "learning_purpose": "Educational value"
            }}
          ],
          "interactions": [
            {{
              "type": "interaction type",
              "description": "How users interact",
              "learning_outcome": "What students learn",
              "feedback_mechanism": "How progress is shown"
            }}
          ],
          "technical_requirements": [
            "Unity version compatibility",
            "Required plugins/packages",
            "Performance considerations"
          ],
          "assessment_opportunities": ["How to measure learning"],
          "grade_level": {grade_level or "flexible"},
          "subject_area": "Primary educational domain"
        }}
        """
        
        # Use centralized Vertex AI service
        response = await vertex_ai_service.generate_content(prompt)
        
        # Parse and validate response
        scene_data = _parse_ar_response(response, topic, grade_level)
        
        # Prepare data for database storage
        ar_scene_data = {
            **scene_data,
            "topic": topic,
            "grade_level": grade_level,
            "user_id": user_id,
            "type": "ar_scene"
        }
        
        # Save to database using DAO
        scene_id = activities_dao.save_ar_scene(ar_scene_data)
        
        # Add scene_id to result
        result = {
            "scene_id": scene_id,
            **scene_data
        }
        
        logger.info(f"Successfully generated AR scene: {scene_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating AR scene: {e}")
        # Return fallback response
        return _create_fallback_ar_scene(topic, grade_level)


@handle_service_dao_errors("assign_badge")
async def assign_badge(user_id: str, badge_name: str, criteria_met: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Assign a badge to a user with detailed tracking
    
    Args:
        user_id (str): User ID to assign badge to
        badge_name (str): Name of the badge to assign
        criteria_met (Dict[str, Any], optional): Criteria that were met for this badge
        
    Returns:
        Dict[str, Any]: Badge assignment result
        
    Raises:
        ServiceError: If badge assignment fails
        DAOError: If database operations fail
    """
    logger.info(f"Assigning badge '{badge_name}' to user: {user_id}")
    
    # Validate inputs
    user_id = ensure_document_id(user_id, "user_id")
    if not badge_name or not badge_name.strip():
        raise ValueError("Badge name cannot be empty")
    
    try:
        # Check if user already has this badge to prevent duplicates
        existing_badges = activities_dao.get_user_badges(user_id)
        for badge in existing_badges:
            if badge.get("badge") == badge_name:
                logger.warning(f"User {user_id} already has badge '{badge_name}'")
                return {
                    "status": "already_exists",
                    "badge": badge_name,
                    "message": f"Badge '{badge_name}' already assigned to user"
                }
        
        # Prepare badge data with enhanced metadata
        badge_data = {
            "badge": badge_name,
            "criteria_met": criteria_met or {},
            "badge_type": _determine_badge_type(badge_name),
            "points_earned": _calculate_badge_points(badge_name),
            "description": _get_badge_description(badge_name),
            "rarity": _get_badge_rarity(badge_name)
        }
        
        # Save badge assignment using DAO
        badge_id = activities_dao.assign_user_badge(user_id, badge_data)
        
        result = {
            "status": "success",
            "badge_id": badge_id,
            "badge": badge_name,
            "points_earned": badge_data["points_earned"],
            "message": f"Badge '{badge_name}' successfully assigned!"
        }
        
        logger.info(f"Successfully assigned badge '{badge_name}' to user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error assigning badge to user {user_id}: {e}")
        raise


# Additional service functions for retrieving data

@handle_service_dao_errors("get_user_badges")
async def get_user_badges(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all badges for a user
    
    Args:
        user_id (str): User ID
        
    Returns:
        List[Dict[str, Any]]: List of user badges with metadata
    """
    user_id = ensure_document_id(user_id, "user_id")
    
    badges = activities_dao.get_user_badges(user_id)
    
    # Enhance badges with additional metadata
    enhanced_badges = []
    for badge in badges:
        enhanced_badge = {
            **badge,
            "display_name": _get_badge_display_name(badge.get("badge", "")),
            "icon_url": _get_badge_icon_url(badge.get("badge", "")),
            "achievement_date": badge.get("assigned_at", "").split("T")[0] if badge.get("assigned_at") else None
        }
        enhanced_badges.append(enhanced_badge)
    
    return enhanced_badges


@handle_service_dao_errors("get_user_activities")
async def get_user_activities(user_id: str, limit: int = 10, activity_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get recent activities for a user
    
    Args:
        user_id (str): User ID
        limit (int): Maximum number of activities to retrieve
        activity_type (str, optional): Filter by activity type
        
    Returns:
        List[Dict[str, Any]]: List of user activities
    """
    user_id = ensure_document_id(user_id, "user_id")
    
    activities = activities_dao.get_user_activities(user_id, limit)
    
    # Filter by type if specified
    if activity_type:
        activities = [activity for activity in activities if activity.get("type") == activity_type]
    
    return activities


# Helper functions

def _parse_story_response(response: str, grade: int, topic: str) -> Dict[str, Any]:
    """Parse and validate story response from AI"""
    try:
        story_data = json.loads(response)
        
        # Ensure required fields exist
        if "title" not in story_data:
            story_data["title"] = f"Learning Adventure: {topic}"
        if "story_text" not in story_data:
            story_data["story_text"] = f"Let's explore the wonderful world of {topic}!"
        if "quizzes" not in story_data:
            story_data["quizzes"] = []
            
        return story_data
        
    except json.JSONDecodeError:
        logger.warning("Failed to parse story response as JSON, creating fallback")
        return _create_fallback_story_data(grade, topic)


def _parse_ar_response(response: str, topic: str, grade_level: Optional[int]) -> Dict[str, Any]:
    """Parse and validate AR scene response from AI"""
    try:
        scene_data = json.loads(response)
        
        # Ensure required fields exist
        if "scene_name" not in scene_data:
            scene_data["scene_name"] = f"Explore {topic}"
        if "environment" not in scene_data:
            scene_data["environment"] = {"setting": f"A 3D learning environment for {topic}"}
        if "objects" not in scene_data:
            scene_data["objects"] = []
        if "interactions" not in scene_data:
            scene_data["interactions"] = []
            
        return scene_data
        
    except json.JSONDecodeError:
        logger.warning("Failed to parse AR response as JSON, creating fallback")
        return _create_fallback_ar_data(topic, grade_level)


async def _generate_story_audio(story_text: str) -> str:
    """Generate audio file for story text"""
    try:
        # Prepare TTS request
        synthesis_input = texttospeech.SynthesisInput(text=story_text[:5000])  # Limit length
        voice_params = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        # Generate audio
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, 
            voice=voice_params, 
            audio_config=audio_config
        )

        # Save audio file
        audio_filename = f"story_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_path = os.path.join(AUDIO_FILES_DIR, audio_filename)
        
        with open(audio_path, "wb") as audio_file:
            audio_file.write(tts_response.audio_content)

        logger.info(f"Generated audio file: {audio_filename}")
        return audio_filename
        
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        return "audio_generation_failed.mp3"  # Return placeholder


def _create_fallback_story(grade: int, topic: str) -> Dict[str, Any]:
    """Create a fallback story when AI generation fails"""
    return {
        "story_id": str(uuid.uuid4()),
        "title": f"Learning Adventure: {topic}",
        "story_text": f"Welcome to an exciting learning adventure about {topic}! Let's explore together and discover amazing things.",
        "quizzes": [{
            "question": f"What would you like to learn about {topic}?",
            "options": ["Everything!", "The basics", "Advanced concepts"],
            "answer": "A",
            "explanation": "Curiosity is the key to learning!"
        }],
        "learning_objectives": [f"Understand basic concepts of {topic}"],
        "vocabulary_words": [topic.lower()],
        "audio_filename": "fallback_audio.mp3",
        "grade_level": grade,
        "topic": topic
    }


def _create_fallback_ar_scene(topic: str, grade_level: Optional[int]) -> Dict[str, Any]:
    """Create a fallback AR scene when AI generation fails"""
    return {
        "scene_id": str(uuid.uuid4()),
        "scene_name": f"Explore {topic}",
        "educational_objective": f"Learn about {topic} through immersive experience",
        "environment": {
            "setting": f"A 3D classroom environment focused on {topic}",
            "lighting": "Bright and welcoming",
            "atmosphere": "Educational and engaging"
        },
        "objects": [{
            "name": f"{topic} Display",
            "description": f"Interactive display about {topic}",
            "interactions": ["Touch to explore", "Rotate to view"],
            "learning_purpose": f"Understand {topic} concepts"
        }],
        "interactions": [{
            "type": "exploration",
            "description": "Walk around and discover",
            "learning_outcome": f"Basic understanding of {topic}",
            "feedback_mechanism": "Visual highlights and audio cues"
        }],
        "grade_level": grade_level or "flexible"
    }


def _create_fallback_story_data(grade: int, topic: str) -> Dict[str, Any]:
    """Create fallback story data"""
    return {
        "title": f"Learning About {topic}",
        "story_text": f"Today we'll learn about {topic} in an exciting way!",
        "quizzes": [],
        "learning_objectives": [f"Understand {topic}"],
        "vocabulary_words": [topic.lower()]
    }


def _create_fallback_ar_data(topic: str, grade_level: Optional[int]) -> Dict[str, Any]:
    """Create fallback AR data"""
    return {
        "scene_name": f"Explore {topic}",
        "environment": {"setting": f"Learning space for {topic}"},
        "objects": [],
        "interactions": []
    }


def _determine_badge_type(badge_name: str) -> str:
    """Determine badge type based on name"""
    badge_lower = badge_name.lower()
    if "achievement" in badge_lower or "complete" in badge_lower:
        return "achievement"
    elif "streak" in badge_lower or "daily" in badge_lower:
        return "consistency" 
    elif "master" in badge_lower or "expert" in badge_lower:
        return "mastery"
    else:
        return "participation"


def _calculate_badge_points(badge_name: str) -> int:
    """Calculate points for badge"""
    badge_type = _determine_badge_type(badge_name)
    points_map = {
        "participation": 10,
        "consistency": 25,
        "achievement": 50,
        "mastery": 100
    }
    return points_map.get(badge_type, 10)


def _get_badge_description(badge_name: str) -> str:
    """Get description for badge"""
    return f"Earned the '{badge_name}' badge for outstanding achievement!"


def _get_badge_rarity(badge_name: str) -> str:
    """Determine badge rarity"""
    badge_lower = badge_name.lower()
    if "master" in badge_lower or "expert" in badge_lower:
        return "rare"
    elif "achievement" in badge_lower:
        return "uncommon"
    else:
        return "common"


def _get_badge_display_name(badge_name: str) -> str:
    """Get display name for badge"""
    return badge_name.replace("_", " ").title()


def _get_badge_icon_url(badge_name: str) -> str:
    """Get icon URL for badge"""
    # In a real implementation, this would return actual icon URLs
    badge_type = _determine_badge_type(badge_name)
    return f"/static/badges/{badge_type}_badge.png"
