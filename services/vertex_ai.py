"""
Vertex AI Service
Centralized service for AI text generation using Google Vertex AI with Gemini models
Updated to fix config import issue
"""
import os
import sys
import logging
import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Optional, Dict, Any

# Add parent directory to path to import config.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

logger = logging.getLogger(__name__)

class VertexAIService:
    """Centralized Vertex AI service for text generation"""
    
    def __init__(self):
        """Initialize Vertex AI with project configuration"""
        try:
            # Set credentials before initializing Vertex AI
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = Config.GOOGLE_APPLICATION_CREDENTIALS
            
            # Initialize Vertex AI
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            
            self.model_name = Config.VERTEX_MODEL
            logger.info(f"Vertex AI initialized with model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise
    
    def generate_text(self, prompt: str, max_output_tokens: Optional[int] = None, temperature: Optional[float] = None) -> str:
        """
        Generate text using Vertex AI Gemini model
        
        Args:
            prompt: Text prompt for generation
            max_output_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If text generation fails
        """
        try:
            print(f"🤖 Initializing model: {self.model_name}")
            model = GenerativeModel(self.model_name)
            
            # Prepare generation config
            generation_config = {}
            if max_output_tokens:
                generation_config['max_output_tokens'] = max_output_tokens
            if temperature is not None:
                generation_config['temperature'] = temperature
            
            print(f"🔧 Generation config: {generation_config}")
            print(f"📝 Prompt length: {len(prompt)} characters")
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config if generation_config else None
            )
            
            print(f"📨 Response object: {type(response)}")
            print(f"📄 Response text length: {len(response.text) if response.text else 0}")
            
            if not response.text:
                logger.warning("Empty response from Vertex AI")
                print("⚠️ Empty response from Vertex AI")
                return "I apologize, but I couldn't generate a response at this time."
            
            return response.text.strip()
            
        except Exception as e:
            error_msg = f"Error generating text with Vertex AI: {str(e)}"
            print(f"❌ Vertex AI Error: {error_msg}")
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def generate_educational_content(self, prompt: str, content_type: str = "general") -> str:
        """
        Generate educational content with optimized settings
        
        Args:
            prompt: Educational content prompt
            content_type: Type of content (story, lesson, assessment, etc.)
            
        Returns:
            Generated educational content
        """
        try:
            # Optimize parameters based on content type
            if content_type == "story":
                temperature = 0.9
                max_tokens = 2000
            elif content_type == "lesson":
                temperature = 0.7
                max_tokens = 3000
            elif content_type == "assessment":
                temperature = 0.5
                max_tokens = 1500
            else:
                temperature = 0.8
                max_tokens = 2000
            
            return self.generate_text(
                prompt=prompt,
                max_output_tokens=max_tokens,
                temperature=temperature
            )
            
        except Exception as e:
            logger.error(f"Error generating {content_type} content: {e}")
            raise

# Create global instance
vertex_ai_service = VertexAIService()

# Legacy function for backward compatibility
def generate_text(prompt: str) -> str:
    """Legacy function for backward compatibility"""
    try:
        return vertex_ai_service.generate_text(prompt)
    except Exception as e:
        return f"Error generating text: {str(e)}"
