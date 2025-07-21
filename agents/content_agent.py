"""
Advanced Content Agent - Enhanced with Google ADK
AI-powered educational content generation with Vertex AI & Firestore Analytics
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

# Google Cloud & ADK imports
from google.cloud import aiplatform, firestore
from vertexai.preview.reasoning_engines import AdkApp, ReasoningEngine
from google.cloud.aiplatform.gapic import JobServiceClient

# Internal imports
from services.content_agent import generate_content
from config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =============================
# Pydantic Models
# =============================
class ContentRequest(BaseModel):
    teacher_id: str
    class_id: str
    content_type: str = "lesson"  # lesson, quiz, worksheet, presentation
    topic: str
    grade_level: str = "elementary"
    duration: int = 30  # minutes
    learning_objectives: Optional[List[str]] = None
    curriculum_standards: Optional[List[str]] = None
    content_format: str = "text"  # text, slides, interactive, multimedia
    difficulty_level: str = "medium"  # easy, medium, hard
    student_data: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None

class ContentResponse(BaseModel):
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    recommendations: List[str]
    next_steps: List[str]
    confidence_score: float

# =============================
# Content Agent
# =============================
class ContentAgent:
    def __init__(self):
        self.name = "advanced_content_agent"
        self.version = "3.0.0"
        self.capabilities = [
            "content_generation", "curriculum_alignment",
            "multimedia_integration", "adaptive_content",
            "interactive_elements", "assessment_integration"
        ]
        self.adk_enabled = False
        self.firestore_client = None
        self.reasoning_engine = None
        self._initialize_adk()

    def _initialize_adk(self):
        """Initialize ADK + Firestore"""
        try:
            # Init Vertex AI
            aiplatform.init(project=Config.PROJECT_ID, location=Config.LOCATION)

            # Firestore
            self.firestore_client = firestore.Client(project=Config.PROJECT_ID)

            # Create ADK Reasoning Engine (with proper error handling)
            try:
                self.reasoning_engine = ReasoningEngine(
                    display_name="content-reasoning-engine",
                    description="Handles reasoning for educational content generation",
                    spec={
                        "class_path": "content_reasoning_engine",
                        "requirements": ["google-cloud-aiplatform", "vertexai"]
                    }
                )
                logger.info("[ADK] Content Reasoning Engine created successfully.")
            except Exception as re_error:
                logger.warning(f"[ADK] Content Reasoning Engine creation failed: {re_error}")
                self.reasoning_engine = None

            self.adk_enabled = True
            logger.info("[ADK] Content Agent initialized successfully.")
        except Exception as e:
            logger.error(f"[ADK Init Error]: {str(e)}")
            self.adk_enabled = False
            self.firestore_client = None
            self.reasoning_engine = None

    async def handle_content_request(self, request: ContentRequest) -> ContentResponse:
        start_time = datetime.now()
        try:
            # Analyze content context
            context = await self._analyze_content_context(request)

            # Generate content
            content = await generate_content(
                topic=request.topic,
                content_type=request.content_type,
                grade_level=request.grade_level,
                duration=request.duration,
                learning_objectives=request.learning_objectives,
                curriculum_standards=request.curriculum_standards,
                content_format=request.content_format,
                difficulty_level=request.difficulty_level
            )

            # Enhance with ADK
            if self.adk_enabled:
                content = await self._enhance_with_adk(content, context, request)

            # Generate recommendations & next steps
            recommendations = await self._generate_recommendations(request, context, content)
            confidence_score = self._calculate_confidence(content, context)
            next_steps = self._generate_next_steps(content, request)

            # Prepare response
            response = ContentResponse(
                content=content,
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "adk_enabled": self.adk_enabled,
                    "reasoning_engine_available": self.reasoning_engine is not None,
                    "agent_version": self.version,
                    "processing_time_sec": (datetime.now() - start_time).total_seconds(),
                    "capabilities": self.capabilities,
                    "content_type": request.content_type,
                    "format": request.content_format
                },
                recommendations=recommendations,
                next_steps=next_steps,
                confidence_score=confidence_score
            )

            # Log to Firestore
            await self._log_to_firestore(request, response, start_time)

            return response

        except Exception as e:
            logger.error(f"[ContentAgent] Error: {e}")
            fallback = await self._generate_fallback_response(request, str(e))
            await self._log_to_firestore(request, fallback, start_time, error=str(e))
            return fallback

    async def _analyze_content_context(self, request: ContentRequest) -> Dict[str, Any]:
        context = {
            "content_analysis": {},
            "pedagogical_factors": {},
            "engagement_patterns": {},
        }

        # Analyze pedagogical requirements
        context["pedagogical_factors"] = {
            "grade_level": request.grade_level,
            "difficulty": request.difficulty_level,
            "format": request.content_format,
            "duration": request.duration
        }

        # Use ADK for enhanced reasoning
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_analysis = await self.reasoning_engine.predict(
                    input_data={
                        "task": "analyze_content_context",
                        "topic": request.topic,
                        "content_type": request.content_type,
                        "grade_level": request.grade_level,
                        "student_data": request.student_data,
                        "preferences": request.preferences
                    }
                )
                context["adk_enhanced"] = adk_analysis
            except Exception as e:
                logger.warning(f"[ADK Content Reasoning] Context analysis failed: {e}")
                context["adk_enhanced"] = {"status": "failed", "fallback": True}

        return context

    async def _enhance_with_adk(self, content: Dict[str, Any], context: Dict[str, Any], request: ContentRequest) -> Dict[str, Any]:
        """Use ADK to enhance content quality and engagement"""
        if not self.reasoning_engine:
            content["adk_enhancement"] = {"status": "adk_unavailable", "fallback": True}
            return content
            
        try:
            enhancement = await self.reasoning_engine.predict(
                input_data={
                    "task": "enhance_content",
                    "content": content,
                    "context": context,
                    "content_type": request.content_type,
                    "grade_level": request.grade_level
                }
            )
            content["adk_enhancement"] = enhancement
            
            # Add multimedia suggestions if applicable
            if request.content_format in ["multimedia", "interactive"]:
                multimedia = await self._generate_multimedia_suggestions(content, request)
                content["multimedia_elements"] = multimedia
                
        except Exception as e:
            logger.warning(f"[ADK Content Enhancement] Failed: {e}")
            content["adk_enhancement"] = {"status": "failed", "fallback": True}
        
        return content

    async def _generate_multimedia_suggestions(self, content: Dict[str, Any], request: ContentRequest) -> List[Dict[str, Any]]:
        """Generate multimedia content suggestions"""
        suggestions = [
            {"type": "image", "description": f"Visual diagram for {request.topic}"},
            {"type": "video", "description": "Introduction video", "duration": "3-5 minutes"},
            {"type": "interactive", "description": "Practice exercise"}
        ]
        
        if self.reasoning_engine:
            try:
                adk_suggestions = await self.reasoning_engine.predict(
                    input_data={
                        "task": "suggest_multimedia",
                        "topic": request.topic,
                        "content_type": request.content_type,
                        "grade_level": request.grade_level
                    }
                )
                if isinstance(adk_suggestions, list):
                    suggestions.extend(adk_suggestions)
            except Exception as e:
                logger.warning(f"[ADK Multimedia Suggestions] Failed: {e}")
        
        return suggestions

    async def _generate_recommendations(self, request: ContentRequest, context: Dict[str, Any], content: Dict[str, Any]) -> List[str]:
        base_recommendations = [
            "Review content for age-appropriateness",
            "Add interactive elements to increase engagement"
        ]
        
        # Content-specific recommendations
        if request.content_type == "quiz":
            base_recommendations.append("Include varied question types for comprehensive assessment")
        elif request.content_type == "presentation":
            base_recommendations.append("Use visual aids and minimal text per slide")
        elif request.content_type == "worksheet":
            base_recommendations.append("Provide clear instructions and examples")
        
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_recs = await self.reasoning_engine.predict(
                    input_data={"task": "generate_content_recommendations", "context": context, "content": content}
                )
                if isinstance(adk_recs, list):
                    base_recommendations.extend(adk_recs)
                else:
                    logger.warning("[ADK Content Recommendations] Invalid response format")
            except Exception as e:
                logger.warning(f"[ADK Content Recommendations] Failed: {e}")
        
        return base_recommendations[:5]  # Limit to top 5

    def _calculate_confidence(self, content: Dict[str, Any], context: Dict[str, Any]) -> float:
        base_score = 0.75
        if self.adk_enabled:
            base_score += 0.15
        if content.get("learning_objectives"):
            base_score += 0.1
        return round(min(base_score, 1.0), 2)

    def _generate_next_steps(self, content: Dict[str, Any], request: ContentRequest) -> List[str]:
        next_steps = [
            f"Review and customize the {request.content_type}",
            "Test content with sample audience"
        ]
        
        if request.content_format == "multimedia":
            next_steps.append("Gather multimedia resources")
        if request.content_type == "quiz":
            next_steps.append("Set up assessment rubrics")
        
        return next_steps

    async def _log_to_firestore(self, request: ContentRequest, response: ContentResponse, start_time: datetime, error: Optional[str] = None):
        """Log agent analytics to Firestore asynchronously"""
        if not self.firestore_client:
            logger.warning("[Firestore] Client not available for logging")
            return
            
        try:
            doc = {
                "agent": "content",
                "timestamp": datetime.utcnow().isoformat(),
                "teacher_id": request.teacher_id,
                "class_id": request.class_id,
                "content_type": request.content_type,
                "topic": request.topic,
                "grade_level": request.grade_level,
                "content_format": request.content_format,
                "request": request.dict(),
                "response": response.dict(),
                "processing_time_sec": (datetime.now() - start_time).total_seconds(),
                "confidence_score": response.confidence_score,
                "adk_enabled": self.adk_enabled,
                "status": "error" if error else "success",
                "error": error
            }
            # Add document to Firestore
            doc_ref = self.firestore_client.collection("agent_logs").document()
            doc_ref.set(doc)
            logger.debug(f"[Firestore] Content analytics logged for {request.topic}")
        except Exception as e:
            logger.warning(f"[Firestore Log Error]: {str(e)}")

    async def _generate_fallback_response(self, request: ContentRequest, error: str) -> ContentResponse:
        basic_content = {
            "title": f"Basic {request.content_type} for {request.topic}",
            "type": request.content_type,
            "content": f"Introduction to {request.topic}",
            "duration": request.duration,
            "status": "fallback_generated"
        }
        return ContentResponse(
            content=basic_content,
            metadata={"fallback_mode": True, "error": error},
            recommendations=["Review and enhance manually"],
            next_steps=["Add detailed content", "Include multimedia elements"],
            confidence_score=0.4
        )

# =============================
# ADK App Entry Point
# =============================

# Global instance (must be created before ADK handler)
content_agent = ContentAgent()

# ADK App initialization
try:
    content_app = AdkApp()
except Exception as e:
    logger.warning(f"[ADK] AdkApp initialization failed: {e}")
    content_app = None

@content_app.handle_message()
async def content_handler(message):
    """ADK-compliant message handler for content agent"""
    try:
        logger.info(f"[ADK Content Handler] Processing message: {message.data.get('topic', 'unknown')}")
        request = ContentRequest(**message.data)
        response = await content_agent.handle_content_request(request)
        return response.dict()
    except Exception as e:
        logger.error(f"[ADK Content Handler Error]: {str(e)}")
        return {"error": str(e), "status": "adk_handler_error"}

# Backward compatibility function
async def handle_content(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backward compatible function for handling content requests
    """
    try:
        request = ContentRequest(**request_data)
        response = await content_agent.handle_content_request(request)
        return response.dict()
    except Exception as e:
        logger.error(f"Error in handle_content: {str(e)}")
        return {
            "error": str(e),
            "content": {},
            "status": "error"
        }
