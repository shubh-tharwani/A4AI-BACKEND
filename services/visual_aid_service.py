"""
Visual Aid Service
Handles generation of educational visual content using Vertex AI Gemini
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from dao.visual_aid_dao import visual_aid_dao
from services.image_generator import ImageGenerator
from utils.dao_error_handler import handle_service_dao_errors, ensure_document_id

logger = logging.getLogger(__name__)

# Initialize image generator
image_generator = ImageGenerator()


@handle_service_dao_errors("generate_visual_aid")
async def generate_visual_aid(
    prompt: str,
    asset_type: str = "image",
    user_id: Optional[str] = None,
    grade_level: Optional[int] = None,
    subject: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate contextual visual aid (image or video) for educational content
    
    Args:
        prompt (str): Description of the visual aid to generate
        asset_type (str): Type of asset ("image" or "video")
        user_id (str, optional): User ID for tracking
        grade_level (int, optional): Grade level for age-appropriate content
        subject (str, optional): Subject area for categorization
        
    Returns:
        Dict[str, Any]: Generated visual aid information
        
    Raises:
        ServiceError: If visual aid generation fails
        DAOError: If database operations fail
    """
    logger.info(f"Generating visual aid: {asset_type} for prompt: {prompt}")
    
    # Validate inputs
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")
    
    if asset_type not in ["image", "video"]:
        raise ValueError("Asset type must be 'image' or 'video'")
    
    if grade_level and (grade_level < 1 or grade_level > 12):
        raise ValueError("Grade level must be between 1 and 12")
    
    try:
        # Enhance prompt with educational context
        enhanced_prompt = _enhance_prompt_for_education(prompt, grade_level, subject)
        
        # Generate visual content using the new image generator
        try:
            if asset_type == "image":
                # Use the image generator to create visual aid description
                file_path, filename, metadata = image_generator.generate_image(
                    content=enhanced_prompt,
                    visual_type="illustration",
                    topic=_extract_topic_from_prompt(prompt),
                    subject=subject or "General",
                    grade=str(grade_level) if grade_level else "K-12",
                    style="educational",
                    color_scheme="vibrant"
                )
                public_url = f"/temp_image/{filename}"
            else:  # video
                # For now, generate a static image as video generation is more complex
                logger.info("Video generation requested - creating enhanced image instead")
                file_path, filename, metadata = image_generator.generate_image(
                    content=f"Dynamic educational illustration: {enhanced_prompt}",
                    visual_type="illustration",
                    topic=_extract_topic_from_prompt(prompt),
                    subject=subject or "General", 
                    grade=str(grade_level) if grade_level else "K-12",
                    style="dynamic",
                    color_scheme="engaging"
                )
                public_url = f"/temp_image/{filename}"
        except Exception as gen_error:
            logger.warning(f"Visual generation failed, using complete fallback: {gen_error}")
            return await _create_fallback_visual_aid(prompt, asset_type, user_id)
        
        # Prepare visual aid data for database
        visual_aid_data = {
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "asset_type": asset_type,
            "url": public_url,
            "filename": filename,
            "topic": _extract_topic_from_prompt(prompt),
            "subject": subject,
            "grade_level": grade_level,
            "user_id": user_id,
            "metadata": metadata,
            "generation_method": "gemini_image_generator"
        }
        
        # Save to database using DAO
        visual_aid_id = visual_aid_dao.save_visual_aid(visual_aid_data)
        
        # Prepare response
        result = {
            "visual_aid_id": visual_aid_id,
            "status": "success",
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "asset_type": asset_type,
            "image_url": public_url,
            "filename": filename,
            "topic": visual_aid_data["topic"],
            "metadata": metadata
        }
        
        logger.info(f"Successfully generated visual aid: {visual_aid_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating visual aid: {e}")
        # Return fallback response
        return await _create_fallback_visual_aid(prompt, asset_type, user_id)


@handle_service_dao_errors("generate_educational_infographic")
async def generate_educational_infographic(
    topic: str,
    data_points: List[str],
    grade_level: Optional[int] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate educational infographic with data visualization
    
    Args:
        topic (str): Main topic of the infographic
        data_points (List[str]): Key data points to include
        grade_level (int, optional): Grade level for complexity
        user_id (str, optional): User ID for tracking
        
    Returns:
        Dict[str, Any]: Generated infographic information
    """
    logger.info(f"Generating infographic for topic: {topic}")
    
    # Validate inputs
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty")
    if not data_points:
        raise ValueError("Data points cannot be empty")
    
    try:
        # Create detailed infographic prompt
        complexity = _get_complexity_for_grade(grade_level) if grade_level else "moderate"
        data_text = ", ".join(data_points)
        
        infographic_prompt = f"""
        Create a comprehensive educational infographic about {topic}.
        
        Requirements:
        - Visual complexity: {complexity}
        - Include these key data points: {data_text}
        - Use clear, readable fonts and educational color scheme
        - Include charts, diagrams, or visual representations where appropriate
        - Age-appropriate design for grade level {grade_level or 'general'}
        - Professional educational layout with good visual hierarchy
        
        Style: Clean, educational, informative, visually appealing
        Format: Vertical infographic layout suitable for classroom display
        """
        
        # Generate the infographic using the image generator
        file_path, filename, metadata = image_generator.generate_image(
            content=infographic_prompt,
            visual_type="infographic",
            topic=topic,
            subject="Educational",
            grade=str(grade_level) if grade_level else "K-12",
            style="professional",
            color_scheme="educational"
        )
        public_url = f"/temp_image/{filename}"
        
        # Save infographic data
        infographic_data = {
            "prompt": infographic_prompt,
            "topic": topic,
            "data_points": data_points,
            "asset_type": "infographic",
            "url": public_url,
            "filename": filename,
            "grade_level": grade_level,
            "user_id": user_id,
            "metadata": {
                **metadata,
                "complexity": complexity,
                "data_point_count": len(data_points)
            }
        }
        
        visual_aid_id = visual_aid_dao.save_visual_aid(infographic_data)
        
        result = {
            "visual_aid_id": visual_aid_id,
            "status": "success",
            "topic": topic,
            "data_points": data_points,
            "image_url": public_url,
            "filename": filename,
            "complexity": complexity,
            "metadata": infographic_data["metadata"]
        }
        
        logger.info(f"Successfully generated infographic: {visual_aid_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating infographic: {e}")
        raise


@handle_service_dao_errors("get_user_visual_aids")
async def get_user_visual_aids(
    user_id: str,
    limit: int = 10,
    asset_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get visual aids created by a user
    
    Args:
        user_id (str): User ID
        limit (int): Maximum number of visual aids to retrieve
        asset_type (str, optional): Filter by asset type
        
    Returns:
        List[Dict[str, Any]]: List of user visual aids
    """
    user_id = ensure_document_id(user_id, "user_id")
    
    visual_aids = visual_aid_dao.get_user_visual_aids(user_id, limit, asset_type)
    
    # Enhance with additional metadata
    enhanced_visual_aids = []
    for visual_aid in visual_aids:
        enhanced_visual_aid = {
            **visual_aid,
            "display_topic": _format_topic_for_display(visual_aid.get("topic", "")),
            "created_date": visual_aid.get("created_at", "").split("T")[0] if visual_aid.get("created_at") else None
        }
        enhanced_visual_aids.append(enhanced_visual_aid)
    
    return enhanced_visual_aids


@handle_service_dao_errors("search_visual_aids")
async def search_visual_aids(
    topic: str,
    asset_type: Optional[str] = None,
    grade_level: Optional[int] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search for existing visual aids by topic
    
    Args:
        topic (str): Topic to search for
        asset_type (str, optional): Filter by asset type
        grade_level (int, optional): Filter by grade level
        limit (int): Maximum number of results
        
    Returns:
        List[Dict[str, Any]]: List of matching visual aids
    """
    if not topic or not topic.strip():
        raise ValueError("Search topic cannot be empty")
    
    visual_aids = visual_aid_dao.search_visual_aids(topic.strip(), asset_type, limit)
    
    # Filter by grade level if specified
    if grade_level:
        visual_aids = [
            va for va in visual_aids
            if va.get("grade_level") == grade_level or va.get("grade_level") is None
        ]
    
    return visual_aids


@handle_service_dao_errors("delete_visual_aid")
async def delete_visual_aid(visual_aid_id: str, user_id: str) -> Dict[str, Any]:
    """
    Delete a visual aid (soft delete)
    
    Args:
        visual_aid_id (str): Visual aid ID to delete
        user_id (str): User ID requesting deletion
        
    Returns:
        Dict[str, Any]: Deletion result
    """
    visual_aid_id = ensure_document_id(visual_aid_id, "visual_aid_id")
    user_id = ensure_document_id(user_id, "user_id")
    
    # Get visual aid to verify ownership
    visual_aid = visual_aid_dao.get_visual_aid(visual_aid_id)
    if not visual_aid:
        raise ValueError("Visual aid not found")
    
    # Check ownership (or allow teachers/admins)
    if visual_aid.get("user_id") != user_id:
        # In a real implementation, check user role here
        raise PermissionError("Not authorized to delete this visual aid")
    
    # Soft delete from database
    success = visual_aid_dao.delete_visual_aid(visual_aid_id)
    
    if success:
        # Optionally delete file from local storage as well
        filename = visual_aid.get("filename")
        if filename:
            try:
                import os
                file_path = os.path.join(os.getcwd(), "temp_image", filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted file from local storage: {filename}")
            except Exception as e:
                logger.warning(f"Could not delete file from local storage: {e}")
    
    return {
        "status": "success" if success else "failed",
        "visual_aid_id": visual_aid_id,
        "message": "Visual aid deleted successfully" if success else "Failed to delete visual aid"
    }


# Helper functions


async def _create_fallback_visual_aid(
    prompt: str, 
    asset_type: str, 
    user_id: Optional[str]
) -> Dict[str, Any]:
    """Create fallback visual aid when generation fails"""
    logger.warning("Creating fallback visual aid response")
    
    # Generate a simple fallback using the image generator
    try:
        file_path, filename, metadata = image_generator._create_fallback_description(
            topic=_extract_topic_from_prompt(prompt),
            subject="General",
            visual_type=asset_type,
            content=prompt
        )
        public_url = f"/temp_image/{filename}"
    except Exception as e:
        logger.error(f"Even fallback generation failed: {e}")
        filename = "placeholder.txt"
        public_url = "/static/placeholder.png"
        metadata = {"fallback": True}
    
    return {
        "visual_aid_id": str(uuid.uuid4()),
        "status": "fallback",
        "prompt": prompt,
        "asset_type": asset_type,
        "image_url": public_url,
        "filename": filename,
        "topic": _extract_topic_from_prompt(prompt),
        "metadata": {
            **metadata,
            "generated_at": datetime.utcnow().isoformat()
        },
        "message": "Generated fallback response due to service unavailability"
    }


def _enhance_prompt_for_education(
    prompt: str, 
    grade_level: Optional[int], 
    subject: Optional[str]
) -> str:
    """Enhance prompt with educational context"""
    enhancements = []
    
    if grade_level:
        age_range = _get_age_range_for_grade(grade_level)
        enhancements.append(f"Age-appropriate for {age_range} year olds (grade {grade_level})")
        enhancements.append(f"Educational complexity suitable for grade {grade_level}")
    
    if subject:
        enhancements.append(f"Focused on {subject} education")
    
    enhancements.extend([
        "Educational illustration style",
        "Clear, informative, and engaging",
        "Suitable for classroom use",
        "Professional educational quality"
    ])
    
    enhanced_prompt = f"{prompt}\n\nStyle requirements: {', '.join(enhancements)}"
    return enhanced_prompt


def _extract_topic_from_prompt(prompt: str) -> str:
    """Extract main topic from prompt"""
    # Simple extraction - first few words
    words = prompt.split()[:3]
    return " ".join(words).strip(".,!?")


def _format_topic_for_display(topic: str) -> str:
    """Format topic for display"""
    return topic.title() if topic else "General"


def _get_age_range_for_grade(grade: int) -> str:
    """Get typical age range for grade level"""
    age_map = {
        1: "6-7", 2: "7-8", 3: "8-9", 4: "9-10", 5: "10-11", 6: "11-12",
        7: "12-13", 8: "13-14", 9: "14-15", 10: "15-16", 11: "16-17", 12: "17-18"
    }
    return age_map.get(grade, "6-18")


def _get_complexity_for_grade(grade_level: int) -> str:
    """Determine visual complexity based on grade level"""
    if grade_level <= 3:
        return "simple and colorful"
    elif grade_level <= 6:
        return "moderate with clear visuals"
    elif grade_level <= 9:
        return "detailed with comprehensive information"
    else:
        return "advanced with sophisticated data representation"
