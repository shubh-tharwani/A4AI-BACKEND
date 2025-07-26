"""
Visual Aid Routes - Fixed Version
FastAPI routes for educational visual content generation with actual image creation
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import os
import uuid
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/visual-aids", tags=["Visual Aids"])


# Request Models
class VisualAidRequest(BaseModel):
    topic: str = Field(..., description="Topic for the visual aid")
    grade: str = Field(..., description="Grade level")
    subject: str = Field(..., description="Subject area")
    visualType: str = Field(default="infographic", description="Type of visual aid")
    style: Optional[str] = Field(default="modern", description="Visual style")
    color_scheme: Optional[str] = Field(default="blue", description="Color scheme")


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


# Visual Aid Generation Routes
@router.post("/generate")
async def generate_visual_aid(request: VisualAidRequest):
    """Generate a visual aid with actual image content"""
    try:
        logger.info(f"Generating visual aid for topic: {request.topic}")
        
        # Generate the actual image
        image_data = create_visual_aid_image(request)
        
        # Save the image and get metadata
        image_info = save_visual_aid_image(image_data, request)
        
        return JSONResponse({
            "success": True,
            "message": "Visual aid generated successfully",
            "data": {
                "id": image_info["id"],
                "image_url": image_info["image_url"], 
                "filename": image_info["filename"],
                "metadata": {
                    "topic": request.topic,
                    "grade": request.grade,
                    "subject": request.subject,
                    "visual_type": request.visualType,
                    "image_size": image_info["size"],
                    "created_at": image_info["created_at"],
                    "dimensions": image_info["dimensions"]
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating visual aid: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infographic")
async def create_infographic(request: InfographicRequest):
    """Create an infographic with actual image content"""
    try:
        logger.info(f"Creating infographic for: {request.topic}")
        
        # Convert to VisualAidRequest format
        visual_request = VisualAidRequest(
            topic=request.topic,
            grade=request.grade,
            subject=request.subject,
            visualType="infographic",
            style=request.style
        )
        
        # Generate infographic
        image_data = create_infographic_image(visual_request)
        image_info = save_visual_aid_image(image_data, visual_request, "infographic")
        
        return JSONResponse({
            "success": True,
            "message": "Infographic created successfully",
            "data": {
                "id": image_info["id"],
                "image_url": image_info["image_url"],
                "filename": image_info["filename"],
                "metadata": {
                    "topic": request.topic,
                    "grade": request.grade,
                    "subject": request.subject,
                    "visual_type": "infographic",
                    "image_size": image_info["size"],
                    "created_at": image_info["created_at"],
                    "dimensions": image_info["dimensions"]
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating infographic: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my-visual-aids")
async def get_user_visual_aids():
    """Get list of generated visual aids"""
    try:
        # Get list of generated visual aids
        visual_aids_dir = os.path.join(os.getcwd(), "uploads", "visual_aids")
        visual_aids = []
        
        if os.path.exists(visual_aids_dir):
            for filename in os.listdir(visual_aids_dir):
                if filename.endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(visual_aids_dir, filename)
                    file_stat = os.stat(file_path)
                    
                    visual_aids.append({
                        "id": filename.split('.')[0],
                        "filename": filename,
                        "image_url": f"http://localhost:8000/uploads/visual_aids/{filename}",
                        "size": file_stat.st_size,
                        "created_at": datetime.fromtimestamp(file_stat.st_ctime).isoformat()
                    })
        
        return JSONResponse({
            "success": True,
            "data": visual_aids,
            "total": len(visual_aids)
        })
        
    except Exception as e:
        logger.error(f"Error getting visual aids: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_visual_aids(query: str = ""):
    """Search visual aids"""
    try:
        # Get all aids first
        response = await get_user_visual_aids()
        all_aids = response.body.decode() if hasattr(response, 'body') else {"data": []}
        
        if isinstance(all_aids, str):
            import json
            all_aids = json.loads(all_aids)
        
        if query and "data" in all_aids:
            filtered_aids = [aid for aid in all_aids["data"] if query.lower() in aid["filename"].lower()]
            return JSONResponse({
                "success": True,
                "data": filtered_aids,
                "total": len(filtered_aids)
            })
        return JSONResponse(all_aids)
        
    except Exception as e:
        logger.error(f"Error searching visual aids: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Image Generation Functions
def create_visual_aid_image(request: VisualAidRequest) -> bytes:
    """Generate a visual aid image using PIL"""
    try:
        # Create a new image
        width, height = 800, 600
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Color schemes
        color_schemes = {
            'blue': {'primary': '#2E86AB', 'secondary': '#A23B72', 'accent': '#F18F01'},
            'green': {'primary': '#588B8B', 'secondary': '#C8AD7F', 'accent': '#F2E394'},
            'purple': {'primary': '#6A4C93', 'secondary': '#C8AD7F', 'accent': '#FFD23F'},
        }
        
        colors = color_schemes.get(request.color_scheme, color_schemes['blue'])
        
        # Draw header background
        draw.rectangle([0, 0, width, 80], fill=colors['primary'])
        
        # Try to load a font, fallback to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 24)
            content_font = ImageFont.truetype("arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
        
        # Draw title
        title = f"{request.subject}: {request.topic}"
        draw.text((20, 25), title, fill='white', font=title_font)
        
        # Draw grade level
        draw.text((20, 100), f"Grade: {request.grade}", fill=colors['primary'], font=content_font)
        
        # Draw visual type
        draw.text((20, 130), f"Type: {request.visualType.title()}", fill=colors['secondary'], font=content_font)
        
        # Add some educational content boxes
        box_y = 180
        concepts = [
            f"Key Concept 1: Understanding {request.topic}",
            f"Key Concept 2: Applications of {request.topic}",
            f"Key Concept 3: Practice with {request.topic}"
        ]
        
        for i, concept in enumerate(concepts):
            # Draw box
            draw.rectangle([20, box_y, width-20, box_y+60], outline=colors['primary'], width=2)
            draw.text((30, box_y+20), concept, fill=colors['primary'], font=content_font)
            box_y += 80
        
        # Add footer
        draw.rectangle([0, height-50, width, height], fill=colors['accent'])
        draw.text((20, height-35), "Generated by AI Education Assistant", fill='black', font=content_font)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG', quality=95)
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        # Return a simple fallback image
        return create_fallback_image(request)


def create_infographic_image(request: VisualAidRequest) -> bytes:
    """Generate an infographic-style image"""
    try:
        width, height = 800, 1000
        image = Image.new('RGB', (width, height), color='#f8f9fa')
        draw = ImageDraw.Draw(image)
        
        # Load fonts
        try:
            title_font = ImageFont.truetype("arial.ttf", 32)
            subtitle_font = ImageFont.truetype("arial.ttf", 20)
            content_font = ImageFont.truetype("arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
        
        # Colors
        primary_color = '#2c3e50'
        accent_color = '#3498db'
        highlight_color = '#e74c3c'
        
        # Header
        draw.rectangle([0, 0, width, 120], fill=primary_color)
        draw.text((40, 40), f"{request.topic}", fill='white', font=title_font)
        
        # Grade and Subject
        draw.text((40, 150), f"{request.grade} • {request.subject}", fill=accent_color, font=subtitle_font)
        
        # Content sections
        sections = [
            "What is it?",
            "Why is it important?",
            "How does it work?",
            "Real-world examples"
        ]
        
        y_pos = 220
        for i, section in enumerate(sections):
            # Section header
            draw.rectangle([40, y_pos, width-40, y_pos+40], fill=accent_color)
            draw.text((50, y_pos+10), section, fill='white', font=subtitle_font)
            
            # Section content
            content_y = y_pos + 60
            draw.text((50, content_y), f"This section explains {section.lower()}", fill=primary_color, font=content_font)
            draw.text((50, content_y+25), f"in relation to {request.topic}.", fill=primary_color, font=content_font)
            
            y_pos += 140
        
        # Footer
        draw.rectangle([0, height-60, width, height], fill=highlight_color)
        draw.text((40, height-40), "AI Generated Educational Content", fill='white', font=content_font)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG', quality=95)
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating infographic: {str(e)}")
        return create_fallback_image(request)


def create_fallback_image(request: VisualAidRequest) -> bytes:
    """Generate a simple fallback image when other methods fail"""
    try:
        width, height = 800, 600
        image = Image.new('RGB', (width, height), color='#f0f0f0')
        draw = ImageDraw.Draw(image)
        
        # Simple centered text
        font = ImageFont.load_default()
        text = f"{request.subject}: {request.topic}\nGrade: {request.grade}"
        
        # Get text size and center it
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill='black', font=font)
        
        # Convert to bytes
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating fallback image: {str(e)}")
        # Return minimal 1x1 pixel image as absolute fallback
        minimal_image = Image.new('RGB', (1, 1), color='white')
        img_buffer = io.BytesIO()
        minimal_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer.getvalue()


def save_visual_aid_image(image_data: bytes, request: VisualAidRequest, prefix: str = "visual_aid") -> dict:
    """Save the image and return metadata"""
    try:
        # Create directory
        uploads_dir = os.path.join(os.getcwd(), "uploads", "visual_aids")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        safe_topic = request.topic.replace(" ", "_").replace("/", "_")[:20]
        safe_subject = request.subject.replace(" ", "_").replace("/", "_")[:15]
        filename = f"{prefix}_{safe_subject}_{safe_topic}_{unique_id}.png"
        file_path = os.path.join(uploads_dir, filename)
        
        # Save image
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Get file info
        file_stat = os.stat(file_path)
        
        # Get image dimensions
        try:
            with Image.open(file_path) as img:
                dimensions = f"{img.width}x{img.height}"
        except:
            dimensions = "unknown"
        
        return {
            "id": unique_id,
            "filename": filename,
            "image_url": f"http://localhost:8000/uploads/visual_aids/{filename}",
            "size": file_stat.st_size,
            "created_at": datetime.now().isoformat(),
            "dimensions": dimensions
        }
        
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        raise
