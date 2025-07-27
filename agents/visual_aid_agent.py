"""
Advanced Visual Aid Agent - Enhanced with Google ADK
AI-powered visual content generation with Vertex AI & Firestore Analytics
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
from services.voice_agent import generate_visual_content
from config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =============================
# Pydantic Models
# =============================
class VisualAidRequest(BaseModel):
    teacher_id: str
    class_id: str
    visual_type: str = "infographic"  # infographic, diagram, chart, presentation, poster, mind_map
    topic: str
    grade_level: str = "elementary"
    purpose: str = "explanation"  # explanation, comparison, process, data_visualization
    style: str = "educational"  # educational, professional, creative, minimal
    color_scheme: str = "vibrant"  # vibrant, pastel, monochrome, brand_colors
    dimensions: str = "standard"  # standard, wide, square, vertical
    text_amount: str = "moderate"  # minimal, moderate, detailed
    learning_objectives: Optional[List[str]] = None
    key_concepts: Optional[List[str]] = None
    data_points: Optional[Dict[str, Any]] = None  # For charts and graphs
    accessibility_features: bool = True
    preferences: Optional[Dict[str, Any]] = None

class VisualAidResponse(BaseModel):
    visual_content: Dict[str, Any]
    design_specifications: Dict[str, Any]
    metadata: Dict[str, Any]
    recommendations: List[str]
    next_steps: List[str]
    confidence_score: float

# =============================
# Visual Aid Agent
# =============================
class VisualAidAgent:
    def __init__(self):
        self.name = "advanced_visual_aid_agent"
        self.version = "3.0.0"
        self.capabilities = [
            "visual_content_generation", "design_optimization",
            "accessibility_compliance", "multi_format_export",
            "interactive_elements", "data_visualization",
            "real_time_rendering", "content_sync",
            "interactive_visuals", "accessibility_support",
            "multi_format_export", "context_aware_scaling",
            "dynamic_content_adaptation"
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
                    display_name="visual-aid-reasoning-engine",
                    description="Handles reasoning for educational visual content generation",
                    spec={
                        "class_path": "visual_aid_reasoning_engine",
                        "requirements": ["google-cloud-aiplatform", "vertexai"]
                    }
                )
                logger.info("[ADK] Visual Aid Reasoning Engine created successfully.")
            except Exception as re_error:
                logger.warning(f"[ADK] Visual Aid Reasoning Engine creation failed: {re_error}")
                self.reasoning_engine = None

            self.adk_enabled = True
            logger.info("[ADK] Visual Aid Agent initialized successfully.")
        except Exception as e:
            logger.error(f"[ADK Init Error]: {str(e)}")
            self.adk_enabled = False
            self.firestore_client = None
            self.reasoning_engine = None

    async def handle_visual_aid_request(self, request: VisualAidRequest) -> VisualAidResponse:
        start_time = datetime.now()
        try:
            # Analyze visual context
            context = await self._analyze_visual_context(request)

            # Generate visual content
            visual_content = await generate_visual_content(
                topic=request.topic,
                visual_type=request.visual_type,
                grade_level=request.grade_level,
                purpose=request.purpose,
                style=request.style,
                learning_objectives=request.learning_objectives,
                key_concepts=request.key_concepts,
                data_points=request.data_points
            )

            # Generate design specifications
            design_specs = await self._generate_design_specifications(request, context)

            # Enhance with ADK
            if self.adk_enabled:
                visual_content = await self._enhance_with_adk(visual_content, context, request)
                design_specs = await self._optimize_design_with_adk(design_specs, context, request)

            # Generate recommendations & next steps
            recommendations = await self._generate_recommendations(request, context, visual_content)
            confidence_score = self._calculate_confidence(visual_content, context)
            next_steps = self._generate_next_steps(visual_content, request)

            # Prepare response
            response = VisualAidResponse(
                visual_content=visual_content,
                design_specifications=design_specs,
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "adk_enabled": self.adk_enabled,
                    "reasoning_engine_available": self.reasoning_engine is not None,
                    "agent_version": self.version,
                    "processing_time_sec": (datetime.now() - start_time).total_seconds(),
                    "capabilities": self.capabilities,
                    "visual_type": request.visual_type,
                    "accessibility_compliant": request.accessibility_features
                },
                recommendations=recommendations,
                next_steps=next_steps,
                confidence_score=confidence_score
            )

            # Log to Firestore
            await self._log_to_firestore(request, response, start_time)

            return response

        except Exception as e:
            logger.error(f"[VisualAidAgent] Error: {e}")
            fallback = await self._generate_fallback_response(request, str(e))
            await self._log_to_firestore(request, fallback, start_time, error=str(e))
            return fallback

    async def _analyze_visual_context(self, request: VisualAidRequest) -> Dict[str, Any]:
        context = {
            "visual_analysis": {},
            "design_requirements": {},
            "accessibility_needs": {},
        }

        # Analyze visual requirements
        context["visual_analysis"] = {
            "type": request.visual_type,
            "purpose": request.purpose,
            "style": request.style,
            "grade_level": request.grade_level,
            "color_scheme": request.color_scheme
        }

        # Design requirements
        context["design_requirements"] = {
            "dimensions": request.dimensions,
            "text_amount": request.text_amount,
            "accessibility": request.accessibility_features,
            "key_concepts_count": len(request.key_concepts or [])
        }

        # Use ADK for enhanced reasoning
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_analysis = await self.reasoning_engine.predict(
                    input_data={
                        "task": "analyze_visual_context",
                        "topic": request.topic,
                        "visual_type": request.visual_type,
                        "grade_level": request.grade_level,
                        "purpose": request.purpose,
                        "key_concepts": request.key_concepts,
                        "learning_objectives": request.learning_objectives
                    }
                )
                context["adk_enhanced"] = adk_analysis
            except Exception as e:
                logger.warning(f"[ADK Visual Reasoning] Context analysis failed: {e}")
                context["adk_enhanced"] = {"status": "failed", "fallback": True}

        return context

    async def _generate_design_specifications(self, request: VisualAidRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed design specifications"""
        specs = {
            "layout": self._get_layout_specs(request.visual_type, request.dimensions),
            "color_palette": self._get_color_palette(request.color_scheme, request.grade_level),
            "typography": self._get_typography_specs(request.grade_level, request.text_amount),
            "imagery": self._get_imagery_specs(request.style, request.topic),
            "accessibility": self._get_accessibility_specs(request.accessibility_features)
        }
        
        return specs

    def _get_layout_specs(self, visual_type: str, dimensions: str) -> Dict[str, Any]:
        """Get layout specifications based on visual type and dimensions"""
        layout_map = {
            "infographic": {"structure": "vertical_flow", "sections": 3-5},
            "diagram": {"structure": "hierarchical", "sections": "variable"},
            "chart": {"structure": "data_focused", "sections": 2-3},
            "presentation": {"structure": "slide_based", "sections": "per_slide"},
            "poster": {"structure": "poster_layout", "sections": 4-6},
            "mind_map": {"structure": "radial", "sections": "branching"}
        }
        
        return layout_map.get(visual_type, {"structure": "flexible", "sections": 3})

    def _get_color_palette(self, color_scheme: str, grade_level: str) -> Dict[str, Any]:
        """Get color palette based on scheme and grade level"""
        palettes = {
            "vibrant": {"primary": "#FF6B6B", "secondary": "#4ECDC4", "accent": "#45B7D1"},
            "pastel": {"primary": "#FFB6C1", "secondary": "#98FB98", "accent": "#87CEEB"},
            "monochrome": {"primary": "#333333", "secondary": "#666666", "accent": "#999999"}
        }
        
        base_palette = palettes.get(color_scheme, palettes["vibrant"])
        
        # Adjust for grade level
        if grade_level in ["elementary", "primary"]:
            base_palette["brightness"] = "high"
        elif grade_level in ["high_school", "university"]:
            base_palette["brightness"] = "moderate"
            
        return base_palette

    def _get_typography_specs(self, grade_level: str, text_amount: str) -> Dict[str, Any]:
        """Get typography specifications"""
        font_sizes = {
            "elementary": {"heading": 24, "body": 16, "caption": 12},
            "middle_school": {"heading": 22, "body": 14, "caption": 11},
            "high_school": {"heading": 20, "body": 13, "caption": 10}
        }
        
        return {
            "font_family": "Sans-serif, Educational",
            "sizes": font_sizes.get(grade_level, font_sizes["elementary"]),
            "weight": "medium" if text_amount == "detailed" else "normal",
            "line_spacing": 1.4
        }

    def _get_imagery_specs(self, style: str, topic: str) -> Dict[str, Any]:
        """Get imagery specifications"""
        return {
            "style": style,
            "illustration_type": "vector" if style == "educational" else "mixed",
            "icon_style": "outline" if style == "minimal" else "filled",
            "image_ratio": "16:9",
            "topic_relevance": "high"
        }

    def _get_accessibility_specs(self, accessibility_features: bool) -> Dict[str, Any]:
        """Get accessibility specifications"""
        if not accessibility_features:
            return {"enabled": False}
            
        return {
            "enabled": True,
            "contrast_ratio": "4.5:1 minimum",
            "alt_text": "required",
            "color_blind_safe": True,
            "large_text_support": True,
            "screen_reader_compatible": True
        }

    async def _enhance_with_adk(self, visual_content: Dict[str, Any], context: Dict[str, Any], request: VisualAidRequest) -> Dict[str, Any]:
        """Use ADK to enhance visual content effectiveness"""
        if not self.reasoning_engine:
            visual_content["adk_enhancement"] = {"status": "adk_unavailable", "fallback": True}
            return visual_content
            
        try:
            enhancement = await self.reasoning_engine.predict(
                input_data={
                    "task": "enhance_visual_content",
                    "content": visual_content,
                    "context": context,
                    "visual_type": request.visual_type,
                    "grade_level": request.grade_level,
                    "purpose": request.purpose
                }
            )
            visual_content["adk_enhancement"] = enhancement
            
            # Add interactive elements if applicable
            if request.visual_type in ["presentation", "infographic"]:
                interactive_elements = await self._generate_interactive_elements(visual_content, request)
                visual_content["interactive_elements"] = interactive_elements
                
        except Exception as e:
            logger.warning(f"[ADK Visual Enhancement] Failed: {e}")
            visual_content["adk_enhancement"] = {"status": "failed", "fallback": True}
        
        return visual_content

    async def _optimize_design_with_adk(self, design_specs: Dict[str, Any], context: Dict[str, Any], request: VisualAidRequest) -> Dict[str, Any]:
        """Use ADK to optimize design specifications"""
        if not self.reasoning_engine:
            return design_specs
            
        try:
            optimization = await self.reasoning_engine.predict(
                input_data={
                    "task": "optimize_design",
                    "design_specs": design_specs,
                    "context": context,
                    "grade_level": request.grade_level,
                    "accessibility": request.accessibility_features
                }
            )
            design_specs["adk_optimization"] = optimization
        except Exception as e:
            logger.warning(f"[ADK Design Optimization] Failed: {e}")
        
        return design_specs

    async def _generate_interactive_elements(self, visual_content: Dict[str, Any], request: VisualAidRequest) -> List[Dict[str, Any]]:
        """Generate interactive elements for visual content"""
        elements = []
        
        if request.visual_type == "infographic":
            elements.extend([
                {"type": "hover_info", "description": "Additional details on hover"},
                {"type": "clickable_sections", "description": "Expandable content areas"}
            ])
        elif request.visual_type == "presentation":
            elements.extend([
                {"type": "slide_transitions", "description": "Smooth slide animations"},
                {"type": "embedded_quiz", "description": "Interactive questions"}
            ])
        elif request.visual_type == "diagram":
            elements.extend([
                {"type": "zoom_functionality", "description": "Zoom into diagram sections"},
                {"type": "step_by_step", "description": "Sequential revelation"}
            ])
        
        return elements

    async def _generate_recommendations(self, request: VisualAidRequest, context: Dict[str, Any], visual_content: Dict[str, Any]) -> List[str]:
        base_recommendations = [
            "Test visual with target audience for effectiveness",
            "Ensure all text is legible at intended viewing size"
        ]
        
        # Visual-specific recommendations
        if request.visual_type == "infographic":
            base_recommendations.append("Maintain logical flow from top to bottom")
        elif request.visual_type == "chart":
            base_recommendations.append("Include clear data labels and legends")
        elif request.accessibility_features:
            base_recommendations.append("Verify accessibility compliance with screen readers")
        
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_recs = await self.reasoning_engine.predict(
                    input_data={"task": "generate_visual_recommendations", "context": context, "visual_content": visual_content}
                )
                if isinstance(adk_recs, list):
                    base_recommendations.extend(adk_recs)
                else:
                    logger.warning("[ADK Visual Recommendations] Invalid response format")
            except Exception as e:
                logger.warning(f"[ADK Visual Recommendations] Failed: {e}")
        
        return base_recommendations[:5]  # Limit to top 5

    def _calculate_confidence(self, visual_content: Dict[str, Any], context: Dict[str, Any]) -> float:
        base_score = 0.75
        if self.adk_enabled:
            base_score += 0.15
        if visual_content.get("key_concepts") and len(visual_content["key_concepts"]) > 0:
            base_score += 0.1
        return round(min(base_score, 1.0), 2)

    def _generate_next_steps(self, visual_content: Dict[str, Any], request: VisualAidRequest) -> List[str]:
        next_steps = [
            f"Create final design for {request.visual_type}",
            "Export in multiple formats (PNG, PDF, SVG)"
        ]
        
        if request.accessibility_features:
            next_steps.append("Add alt text and accessibility metadata")
        if visual_content.get("interactive_elements"):
            next_steps.append("Implement interactive features")
        
        next_steps.append("Test visual aid with students for feedback")
        
        return next_steps

    async def _log_to_firestore(self, request: VisualAidRequest, response: VisualAidResponse, start_time: datetime, error: Optional[str] = None):
        """Log agent analytics to Firestore asynchronously"""
        if not self.firestore_client:
            logger.warning("[Firestore] Client not available for logging")
            return
            
        try:
            doc = {
                "agent": "visual_aid",
                "timestamp": datetime.utcnow().isoformat(),
                "teacher_id": request.teacher_id,
                "class_id": request.class_id,
                "visual_type": request.visual_type,
                "topic": request.topic,
                "grade_level": request.grade_level,
                "purpose": request.purpose,
                "style": request.style,
                "accessibility_enabled": request.accessibility_features,
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
            logger.debug(f"[Firestore] Visual Aid analytics logged for {request.topic}")
        except Exception as e:
            logger.warning(f"[Firestore Log Error]: {str(e)}")

    async def _generate_fallback_response(self, request: VisualAidRequest, error: str) -> VisualAidResponse:
        basic_visual = {
            "title": f"Basic {request.visual_type} for {request.topic}",
            "type": request.visual_type,
            "content": f"Visual representation of {request.topic}",
            "elements": ["title", "main_content", "summary"],
            "status": "fallback_generated"
        }
        
        basic_design = {
            "layout": "simple",
            "colors": ["#333333", "#666666"],
            "fonts": ["Arial", "sans-serif"],
            "accessibility": request.accessibility_features
        }
        
        return VisualAidResponse(
            visual_content=basic_visual,
            design_specifications=basic_design,
            metadata={"fallback_mode": True, "error": error},
            recommendations=["Review and enhance design manually"],
            next_steps=["Add visual elements", "Improve layout and design"],
            confidence_score=0.4
        )

# =============================
# ADK App Entry Point
# =============================

# Global instance (must be created before ADK handler)
visual_aid_agent = VisualAidAgent()

# ADK App initialization
try:
    visual_aid_app = AdkApp()
except Exception as e:
    logger.warning(f"[ADK] AdkApp initialization failed: {e}")
    visual_aid_app = None

@visual_aid_app.handle_message()
async def visual_aid_handler(message):
    """ADK-compliant message handler for visual aid agent"""
    try:
        logger.info(f"[ADK Visual Aid Handler] Processing message: {message.data.get('topic', 'unknown')}")
        request = VisualAidRequest(**message.data)
        response = await visual_aid_agent.handle_visual_aid_request(request)
        return response.dict()
    except Exception as e:
        logger.error(f"[ADK Visual Aid Handler Error]: {str(e)}")
        return {"error": str(e), "status": "adk_handler_error"}

# Backward compatibility function
async def handle_visual_aid(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backward compatible function for handling visual aid requests
    """
    try:
        request = VisualAidRequest(**request_data)
        response = await visual_aid_agent.handle_visual_aid_request(request)
        return response.dict()
    except Exception as e:
        logger.error(f"Error in handle_visual_aid: {str(e)}")
        return {
            "error": str(e),
            "visual_content": {},
            "status": "error"
        }
