"""
Image Generator Service
Uses Vertex AI Gemini to generate Mermaid diagrams and converts them to PNG images
"""
import os
import uuid
import logging
import subprocess
import tempfile
from typing import Dict, Any, Tuple
from datetime import datetime
import vertexai
from vertexai.generative_models import GenerativeModel
from config import Config

logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self):
        self.output_dir = os.path.join(os.getcwd(), "temp_image")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize Vertex AI
        vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
        self.model = GenerativeModel(Config.VERTEX_MODEL)
        
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
        Generate a Mermaid diagram using Vertex AI Gemini
        
        Returns:
            Tuple[str, str, Dict]: (file_path, filename, metadata)
        """
        try:
            # Create detailed prompt for Mermaid diagram generation
            mermaid_prompt = self._create_mermaid_prompt(
                content, visual_type, topic, subject, grade, style, color_scheme
            )
            
            # Generate Mermaid diagram using Gemini
            response = self.model.generate_content([
                f"Generate a Mermaid diagram based on this prompt: {mermaid_prompt}",
                "Create valid Mermaid syntax that is educational, clear, and appropriate for the specified grade level.",
                "The diagram should be informative and visually appealing when rendered.",
                "Only return the Mermaid code, starting with the diagram type (flowchart, graph, mindmap, etc.)"
            ])
            
            # Generate unique filename with .mmd extension
            unique_id = str(uuid.uuid4())[:8]
            safe_topic = topic.replace(" ", "_").replace("/", "_")[:20]
            safe_subject = subject.replace(" ", "_").replace("/", "_")[:15]
            filename = f"{visual_type}_{safe_subject}_{safe_topic}_{unique_id}.mmd"
            file_path = os.path.join(self.output_dir, filename)
            
            # Clean up the Mermaid code
            mermaid_code = self._clean_mermaid_code(response.text)
            
            # Generate unique filename with .png extension
            unique_id = str(uuid.uuid4())[:8]
            safe_topic = topic.replace(" ", "_").replace("/", "_")[:20]
            safe_subject = subject.replace(" ", "_").replace("/", "_")[:15]
            filename = f"{visual_type}_{safe_subject}_{safe_topic}_{unique_id}.png"
            file_path = os.path.join(self.output_dir, filename)
            
            # Convert Mermaid to PNG image
            success = self._convert_mermaid_to_png(mermaid_code, file_path)
            
            if not success:
                logger.warning("Mermaid to PNG conversion failed, creating fallback")
                return self._create_fallback_image(topic, subject, visual_type, content)
            
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
                "dimensions": f"{800}x{600}",  # Standard dimensions
                "source": "mermaid_diagram"
            }
            
            logger.info(f"Generated Mermaid diagram: {filename} ({file_stat.st_size} bytes)")
            return file_path, filename, metadata
            
        except Exception as e:
            logger.error(f"Error generating Mermaid diagram with Gemini: {str(e)}")
            # Create fallback
            return self._create_fallback_image(topic, subject, visual_type, content)
    
    def _create_mermaid_prompt(
        self, 
        content: str, 
        visual_type: str, 
        topic: str, 
        subject: str, 
        grade: str, 
        style: str, 
        color_scheme: str
    ) -> str:
        """Create a detailed prompt for Mermaid diagram generation"""
        
        # Define Mermaid diagram types based on visual type
        mermaid_type_mapping = {
            "diagram": "flowchart TD",
            "infographic": "flowchart LR", 
            "chart": "graph TD",
            "illustration": "flowchart TB",
            "mind_map": "mindmap",
            "timeline": "timeline"
        }
        
        mermaid_type = mermaid_type_mapping.get(visual_type, "flowchart TD")
        
        prompt_parts = [
            f"Create a {mermaid_type} Mermaid diagram about '{topic}' for {subject} class, Grade {grade}.",
            f"Educational content to visualize: {content[:500]}",
            f"Style: {style}, Color scheme: {color_scheme}",
        ]
        
        # Add specific requirements based on visual type
        if visual_type == "diagram":
            prompt_parts.extend([
                "Create a flowchart showing relationships and processes.",
                "Include labeled components with clear connections.",
                "Use boxes, diamonds, and arrows to show flow and relationships."
            ])
        elif visual_type == "infographic":
            prompt_parts.extend([
                "Create a left-to-right flowchart with information sections.",
                "Include key statistics, facts, and data points.",
                "Use different node shapes for different types of information."
            ])
        elif visual_type == "chart":
            prompt_parts.extend([
                "Create a graph showing data relationships or hierarchies.",
                "Include comparative elements and clear data visualization.",
                "Use appropriate node shapes and connections."
            ])
        elif visual_type == "mind_map":
            prompt_parts.extend([
                "Create a mindmap with the main topic at the center.",
                "Branch out to subtopics and details.",
                "Use the Mermaid mindmap syntax properly."
            ])
        elif visual_type == "timeline":
            prompt_parts.extend([
                "Create a timeline showing chronological progression.",
                "Include dates, events, and sequential relationships.",
                "Use flowchart format to show time progression."
            ])
        else:
            prompt_parts.extend([
                "Create an educational flowchart that illustrates the concept clearly.",
                "Include all important elements and their relationships."
            ])
        
        prompt_parts.extend([
            f"Make it appropriate for Grade {grade} students.",
            "Ensure educational value and visual clarity.",
            "Use proper Mermaid syntax with meaningful node IDs and labels.",
            "Include colors and styling where appropriate.",
            "Make sure the diagram will render correctly in Mermaid."
        ])
        
        return " ".join(prompt_parts)
    
    def _clean_mermaid_code(self, raw_code: str) -> str:
        """Clean and validate Mermaid code"""
        # Remove markdown code blocks if present
        code = raw_code.strip()
        if code.startswith("```mermaid"):
            code = code[10:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        
        # Remove any extra explanatory text before the diagram
        lines = code.split('\n')
        mermaid_start = -1
        
        for i, line in enumerate(lines):
            line = line.strip()
            if (line.startswith('flowchart') or line.startswith('graph') or 
                line.startswith('mindmap') or line.startswith('timeline') or
                line.startswith('sequenceDiagram') or line.startswith('classDiagram')):
                mermaid_start = i
                break
        
        if mermaid_start >= 0:
            code = '\n'.join(lines[mermaid_start:])
        
        return code.strip()
    
    def _convert_mermaid_to_png(self, mermaid_code: str, output_path: str) -> bool:
        """Convert Mermaid diagram code to PNG image"""
        try:
            # Create a temporary Mermaid file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
                temp_file.write(mermaid_code)
                temp_mmd_path = temp_file.name
            
            try:
                # Try using mermaid-cli (mmdc) if available
                result = subprocess.run([
                    'mmdc', 
                    '-i', temp_mmd_path, 
                    '-o', output_path,
                    '-w', '800',
                    '-H', '600',
                    '-b', 'white'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(output_path):
                    logger.info(f"Successfully converted Mermaid to PNG: {output_path}")
                    return True
                else:
                    logger.warning(f"Mermaid CLI conversion failed: {result.stderr}")
                    return self._create_fallback_png(mermaid_code, output_path)
                    
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("Mermaid CLI not available, creating fallback PNG")
                return self._create_fallback_png(mermaid_code, output_path)
                
        except Exception as e:
            logger.error(f"Error in Mermaid conversion: {e}")
            return self._create_fallback_png(mermaid_code, output_path)
        finally:
            # Clean up temporary file
            if 'temp_mmd_path' in locals() and os.path.exists(temp_mmd_path):
                os.unlink(temp_mmd_path)
    
    def _create_fallback_png(self, mermaid_code: str, output_path: str) -> bool:
        """Create a simple PNG image with diagram text when Mermaid conversion fails"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a white image
            width, height = 800, 600
            image = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(image)
            
            # Try to use default font
            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()
            
            # Add title
            title = "Educational Diagram"
            draw.text((20, 20), title, fill='black', font=font)
            
            # Add truncated Mermaid code
            lines = mermaid_code.split('\n')[:25]  # First 25 lines
            y_pos = 60
            for line in lines:
                if y_pos > height - 40:
                    break
                draw.text((20, y_pos), line[:80], fill='black', font=font)
                y_pos += 20
            
            # Add note at bottom
            draw.text((20, height - 30), "Note: This is a text representation. Use a Mermaid renderer for full visualization.", 
                     fill='gray', font=font)
            
            # Save the image
            image.save(output_path, 'PNG')
            logger.info(f"Created fallback PNG: {output_path}")
            return True
            
        except ImportError:
            logger.error("PIL not available for fallback PNG creation")
            return False
        except Exception as e:
            logger.error(f"Error creating fallback PNG: {e}")
            return False
    
    def _create_mermaid_file(
        self, 
        mermaid_code: str, 
        visual_type: str, 
        topic: str,
        subject: str,
        grade: str,
        style: str,
        color_scheme: str,
        file_path: str
    ):
        """Create the Mermaid diagram file"""
        
        # Color scheme definitions for Mermaid
        color_schemes = {
            "blue": {"primary": "#1e40af", "secondary": "#3b82f6", "accent": "#60a5fa"},
            "green": {"primary": "#059669", "secondary": "#10b981", "accent": "#34d399"},
            "red": {"primary": "#dc2626", "secondary": "#ef4444", "accent": "#f87171"},
            "purple": {"primary": "#7c3aed", "secondary": "#8b5cf6", "accent": "#a78bfa"},
            "orange": {"primary": "#ea580c", "secondary": "#f97316", "accent": "#fb923c"},
            "teal": {"primary": "#0f766e", "secondary": "#14b8a6", "accent": "#5eead4"}
        }
        
        colors = color_schemes.get(color_scheme, color_schemes["blue"])
        
        # Create complete Mermaid file with metadata
        full_content = f"""---
title: {subject.title()}: {topic.title()}
---
{mermaid_code}

%% Educational Visual Aid
%% Subject: {subject.title()}
%% Topic: {topic.title()}
%% Grade: {grade}
%% Style: {style}
%% Color Scheme: {color_scheme}
%% Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
%% Type: {visual_type}
"""
        
        # Save the Mermaid file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        logger.info(f"Saved Mermaid diagram: {file_path}")
    
    def _create_fallback_image(
        self, 
        topic: str, 
        subject: str, 
        visual_type: str, 
        content: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Create a fallback PNG image when Gemini or conversion fails"""
        try:
            filename = f"fallback_{visual_type}_{uuid.uuid4().hex[:8]}.png"
            file_path = os.path.join(self.output_dir, filename)
            
            # Create a simple fallback PNG image
            success = self._create_simple_fallback_png(topic, subject, visual_type, file_path)
            
            if not success:
                # If PIL fails, create a minimal text file as last resort
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
                "dimensions": "800x600" if file_path.endswith('.png') else "text"
            }
            
            logger.info(f"Created fallback image: {filename}")
            return file_path, filename, metadata
            
        except Exception as e:
            logger.error(f"Error creating fallback image: {str(e)}")
            raise
    
    def _create_simple_fallback_png(self, topic: str, subject: str, visual_type: str, output_path: str) -> bool:
        """Create a simple educational PNG image as fallback"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create image
            width, height = 800, 600
            image = Image.new('RGB', (width, height), '#f8f9fa')
            draw = ImageDraw.Draw(image)
            
            # Try to load fonts
            try:
                title_font = ImageFont.truetype("arial.ttf", 24)
                subtitle_font = ImageFont.truetype("arial.ttf", 18)
                body_font = ImageFont.truetype("arial.ttf", 14)
            except:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                body_font = ImageFont.load_default()
            
            # Draw header
            draw.rectangle([(0, 0), (width, 80)], fill='#3b82f6')
            draw.text((20, 20), f"{subject}", fill='white', font=title_font)
            draw.text((20, 50), f"{topic}", fill='white', font=subtitle_font)
            
            # Draw content area
            y_pos = 120
            draw.text((20, y_pos), f"Visual Aid Type: {visual_type.title()}", fill='#374151', font=body_font)
            y_pos += 40
            
            # Add some educational elements
            elements = [
                "📚 Educational Content",
                "🎯 Learning Objectives",
                "💡 Key Concepts",
                "📊 Visual Representation",
                "🔍 Further Exploration"
            ]
            
            for element in elements:
                draw.text((40, y_pos), element, fill='#4b5563', font=body_font)
                y_pos += 35
            
            # Add footer
            draw.rectangle([(0, height-40), (width, height)], fill='#e5e7eb')
            draw.text((20, height-30), "Generated by AI Education Backend", fill='#6b7280', font=body_font)
            
            # Save image
            image.save(output_path, 'PNG')
            return True
            
        except ImportError:
            logger.warning("PIL not available for fallback image creation")
            return False
        except Exception as e:
            logger.error(f"Error creating simple fallback PNG: {e}")
            return False
