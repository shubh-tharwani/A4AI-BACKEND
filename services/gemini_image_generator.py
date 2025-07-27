"""
Gemini Image Generator Service
Uses Vertex AI Gemini to generate images directly for educational visual aids
"""
import os
import uuid
import logging
import base64
from typing import Dict, Any, Tuple
from datetime import datetime
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from config import Config

logger = logging.getLogger(__name__)

class GeminiImageGenerator:
    def __init__(self):
        self.output_dir = os.path.join(os.getcwd(), "temp_image")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize Vertex AI
        vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
        self.model = GenerativeModel(Config.VERTEX_MODEL)  # Use model from config
        
    def generate_image(
        self, 
        content: str, 
        visual_type: str, 
        topic: str,
        subject: str,
        grade: str,
        style: str = "modern",
        color_scheme: str = "blue"
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Generate an educational image using Vertex AI Gemini
        
        Returns:
            Tuple[str, str, Dict]: (file_path, filename, metadata)
        """
        try:
            # Create image generation prompt
            image_prompt = self._create_image_prompt(
                content, visual_type, topic, subject, grade, style, color_scheme
            )
            
            # Generate image using Gemini with specific PNG format requirement
            response = self.model.generate_content([
                image_prompt,
                "Generate a high-quality PNG image file only. Do not generate text, code, or any other format.",
                "The output must be a PNG image that is clear, informative, and visually appealing.",
                "Return only the PNG image data, no other content types are acceptable.",
                "The image should be suitable for educational use and appropriate for the specified grade level."
            ])
            
            # Generate unique filename
            unique_id = str(uuid.uuid4())[:8]
            safe_topic = topic.replace(" ", "_").replace("/", "_")[:20]
            safe_subject = subject.replace(" ", "_").replace("/", "_")[:15]
            filename = f"{visual_type}_{safe_subject}_{safe_topic}_{unique_id}.png"
            file_path = os.path.join(self.output_dir, filename)
            
            # Check if response contains image data
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data'):
                            # Verify it's PNG format
                            mime_type = getattr(part.inline_data, 'mime_type', '')
                            if mime_type != 'image/png':
                                logger.warning(f"Received non-PNG format: {mime_type}, creating fallback")
                                return self._create_fallback_image(topic, subject, visual_type, content)
                            
                            # Save the generated PNG image
                            image_data = part.inline_data.data
                            with open(file_path, 'wb') as f:
                                f.write(base64.b64decode(image_data))
                            
                            # Get file metadata
                            file_stat = os.stat(file_path)
                            
                            metadata = {
                                "filename": filename,
                                "file_path": file_path,
                                "size": file_stat.st_size,
                                "format": "PNG",
                                "visual_type": visual_type,
                                "topic": topic,
                                "subject": subject,
                                "grade": grade,
                                "created_at": datetime.now().isoformat(),
                                "color_scheme": color_scheme,
                                "style": style,
                                "content_type": "image/png",
                                "can_render": True,
                                "dimensions": "1024x1024",  # Standard Gemini image dimensions
                                "source": "gemini_generated",
                                "generation_method": "gemini_ai_direct"
                            }
                            
                            logger.info(f"Generated image with Gemini: {filename} ({file_stat.st_size} bytes)")
                            return file_path, filename, metadata
            
            # If no image data, create fallback
            logger.warning("No image data in Gemini response, creating fallback")
            return self._create_fallback_image(topic, subject, visual_type, content)
            
        except Exception as e:
            logger.error(f"Error generating image with Gemini: {str(e)}")
            # Create fallback
            return self._create_fallback_image(topic, subject, visual_type, content)
    
    def _create_image_prompt(
        self, 
        content: str, 
        visual_type: str, 
        topic: str, 
        subject: str, 
        grade: str, 
        style: str, 
        color_scheme: str
    ) -> str:
        """Create a detailed prompt for image generation"""
        
        # Base prompt for educational image
        base_prompt = f"""
        Create an educational image about "{topic}" for grade {grade} {subject} students.
        
        Content to visualize: {content[:300]}
        
        Style: {style}
        Color scheme: {color_scheme}
        
        IMPORTANT: Generate only a PNG image file. No other formats are acceptable.
        
        Requirements:
        - Output format: PNG image only
        - High quality and clear visual elements
        - Age-appropriate for grade {grade}
        - Educational and informative
        - Visually engaging and interactive
        - Include relevant icons, illustrations, and text
        - Use the {color_scheme} color scheme effectively
        - Professional {style} design
        - Standard image dimensions (1024x1024 or similar)
        """
        
        return base_prompt + f"""
        
        Additional details:
        - Subject: {subject}
        - Grade level: {grade}
        - Make it suitable for educational use
        - Ensure readability and clarity
        - Include interactive visual elements
        """
    
    def _create_fallback_image(
        self, 
        topic: str, 
        subject: str, 
        visual_type: str, 
        content: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Create a fallback PNG image when Gemini image generation fails"""
        try:
            filename = f"fallback_{visual_type}_{uuid.uuid4().hex[:8]}.png"
            file_path = os.path.join(self.output_dir, filename)
            
            # Create a fallback PNG image using PIL
            success = self._create_educational_fallback_png(topic, subject, visual_type, content, file_path)
            
            if not success:
                # If PIL fails, create a simple text file as last resort
                filename = f"fallback_{visual_type}_{uuid.uuid4().hex[:8]}.txt"
                file_path = os.path.join(self.output_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Educational Visual Aid\n\nSubject: {subject}\nTopic: {topic}\nType: {visual_type}\n\nContent:\n{content[:500]}...")
            
            file_stat = os.stat(file_path)
            metadata = {
                "filename": filename,
                "file_path": file_path,
                "size": file_stat.st_size,
                "format": "PNG" if file_path.endswith('.png') else "Text",
                "visual_type": visual_type,
                "topic": topic,
                "subject": subject,
                "created_at": datetime.now().isoformat(),
                "is_fallback": True,
                "content_type": "image/png" if file_path.endswith('.png') else "text/plain",
                "can_render": True,
                "dimensions": "800x600" if file_path.endswith('.png') else "text",
                "source": "fallback_generated",
                "generation_method": "fallback_pil"
            }
            
            logger.info(f"Created fallback image: {filename}")
            return file_path, filename, metadata
            
        except Exception as e:
            logger.error(f"Error creating fallback image: {str(e)}")
            raise
    
    def _create_educational_fallback_png(
        self, 
        topic: str, 
        subject: str, 
        visual_type: str, 
        content: str,
        output_path: str
    ) -> bool:
        """Create an educational PNG image as fallback"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create image with educational theme
            width, height = 800, 600
            
            # Color schemes
            color_schemes = {
                "blue": {"bg": "#f0f8ff", "header": "#1e40af", "accent": "#3b82f6", "text": "#1f2937"},
                "green": {"bg": "#f0fdf4", "header": "#059669", "accent": "#10b981", "text": "#1f2937"},
                "purple": {"bg": "#faf5ff", "header": "#7c3aed", "accent": "#8b5cf6", "text": "#1f2937"},
                "orange": {"bg": "#fff7ed", "header": "#ea580c", "accent": "#f97316", "text": "#1f2937"},
            }
            
            colors = color_schemes.get("blue")  # Default to blue
            
            # Create image
            image = Image.new('RGB', (width, height), colors["bg"])
            draw = ImageDraw.Draw(image)
            
            # Try to load fonts
            try:
                title_font = ImageFont.truetype("arial.ttf", 28)
                subtitle_font = ImageFont.truetype("arial.ttf", 20)
                body_font = ImageFont.truetype("arial.ttf", 16)
                small_font = ImageFont.truetype("arial.ttf", 12)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                body_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Draw header with rounded rectangle effect
            header_height = 100
            draw.rectangle([(0, 0), (width, header_height)], fill=colors["header"])
            draw.rectangle([(10, 10), (width-10, header_height-10)], outline=colors["accent"], width=2)
            
            # Title and subject
            draw.text((30, 25), f"{subject.upper()}", fill='white', font=subtitle_font)
            draw.text((30, 55), topic.title(), fill='white', font=title_font)
            
            # Visual type badge
            badge_x = width - 200
            draw.rectangle([(badge_x, 20), (width-20, 50)], fill=colors["accent"])
            draw.text((badge_x + 10, 28), f"{visual_type.title()}", fill='white', font=small_font)
            
            # Content area
            y_pos = header_height + 30
            
            # Add visual type specific content
            if visual_type == "infographic":
                self._draw_infographic_elements(draw, width, y_pos, colors, body_font, small_font)
            elif visual_type == "diagram":
                self._draw_diagram_elements(draw, width, y_pos, colors, body_font, small_font)
            elif visual_type == "chart":
                self._draw_chart_elements(draw, width, y_pos, colors, body_font, small_font)
            elif visual_type == "mind_map":
                self._draw_mindmap_elements(draw, width, y_pos, colors, body_font, small_font)
            elif visual_type == "timeline":
                self._draw_timeline_elements(draw, width, y_pos, colors, body_font, small_font)
            else:
                self._draw_generic_elements(draw, width, y_pos, colors, body_font, small_font)
            
            # Add content preview
            content_y = y_pos + 200
            draw.text((30, content_y), "Content Preview:", fill=colors["text"], font=subtitle_font)
            
            # Split content into lines
            content_lines = content[:200].split('\n')[:8]  # First 8 lines, max 200 chars
            line_y = content_y + 30
            for line in content_lines:
                if line_y > height - 80:
                    break
                draw.text((30, line_y), line[:60], fill=colors["text"], font=small_font)
                line_y += 18
            
            # Footer
            footer_y = height - 50
            draw.rectangle([(0, footer_y), (width, height)], fill="#f3f4f6")
            draw.text((30, footer_y + 15), f"Generated by AI Education System • {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
                     fill="#6b7280", font=small_font)
            
            # Save image
            image.save(output_path, 'PNG')
            return True
            
        except ImportError:
            logger.warning("PIL not available for fallback image creation")
            return False
        except Exception as e:
            logger.error(f"Error creating educational fallback PNG: {e}")
            return False
    
    def _draw_infographic_elements(self, draw, width, y_pos, colors, body_font, small_font):
        """Draw infographic-style elements"""
        # Draw some boxes and icons
        box_width = 150
        box_height = 80
        spacing = 30
        
        for i in range(3):
            x = 30 + i * (box_width + spacing)
            draw.rectangle([(x, y_pos), (x + box_width, y_pos + box_height)], 
                          fill=colors["accent"], outline=colors["header"], width=2)
            draw.text((x + 10, y_pos + 10), f"Section {i+1}", fill='white', font=body_font)
            draw.text((x + 10, y_pos + 35), "Key Information", fill='white', font=small_font)
            draw.text((x + 10, y_pos + 50), "Details & Facts", fill='white', font=small_font)
    
    def _draw_diagram_elements(self, draw, width, y_pos, colors, body_font, small_font):
        """Draw diagram-style elements"""
        # Draw connected boxes
        box_size = 60
        positions = [(100, y_pos), (300, y_pos), (500, y_pos + 50), (300, y_pos + 100)]
        
        for i, (x, y) in enumerate(positions):
            draw.rectangle([(x, y), (x + box_size, y + box_size)], 
                          fill=colors["accent"], outline=colors["header"], width=2)
            draw.text((x + 15, y + 20), f"Step {i+1}", fill='white', font=small_font)
            
            # Draw arrows between boxes
            if i < len(positions) - 1:
                next_x, next_y = positions[i + 1]
                draw.line([(x + box_size, y + box_size//2), (next_x, next_y + box_size//2)], 
                         fill=colors["header"], width=3)
    
    def _draw_chart_elements(self, draw, width, y_pos, colors, body_font, small_font):
        """Draw chart-style elements"""
        # Draw simple bar chart
        bar_width = 40
        max_height = 120
        values = [80, 120, 60, 100, 90]
        
        for i, value in enumerate(values):
            x = 50 + i * (bar_width + 20)
            bar_height = int(value)
            draw.rectangle([(x, y_pos + max_height - bar_height), (x + bar_width, y_pos + max_height)], 
                          fill=colors["accent"])
            draw.text((x + 5, y_pos + max_height + 10), f"Cat {i+1}", fill=colors["text"], font=small_font)
    
    def _draw_mindmap_elements(self, draw, width, y_pos, colors, body_font, small_font):
        """Draw mind map-style elements"""
        # Central topic
        center_x, center_y = width // 2, y_pos + 60
        draw.ellipse([(center_x - 60, center_y - 30), (center_x + 60, center_y + 30)], 
                    fill=colors["header"])
        draw.text((center_x - 35, center_y - 10), "Main Topic", fill='white', font=body_font)
        
        # Branches
        branch_positions = [(-100, -40), (100, -40), (-80, 50), (80, 50)]
        for i, (dx, dy) in enumerate(branch_positions):
            x, y = center_x + dx, center_y + dy
            draw.ellipse([(x - 40, y - 20), (x + 40, y + 20)], fill=colors["accent"])
            draw.text((x - 25, y - 8), f"Branch {i+1}", fill='white', font=small_font)
            # Draw line to center
            draw.line([(center_x, center_y), (x, y)], fill=colors["header"], width=2)
    
    def _draw_timeline_elements(self, draw, width, y_pos, colors, body_font, small_font):
        """Draw timeline-style elements"""
        # Draw timeline line
        timeline_y = y_pos + 60
        draw.line([(50, timeline_y), (width - 50, timeline_y)], fill=colors["header"], width=4)
        
        # Draw events
        events = ["2020", "2021", "2022", "2023", "2024"]
        event_spacing = (width - 100) // len(events)
        
        for i, event in enumerate(events):
            x = 50 + i * event_spacing
            # Draw event marker
            draw.ellipse([(x - 8, timeline_y - 8), (x + 8, timeline_y + 8)], fill=colors["accent"])
            # Draw event box
            draw.rectangle([(x - 30, timeline_y - 50), (x + 30, timeline_y - 20)], 
                          fill=colors["accent"], outline=colors["header"], width=1)
            draw.text((x - 15, timeline_y - 40), event, fill='white', font=small_font)
    
    def _draw_generic_elements(self, draw, width, y_pos, colors, body_font, small_font):
        """Draw generic educational elements"""
        # Draw some educational icons and text
        elements = ["📚 Learning", "🎯 Objectives", "💡 Concepts", "📊 Data", "🔍 Analysis"]
        
        for i, element in enumerate(elements):
            y = y_pos + i * 35
            draw.rectangle([(30, y), (width - 30, y + 25)], fill=colors["accent"], outline=colors["header"], width=1)
            draw.text((40, y + 5), element, fill='white', font=body_font)
