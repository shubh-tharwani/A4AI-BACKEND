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
async def generate_interactive_story(grade: int, topic: str, language: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a voice-enabled interactive story based on grade, topic, and language
    
    Args:
        grade (int): Grade level for the story (1-12)
        topic (str): Educational topic for the story
        language (str): Language for the story (default: "English")
        user_id (str, optional): User ID for tracking
        
    Returns:
        Dict[str, Any]: Generated story data with audio file information
        
    Raises:
        ServiceError: If story generation fails
        DAOError: If database operations fail
    """
    logger.info(f"Generating interactive story for grade {grade}, topic: {topic}, language: {language}")
    
    # Validate inputs
    if not isinstance(grade, int) or grade < 1 or grade > 12:
        raise ValueError("Grade must be an integer between 1 and 12")
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty")
    
    try:
        # Enhanced prompt to generate 500-word educational story in specified language
        prompt = f"""
        You are an expert educational content creator. Generate ALL content in {language}. Every field, every word, every section must be in {language}.
        
        Create a comprehensive, informative, and engaging educational story for Grade {grade} students about '{topic}' entirely in {language}.
        
        STORY CONTENT REQUIREMENTS:
        - MANDATORY: Exactly 450-550 words in the story_text field
        - ALL CONTENT must be in {language} language only
        - Grade {grade} appropriate vocabulary and concepts
        - Rich educational content with detailed explanations
        - Include scientific facts, historical context, or practical applications
        - Use descriptive language to paint vivid pictures
        - Include cause-and-effect relationships
        - Add real-world examples and connections
        - Incorporate problem-solving scenarios
        - Use storytelling elements: characters, setting, conflict, resolution
        
        EDUCATIONAL DEPTH:
        - Explain WHY things happen, not just WHAT happens
        - Include multiple learning concepts within {topic}
        - Connect to other subjects (science, math, history, etc.)
        - Provide step-by-step explanations of processes
        - Include interesting facts and surprising discoveries
        - Show practical applications in daily life
        - Encourage critical thinking and curiosity
        
        STRUCTURE FOR 500 WORDS:
        - Introduction with hook (75-100 words)
        - Main educational content with examples (250-300 words)
        - Problem/challenge scenario (75-100 words)
        - Resolution with learning reinforcement (75-100 words)
        
        QUALITY STANDARDS:
        - Information-rich content that teaches substantial concepts
        - Engaging narrative that maintains student interest
        - Clear explanations suitable for Grade {grade} comprehension
        - Positive, encouraging tone throughout
        - Seamless integration of educational facts into story flow
        
        Format as valid JSON (field names in English, content in {language}):
        {{
          "title": "Captivating educational title about {topic} in {language}",
          "learning_objectives": ["specific learning goal 1 in {language}", "specific learning goal 2 in {language}", "specific learning goal 3 in {language}"],
          "story_text": "EXACTLY 450-550 word comprehensive educational story in {language} with rich content, detailed explanations, real-world examples, and engaging narrative elements",
          "think_about_it": "Single string with 3-4 thought-provoking questions separated by spaces or newlines in {language}",
          "what_you_learn": "Single string with comprehensive summary of key concepts, facts, and skills learned from the story in {language}",
          "vocabulary_words": ["key term 1 in {language}", "key term 2 in {language}", "key term 3 in {language}", "key term 4 in {language}", "key term 5 in {language}"],
          "grade_level": {grade},
          "subject": "Primary academic subject area in {language}",
          "language": "{language}"
        }}
        
        IMPORTANT DATA TYPE REQUIREMENTS:
        - "think_about_it" must be a single string, not an array
        - "what_you_learn" must be a single string, not an array  
        - "learning_objectives" must be an array of strings
        - "vocabulary_words" must be an array of strings
        - All other text fields must be single strings
        
        Topic: {topic}
        Grade Level: {grade}
        Target Language: {language}
        
        CRITICAL REMINDERS:
        - story_text must be 450-550 words with substantial educational content
        - Include detailed explanations, facts, and real-world applications
        - Every text field must be entirely in {language}
        - Make it informative AND engaging for Grade {grade} students
        """

        print("🔥 INTERACTIVE STORY GENERATION STARTED")
        print(f"📝 Request: Grade={grade}, Topic={topic}, Language={language}")
        
        # Use centralized Vertex AI service
        print("🤖 Calling Vertex AI service...")
        try:
            response = vertex_ai_service.generate_educational_content(prompt, "story")
            print(f"✅ Vertex AI Response received: {len(response) if response else 0} characters")
            print(f"🔍 Response preview: {response[:200] if response else 'NO RESPONSE'}...")
        except Exception as ai_error:
            print(f"❌ Vertex AI Error: {ai_error}")
            raise ai_error

        # Parse and validate response
        print("🔧 Parsing response...")
        if not response:
            print("❌ Empty response from Vertex AI!")
            raise Exception("Empty response from Vertex AI")
            
        story_data = _parse_story_response(response, grade, topic, language)
        print(f"📊 Parsed data keys: {list(story_data.keys()) if story_data else 'NO DATA'}")
        
        if not story_data:
            print("❌ Failed to parse story data!")
            raise Exception("Failed to parse story data")

        # Generate audio file
        audio_filename = await _generate_story_audio(story_data["story_text"])
        print(f"🎵 Audio generated: {audio_filename}")

        # Prepare data for database storage
        activity_data = {
            "title": story_data["title"],
            "story_text": story_data["story_text"],
            "think_about_it": story_data.get("think_about_it", ""),
            "what_you_learn": story_data.get("what_you_learn", ""),
            "learning_objectives": story_data.get("learning_objectives", []),
            "vocabulary_words": story_data.get("vocabulary_words", []),
            "audio_file": audio_filename,
            "grade_level": grade,
            "topic": topic,
            "language": language,
            "subject": story_data.get("subject", topic),
            "type": "interactive_story",
            "user_id": user_id
        }
        
        # Save to database using DAO
        story_id = activities_dao.save_interactive_story(activity_data)
        print(f"💾 Story saved to database with ID: {story_id}")
        
        # Return response with generated content
        result = {
            "story_id": story_id,
            "title": story_data["title"],
            "story_text": story_data["story_text"],
            "think_about_it": story_data.get("think_about_it", ""),
            "what_you_learn": story_data.get("what_you_learn", ""),
            "learning_objectives": story_data.get("learning_objectives", []),
            "vocabulary_words": story_data.get("vocabulary_words", []),
            "audio_filename": audio_filename,
            "grade_level": grade,
            "topic": topic,
            "language": language,
            "subject": story_data.get("subject", topic)
        }
        
        logger.info(f"Successfully generated interactive story: {story_id}")
        return result
        
    except Exception as e:
        error_msg = f"Error generating interactive story: {e}"
        print(f"ERROR: {error_msg}")  # Also print to console for immediate visibility
        logger.error(error_msg, exc_info=True)
        logger.info(error_msg, exc_info=True)
        # Return fallback response
        fallback_story = _create_fallback_story(grade, topic, language)
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
        error_msg = f"Error generating AR scene: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"ERROR: {error_msg}")  # Also print to console for immediate visibility
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
        error_msg = f"Error assigning badge to user {user_id}: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"ERROR: {error_msg}")  # Also print to console for immediate visibility
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

def _parse_story_response(response: str, grade: int, topic: str, language: str = "English") -> Dict[str, Any]:
    """Parse and validate story response from AI"""
    print(f"🔍 Parsing response of length: {len(response) if response else 0}")
    print(f"📄 Raw response preview: {response[:500] if response else 'EMPTY'}...")
    
    try:
        # Clean the response - remove markdown code blocks if present
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # Remove ```json
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]   # Remove ```
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # Remove ending ```
        
        # Remove any leading/trailing whitespace after cleaning
        cleaned_response = cleaned_response.strip()
        
        print(f"🧹 Cleaned response preview: {cleaned_response[:300] if cleaned_response else 'EMPTY'}...")
        
        story_data = json.loads(cleaned_response)
        print(f"✅ Successfully parsed JSON with keys: {list(story_data.keys())}")
        
        # Ensure required fields exist and fix data types
        if "title" not in story_data:
            story_data["title"] = f"Learning Adventure: {topic}"
            print("⚠️ Added default title")
        if "story_text" not in story_data:
            story_data["story_text"] = f"Let's explore the wonderful world of {topic}!"
            print("⚠️ Added default story_text")
        if "think_about_it" not in story_data:
            story_data["think_about_it"] = f"Think about how {topic} relates to your daily life."
            print("⚠️ Added default think_about_it")
        elif isinstance(story_data["think_about_it"], list):
            # Convert list to string if AI returned an array
            story_data["think_about_it"] = " ".join(story_data["think_about_it"])
            print("🔧 Converted think_about_it from list to string")
        if "what_you_learn" not in story_data:
            story_data["what_you_learn"] = f"You will learn important concepts about {topic}."
            print("⚠️ Added default what_you_learn")
        elif isinstance(story_data["what_you_learn"], list):
            # Convert list to string if AI returned an array
            story_data["what_you_learn"] = " ".join(story_data["what_you_learn"])
            print("🔧 Converted what_you_learn from list to string")
        if "learning_objectives" not in story_data:
            story_data["learning_objectives"] = [f"Learn about {topic}"]
            print("⚠️ Added default learning_objectives")
        elif not isinstance(story_data["learning_objectives"], list):
            # Convert to list if AI returned a string
            story_data["learning_objectives"] = [story_data["learning_objectives"]]
            print("🔧 Converted learning_objectives to list")
        if "vocabulary_words" not in story_data:
            story_data["vocabulary_words"] = []
            print("⚠️ Added default vocabulary_words")
        elif not isinstance(story_data["vocabulary_words"], list):
            # Convert to list if AI returned a string
            story_data["vocabulary_words"] = [story_data["vocabulary_words"]]
            print("🔧 Converted vocabulary_words to list")
        if "subject" not in story_data:
            story_data["subject"] = topic
            print("⚠️ Added default subject")
        
        # Validate story length
        word_count = len(story_data["story_text"].split())
        print(f"📊 Story statistics: {word_count} words, {len(story_data['story_text'])} characters")
        
        return story_data
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse story response as JSON: {e}"
        print(f"❌ JSON Parse Error: {error_msg}")
        print(f"📄 Full response that failed to parse: {response}")
        logger.warning(error_msg, exc_info=True)
        print(f"WARNING: {error_msg}")  # Also print to console for immediate visibility
        return _create_fallback_story_data(grade, topic, language)


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
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse AR response as JSON, creating fallback: {e}"
        logger.warning(error_msg, exc_info=True)
        print(f"WARNING: {error_msg}")  # Also print to console for immediate visibility
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
        error_msg = f"Error generating audio: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"ERROR: {error_msg}")  # Also print to console for immediate visibility
        return "audio_generation_failed.mp3"  # Return placeholder


def _create_fallback_story(grade: int, topic: str, language: str = "English") -> Dict[str, Any]:
    """Create a comprehensive fallback story when AI generation fails"""
    
    # Create a more detailed fallback story based on topic and grade
    base_story = f"""Welcome to an exciting educational journey about {topic}! This adventure will take you deep into the fascinating world of {topic}, where you'll discover amazing concepts and learn how they shape our daily lives.

Let's begin by exploring what {topic} really means. In simple terms, {topic} involves many interesting processes and principles that affect everything around us. Scientists and researchers have spent years studying {topic} to understand how it works and why it's so important.

Throughout history, people have been curious about {topic}. They asked questions, conducted experiments, and made discoveries that changed our understanding of the world. Today, we use this knowledge in countless ways - from the technology we use to the decisions we make every day.

One of the most fascinating aspects of {topic} is how it connects to other subjects you might be studying. For example, when we look at {topic}, we can see connections to mathematics, science, history, and even art. This interconnectedness shows us that learning is like a web - everything is connected!

Let's imagine a real-world scenario where {topic} plays a crucial role. Think about your daily routine and try to identify where {topic} might be involved. You might be surprised to discover how often you encounter concepts related to {topic} without even realizing it.

As we continue our exploration, remember that understanding {topic} isn't just about memorizing facts. It's about developing critical thinking skills, asking good questions, and making connections between different ideas. These skills will help you become a better learner and problem-solver.

By the end of this journey, you'll have gained valuable insights into {topic} and developed a deeper appreciation for how it influences our world. Remember, every expert was once a beginner, and every question you ask brings you one step closer to understanding."""

    # Adjust complexity based on grade level
    if grade <= 3:
        story_length = 300
    elif grade <= 6:
        story_length = 400
    else:
        story_length = 500
    
    # Trim story to appropriate length
    words = base_story.split()
    if len(words) > story_length:
        trimmed_story = " ".join(words[:story_length]) + "..."
    else:
        trimmed_story = base_story

    return {
        "story_id": str(uuid.uuid4()),
        "title": f"Discovering the World of {topic}: An Educational Adventure",
        "story_text": trimmed_story,
        "think_about_it": f"Think about how {topic} affects your daily life. What examples of {topic} do you see around you? How might understanding {topic} help you solve problems or make better decisions? Can you think of questions you'd like to explore further about {topic}?",
        "what_you_learn": f"In this story, you will learn the fundamental concepts of {topic}, understand its real-world applications, develop critical thinking skills related to {topic}, and discover how {topic} connects to other subjects and areas of life. You'll also learn to ask meaningful questions and make connections between different ideas.",
        "learning_objectives": [
            f"Understand the basic principles and concepts of {topic}",
            f"Explore real-world applications and examples of {topic}",
            f"Develop critical thinking skills related to {topic}",
            f"Make connections between {topic} and other subjects"
        ],
        "vocabulary_words": [topic.lower(), "concepts", "principles", "applications", "connections", "research", "discovery", "understanding"],
        "audio_filename": "fallback_audio.mp3",
        "grade_level": grade,
        "topic": topic,
        "language": language,
        "subject": topic
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


def _create_fallback_story_data(grade: int, topic: str, language: str = "English") -> Dict[str, Any]:
    """Create comprehensive fallback story data when parsing fails"""
    
    # Generate more detailed content for fallback
    story_text = f"""Today we embark on an educational journey to understand {topic} in depth. This fascinating subject has captured the attention of learners and researchers for generations, and now it's your turn to discover its wonders.

{topic} is more than just a concept we study in school - it's a fundamental part of our world that influences many aspects of our daily lives. When we examine {topic} closely, we can see how it connects to science, mathematics, history, and even the arts, creating a rich tapestry of knowledge.

Let's explore some key principles of {topic}. Scientists and experts have identified several important characteristics that help us understand how {topic} works. These principles guide us in making predictions, solving problems, and developing new technologies that benefit society.

One of the most exciting aspects of studying {topic} is discovering its practical applications. From the moment you wake up in the morning until you go to bed at night, you encounter examples of {topic} in action. These real-world connections make learning about {topic} both relevant and meaningful.

Throughout history, curious minds have asked important questions about {topic}. Their investigations led to breakthrough discoveries that changed our understanding of the world. Today, we continue to build on this foundation of knowledge, asking new questions and seeking innovative solutions.

As you continue your educational journey, remember that understanding {topic} requires both careful observation and creative thinking. The skills you develop while studying {topic} will serve you well in many other areas of learning and life."""

    # Adjust for grade level
    if grade <= 3:
        words = story_text.split()[:250]
        story_text = " ".join(words)
    elif grade <= 6:
        words = story_text.split()[:350]
        story_text = " ".join(words)
    
    return {
        "title": f"Understanding {topic}: A Comprehensive Learning Experience",
        "story_text": story_text,
        "think_about_it": f"Think about how {topic} relates to things you see every day. Can you find examples of {topic} in your environment? What questions do you have about {topic}? How might understanding {topic} help you in other subjects or activities?",
        "what_you_learn": f"You will learn fundamental concepts about {topic}, understand its practical applications in daily life, explore its connections to other subjects, develop critical thinking skills, and appreciate the historical context of discoveries related to {topic}.",
        "learning_objectives": [
            f"Understand fundamental concepts of {topic}",
            f"Identify real-world applications of {topic}",
            f"Appreciate the importance of {topic} in our world",
            f"Develop critical thinking skills related to {topic}"
        ],
        "vocabulary_words": [topic.lower(), "concepts", "principles", "applications", "discovery", "investigation", "understanding", "knowledge"],
        "subject": topic
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
