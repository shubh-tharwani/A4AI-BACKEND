"""
Visual Aid Routes
FastAPI routes for educational visual content generation using Vertex AI Gemini + Image Generation
"""
import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import vertexai
from vertexai.generative_models import GenerativeModel

# Add parent directory to path to import config.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Import the DAO layer
from dao.visual_aid_dao import visual_aid_dao
from dao.user_dao import user_dao

# Import centralized error handling
from utils.dao_error_handler import handle_service_dao_errors, ensure_document_id

# Import the new Gemini image generator
from services.gemini_image_generator import GeminiImageGenerator

# Initialize Vertex AI
vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
model = GenerativeModel(Config.GOOGLE_GEMINI_MODEL)

# Initialize Gemini image generator
image_generator = GeminiImageGenerator()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/visual-aids", tags=["Visual Aids"])


# Request Models
class VisualAidRequest(BaseModel):
    topic: str = Field(..., description="Topic for the visual aid")
    grade: str = Field(..., description="Grade level")
    subject: str = Field(..., description="Subject area")
    visualType: str = Field(default="infographic", description="Type of visual aid (infographic, illustration, diagram, chart, mind_map, timeline)")
    style: Optional[str] = Field(default="modern", description="Visual style (modern, classic, creative, professional)")
    color_scheme: Optional[str] = Field(default="blue", description="Color scheme (blue, green, purple, orange, teal)")


class InfographicRequest(BaseModel):
    topic: str = Field(..., description="Main topic of the infographic")
    grade: str = Field(..., description="Grade level")
    subject: str = Field(..., description="Subject area")
    style: Optional[str] = Field(default="modern", description="Visual style")


# Response Models
class VisualAidResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


# Helper function to generate context-specific prompts based on visual type
def get_visual_type_context(visual_type: str, topic: str, subject: str, grade: str) -> str:
    """Generate context-specific prompts based on visual type"""
    
    base_context = f"Create educational content for {subject} topic '{topic}' suitable for grade {grade} students."
    
    visual_contexts = {
        "infographic": f"""
        {base_context}
        Create a comprehensive educational infographic with:
        - Clear hierarchical information layout with distinct sections
        - Statistical data visualization and infographic elements
        - Icons, charts, and visual data representations
        - Flowing narrative structure with logical progression
        - Key facts, statistics, and educational insights
        - Visual metaphors and educational symbols
        - Step-by-step information flow
        """,
        
        "illustration": f"""
        {base_context}
        Create detailed educational illustrations with:
        - Artistic visual representations and detailed imagery
        - Educational metaphors and symbolic elements
        - Annotated diagrams with explanatory callouts
        - Engaging, memorable visual storytelling elements
        - Character-based explanations where appropriate
        - Rich visual details that support learning
        - Creative artistic elements that enhance understanding
        """,
        
        "diagram": f"""
        {base_context}
        Create educational diagrams with:
        - Process flows, connections, and systematic relationships
        - Arrows, connecting lines, and step-by-step progression
        - Labeled components and functional elements
        - Clear cause-and-effect or sequential relationships
        - Technical accuracy with proper terminology
        - Logical flow from concept to application
        - Visual representation of abstract concepts
        """,
        
        "chart": f"""
        {base_context}
        Create educational charts with:
        - Proper data visualization with charts and graphs
        - Clear axes, labels, and legends for data interpretation
        - Statistical insights and trend analysis
        - Data context and educational significance
        - Comparative analysis where relevant
        - Visual representation of numerical relationships
        - Educational interpretation of data patterns
        """,
        
        "mind_map": f"""
        {base_context}
        Create educational mind maps with:
        - Central topic with branching concept relationships
        - Hierarchical information structure with clear connections
        - Color-coded categories and visual groupings
        - Conceptual relationships and knowledge mapping
        - Interconnected ideas and sub-topics
        - Visual organization of complex information
        - Learning pathway visualization
        """,
        
        "timeline": f"""
        {base_context}
        Create educational timelines with:
        - Chronological sequence with clear time progression
        - Date markers, periods, and historical context
        - Milestone events with descriptive details
        - Temporal relationships and historical significance
        - Cause-and-effect relationships over time
        - Visual representation of historical progression
        - Educational context for each time period
        """
    }
    
    return visual_contexts.get(visual_type.lower(), visual_contexts["infographic"])


@handle_service_dao_errors("generate_visual_aid_content")
async def generate_visual_aid_content(request: VisualAidRequest, user_id: str = None) -> Dict[str, Any]:
    """Generate educational visual aid content using Vertex AI Gemini + create actual image"""
    try:
        prompt = f"""
        Create a visually engaging, interactive-style educational on the topic "{request.topic}" for grade {request.grade} {request.subject}.

        Design requirements:
        - Modern infographic style with **vibrant colors**, **clean icons**, and **visual hierarchy**
        - Use **illustrations, diagrams, and minimal text**
        - Include: **Title at the top**, central concept in the middle, and related sub-topics in rounded boxes with arrows connecting them
        - Background: soft gradient or white with subtle patterns
        - Highlight key points using icons (e.g., heart icon, pulse icon, blood drop for cardiovascular system)
        - Make it look like a **learning poster** with engaging visual storytelling
        - Avoid plain step-by-step text; instead use **graphical representation**
        - Ensure readability for school students and an **interactive dashboard-like feel**
        - Final output should be in **image format only** with no code or text overlays
        """

        # Generate content using Gemini
        response = model.generate_content(prompt)
        generated_content = response.text
        
        # Generate actual image using the content
        logger.info(f"Generating actual image for : {request.topic}")
        file_path, filename, image_metadata = image_generator.generate_image(
            content=generated_content,
            visual_type=request.visualType,
            topic=request.topic,
            subject=request.subject,
            grade=request.grade,
            style=request.style,
            color_scheme=request.color_scheme
        )
        
        # Create comprehensive metadata with expected structure
        metadata = {
            "visual_type": request.visualType,
            "subject": request.subject,
            "grade_level": request.grade,
            "style": request.style,
            "color_scheme": request.color_scheme,
            "generated_at": datetime.now().isoformat(),
            "generation_method": "gemini_ai_with_mermaid",
            "content_length": len(generated_content),
            "prompt_type": f"{request.visualType}_specific",
            "image_metadata": {
                "size": image_metadata.get("size", 0),
                "dimensions": "scalable",  # Mermaid diagrams are scalable
                "format": image_metadata.get("format", "Mermaid"),
                "content_type": image_metadata.get("content_type", "text/mermaid"),
                "can_render": image_metadata.get("can_render", True),
                "filename": image_metadata.get("filename", filename)
            },
            "has_downloadable_image": True
        }
        
        # Save to database using DAO
        visual_aid_data = {
            "topic": request.topic,
            "subject": request.subject,
            "grade_level": request.grade,
            "visual_type": request.visualType,
            "style": request.style,
            "color_scheme": request.color_scheme,
            "content": generated_content,
            "image_filename": filename,
            "image_path": file_path,
            "user_id": user_id,
            "metadata": metadata,
            "status": "completed"
        }
        
        visual_aid_id = visual_aid_dao.save_visual_aid(visual_aid_data)
        
        return {
            "id": visual_aid_id,
            "title": f"{request.subject}: {request.topic}",
            "content": generated_content,
            "visual_type": request.visualType,
            "image_filename": filename,
            "image_path": file_path,
            "metadata": metadata,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error generating visual aid content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate visual aid: {str(e)}")


# Visual Aid Generation Routes
@router.post("/generate")
async def generate_visual_aid(request: VisualAidRequest):
    """Generate a visual aid using Vertex AI Gemini"""
    try:
        logger.info(f"Generating visual aid for topic: {request.topic}, type: {request.visualType}")
        
        # Generate content using Gemini
        result = await generate_visual_aid_content(request)
        
        return JSONResponse({
            "success": True,
            "message": "Visual aid generated successfully",
            "data": {
                "id": result["id"],
                "title": result["title"],
                "content": result["content"],
                "visual_type": result["visual_type"],
                "image_url": f"http://localhost:8000/api/v1/visual-aids/{result['id']}/image",  # Backend image URL
                "image_filename": result["image_filename"],
                "download_url": f"http://localhost:8000/api/v1/visual-aids/{result['id']}/download",  # Backend download endpoint
                "preview_url": f"http://localhost:8000/api/v1/visual-aids/{result['id']}/preview",  # Backend preview endpoint
                "content_url": f"http://localhost:8000/api/v1/visual-aids/{result['id']}/content",  # Backend content endpoint
                "metadata": {
                    "topic": request.topic,
                    "grade": request.grade,
                    "subject": request.subject,
                    "visual_type": request.visualType,
                    "style": request.style,
                    "color_scheme": request.color_scheme,
                    "created_at": result["metadata"]["generated_at"],
                    "generation_method": result["metadata"]["generation_method"],
                    "has_downloadable_image": result["metadata"]["has_downloadable_image"],
                    "image_size": result["metadata"]["image_metadata"]["size"],
                    "image_dimensions": result["metadata"]["image_metadata"]["dimensions"]
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating visual aid: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infographic")
async def create_infographic(request: InfographicRequest):
    """Create an infographic using Vertex AI Gemini"""
    try:
        logger.info(f"Creating infographic for: {request.topic}")
        
        # Convert to VisualAidRequest format
        visual_request = VisualAidRequest(
            topic=request.topic,
            grade=request.grade,
            subject=request.subject,
            visualType="infographic",
            style=request.style or "modern"
        )
        
        # Generate infographic content using Gemini
        result = await generate_visual_aid_content(visual_request)
        
        return JSONResponse({
            "success": True,
            "message": "Infographic created successfully",
            "data": {
                "id": result["id"],
                "title": result["title"],
                "content": result["content"],
                "visual_type": "infographic",
                "image_url": f"http://localhost:8000/api/v1/visual-aids/{result['id']}/image",  # Backend image URL
                "image_filename": result["image_filename"],
                "download_url": f"http://localhost:8000/api/v1/visual-aids/{result['id']}/download",  # Backend download endpoint
                "preview_url": f"http://localhost:8000/api/v1/visual-aids/{result['id']}/preview",  # Backend preview endpoint
                "content_url": f"http://localhost:8000/api/v1/visual-aids/{result['id']}/content",  # Backend content endpoint
                "metadata": {
                    "topic": request.topic,
                    "grade": request.grade,
                    "subject": request.subject,
                    "visual_type": "infographic",
                    "style": request.style,
                    "created_at": result["metadata"]["generated_at"],
                    "generation_method": result["metadata"]["generation_method"],
                    "has_downloadable_image": result["metadata"]["has_downloadable_image"]
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating infographic: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-visual-aids")
async def get_user_visual_aids(user_id: str = None):
    """Get list of generated visual aids for a user"""
    try:
        # Get visual aids from database using DAO
        visual_aids = visual_aid_dao.get_user_visual_aids(user_id or "default_user")
        
        # Format response
        formatted_aids = []
        for aid in visual_aids:
            formatted_aids.append({
                "id": aid.get("id"),
                "title": f"{aid.get('subject', 'General')}: {aid.get('topic', 'Visual Aid')}",
                "topic": aid.get("topic"),
                "subject": aid.get("subject"),
                "grade": aid.get("grade_level"),
                "visual_type": aid.get("visual_type"),
                "style": aid.get("style"),
                "color_scheme": aid.get("color_scheme"),
                "image_url": f"http://localhost:8000/api/v1/visual-aids/{aid.get('id')}/image",  # Backend image URL
                "download_url": f"http://localhost:8000/api/v1/visual-aids/{aid.get('id')}/download",  # Backend download URL
                "preview_url": f"http://localhost:8000/api/v1/visual-aids/{aid.get('id')}/preview",  # Backend preview URL
                "content_url": f"http://localhost:8000/api/v1/visual-aids/{aid.get('id')}/content",  # Backend content URL
                "image_filename": aid.get("image_filename"),
                "created_at": aid.get("created_at"),
                "status": aid.get("status", "completed")
            })
        
        return JSONResponse({
            "success": True,
            "data": formatted_aids,
            "total": len(formatted_aids)
        })
        
    except Exception as e:
        logger.error(f"Error getting visual aids: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_visual_aids(query: str = "", visual_type: str = None, subject: str = None):
    """Search visual aids by query, type, or subject"""
    try:
        # Search visual aids using DAO
        visual_aids = visual_aid_dao.search_visual_aids(
            query=query,
            visual_type=visual_type,
            subject=subject
        )
        
        # Format response
        formatted_aids = []
        for aid in visual_aids:
            formatted_aids.append({
                "id": aid.get("id"),
                "title": f"{aid.get('subject', 'General')}: {aid.get('topic', 'Visual Aid')}",
                "topic": aid.get("topic"),
                "subject": aid.get("subject"),
                "grade": aid.get("grade_level"),
                "visual_type": aid.get("visual_type"),
                "style": aid.get("style"),
                "image_url": f"http://localhost:8000/api/v1/visual-aids/{aid.get('id')}/image",  # Backend image URL
                "download_url": f"http://localhost:8000/api/v1/visual-aids/{aid.get('id')}/download",  # Backend download URL
                "preview_url": f"http://localhost:8000/api/v1/visual-aids/{aid.get('id')}/preview",  # Backend preview URL
                "content_url": f"http://localhost:8000/api/v1/visual-aids/{aid.get('id')}/content",  # Backend content URL
                "image_filename": aid.get("image_filename"),
                "created_at": aid.get("created_at"),
                "content_preview": aid.get("content", "")[:200] + "..." if len(aid.get("content", "")) > 200 else aid.get("content", "")
            })
        
        return JSONResponse({
            "success": True,
            "data": formatted_aids,
            "total": len(formatted_aids),
            "query": query,
            "filters": {
                "visual_type": visual_type,
                "subject": subject
            }
        })
        
    except Exception as e:
        logger.error(f"Error searching visual aids: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{visual_aid_id}")
async def get_visual_aid(visual_aid_id: str):
    """Get a specific visual aid by ID"""
    try:
        # Get visual aid from database
        visual_aid = visual_aid_dao.get_visual_aid(visual_aid_id)
        
        if not visual_aid:
            raise HTTPException(status_code=404, detail="Visual aid not found")
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": visual_aid.get("id"),
                "title": f"{visual_aid.get('subject', 'General')}: {visual_aid.get('topic', 'Visual Aid')}",
                "topic": visual_aid.get("topic"),
                "subject": visual_aid.get("subject"),
                "grade": visual_aid.get("grade_level"),
                "visual_type": visual_aid.get("visual_type"),
                "style": visual_aid.get("style"),
                "color_scheme": visual_aid.get("color_scheme"),
                "content": visual_aid.get("content"),
                "image_url": f"http://localhost:8000/api/v1/visual-aids/{visual_aid.get('id')}/image",  # Backend image URL
                "download_url": f"http://localhost:8000/api/v1/visual-aids/{visual_aid.get('id')}/download",  # Backend download URL
                "preview_url": f"http://localhost:8000/api/v1/visual-aids/{visual_aid.get('id')}/preview",  # Backend preview URL
                "content_url": f"http://localhost:8000/api/v1/visual-aids/{visual_aid.get('id')}/content",  # Backend content URL
                "image_filename": visual_aid.get("image_filename"),
                "metadata": visual_aid.get("metadata", {}),
                "created_at": visual_aid.get("created_at"),
                "status": visual_aid.get("status", "completed")
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visual aid: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{visual_aid_id}")
async def delete_visual_aid(visual_aid_id: str, user_id: str = None):
    """Delete a visual aid"""
    try:
        # Delete from database using DAO
        success = visual_aid_dao.delete_visual_aid(visual_aid_id, user_id or "default_user")
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Visual aid deleted successfully",
                "visual_aid_id": visual_aid_id
            })
        else:
            raise HTTPException(status_code=404, detail="Visual aid not found or not authorized")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting visual aid: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{visual_aid_id}/image")
async def get_visual_aid_image(visual_aid_id: str):
    """Get the actual image file for a visual aid"""
    try:
        # Get visual aid from database
        visual_aid = visual_aid_dao.get_visual_aid(visual_aid_id)
        
        if not visual_aid:
            raise HTTPException(status_code=404, detail="Visual aid not found")
        
        # Get image path
        image_path = visual_aid.get("image_path")
        if not image_path or not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file not found")
        
        # Return the actual image file
        return FileResponse(
            path=image_path,
            media_type='image/png',
            filename=visual_aid.get("image_filename", "visual_aid.png")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visual aid image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{visual_aid_id}/download")
async def download_visual_aid_image(visual_aid_id: str):
    """Download the visual aid image"""
    try:
        # Get visual aid from database
        visual_aid = visual_aid_dao.get_visual_aid(visual_aid_id)
        
        if not visual_aid:
            raise HTTPException(status_code=404, detail="Visual aid not found")
        
        # Get image path
        image_path = visual_aid.get("image_path")
        if not image_path or not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file not found")
        
        # Generate download filename
        topic = visual_aid.get("topic", "visual_aid").replace(" ", "_")
        subject = visual_aid.get("subject", "general").replace(" ", "_")
        visual_type = visual_aid.get("visual_type", "image")
        download_filename = f"{subject}_{topic}_{visual_type}.png"
        
        # Return file for download
        return FileResponse(
            path=image_path,
            media_type='image/png',
            filename=download_filename,
            headers={"Content-Disposition": f"attachment; filename={download_filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading visual aid image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{visual_aid_id}/preview")
async def get_visual_aid_preview(visual_aid_id: str):
    """Get a preview image for a visual aid"""
    try:
        # Get visual aid from database
        visual_aid = visual_aid_dao.get_visual_aid(visual_aid_id)
        
        if not visual_aid:
            raise HTTPException(status_code=404, detail="Visual aid not found")
        
        # Check if actual image exists
        image_path = visual_aid.get("image_path")
        if image_path and os.path.exists(image_path):
            # If it's a Mermaid file, return the content as text for preview
            if image_path.endswith('.mmd'):
                with open(image_path, 'r', encoding='utf-8') as f:
                    mermaid_content = f.read()
                
                return JSONResponse({
                    "success": True,
                    "data": {
                        "type": "mermaid",
                        "content": mermaid_content,
                        "visual_type": visual_aid.get("visual_type"),
                        "title": f"{visual_aid.get('subject', 'General')}: {visual_aid.get('topic', 'Visual Aid')}",
                        "can_render": True,
                        "instructions": "This is a Mermaid diagram. Use a Mermaid renderer to visualize it."
                    }
                })
            else:
                # Return the actual image as preview for other formats
                return FileResponse(
                    path=image_path,
                    media_type='image/png'
                )
        else:
            # Return metadata with placeholder info
            visual_type = visual_aid.get("visual_type", "infographic")
            placeholder_images = {
                "infographic": "https://via.placeholder.com/800x600/3498db/ffffff?text=Infographic+Preview",
                "illustration": "https://via.placeholder.com/800x600/e74c3c/ffffff?text=Illustration+Preview", 
                "diagram": "https://via.placeholder.com/800x600/2ecc71/ffffff?text=Diagram+Preview",
                "chart": "https://via.placeholder.com/800x600/f39c12/ffffff?text=Chart+Preview",
                "mind_map": "https://via.placeholder.com/800x600/9b59b6/ffffff?text=Mind+Map+Preview",
                "timeline": "https://via.placeholder.com/800x600/1abc9c/ffffff?text=Timeline+Preview"
            }
            
            placeholder_url = placeholder_images.get(visual_type, placeholder_images["infographic"])
            
            return JSONResponse({
                "success": True,
                "data": {
                    "image_url": placeholder_url,
                    "visual_type": visual_type,
                    "title": f"{visual_aid.get('subject', 'General')}: {visual_aid.get('topic', 'Visual Aid')}"
                }
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visual aid preview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{visual_aid_id}/content")
async def get_visual_aid_content(visual_aid_id: str):
    """Get the text content of a visual aid"""
    try:
        # Get visual aid from database
        visual_aid = visual_aid_dao.get_visual_aid(visual_aid_id)
        
        if not visual_aid:
            raise HTTPException(status_code=404, detail="Visual aid not found")
        
        return JSONResponse({
            "success": True,
            "data": {
                "id": visual_aid.get("id"),
                "title": f"{visual_aid.get('subject', 'General')}: {visual_aid.get('topic', 'Visual Aid')}",
                "content": visual_aid.get("content"),
                "visual_type": visual_aid.get("visual_type"),
                "metadata": visual_aid.get("metadata", {})
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visual aid content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
