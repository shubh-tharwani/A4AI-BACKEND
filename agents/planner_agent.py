"""
Advanced Planner Agent - Enhanced with Google ADK
AI-powered educational lesson planning with Vertex AI & Firestore Analytics
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
from services.planning_service import (
    generate_lesson_plan
)
from config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =============================
# Pydantic Models
# =============================
class PlannerRequest(BaseModel):
    teacher_id: str
    class_id: str
    plan_type: str = "weekly"
    duration: int = 7
    curriculum_standards: Optional[List[str]] = None
    learning_objectives: Optional[List[str]] = None
    student_data: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None

class PlannerResponse(BaseModel):
    lesson_plan: Dict[str, Any]
    metadata: Dict[str, Any]
    recommendations: List[str]
    next_steps: List[str]
    confidence_score: float

# =============================
# Planner Agent
# =============================
class PlannerAgent:
    def __init__(self):
        self.name = "advanced_planner_agent"
        self.version = "3.0.0"
        self.capabilities = [
            "lesson_planning", "curriculum_alignment",
            "progress_analysis", "adaptive_learning_paths",
            "visual_aid_coordination", "content_orchestration",
            "multi_agent_sync", "resource_optimization",
            "dynamic_plan_adaptation", "assessment_integration"
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
                    display_name="planner-reasoning-engine",
                    description="Handles reasoning for educational planning",
                    spec={
                        "class_path": "planner_reasoning_engine",
                        "requirements": ["google-cloud-aiplatform", "vertexai"]
                    }
                )
                logger.info("[ADK] Reasoning Engine created successfully.")
            except Exception as re_error:
                logger.warning(f"[ADK] Reasoning Engine creation failed: {re_error}")
                self.reasoning_engine = None

            self.adk_enabled = True
            logger.info("[ADK] Planner Agent initialized successfully.")
        except Exception as e:
            logger.error(f"[ADK Init Error]: {str(e)}")
            self.adk_enabled = False
            self.firestore_client = None
            self.reasoning_engine = None

    async def handle_planning_request(self, request: PlannerRequest) -> PlannerResponse:
        start_time = datetime.now()
        try:
            # Analyze context
            context = await self._analyze_planning_context(request)

            # Generate lesson plan
            lesson_plan = await generate_lesson_plan(
                class_id=request.class_id,
                plan_type=request.plan_type,
                duration=request.duration,
                user_id=request.teacher_id,
                curriculum_standards=request.curriculum_standards,
                learning_objectives=request.learning_objectives
            )

            # Personalize with ADK
            if self.adk_enabled:
                lesson_plan = await self._personalize_with_adk(lesson_plan, context)

            # Generate recommendations & next steps
            recommendations = await self._generate_recommendations(request, context, lesson_plan)
            confidence_score = self._calculate_confidence(lesson_plan, context)
            next_steps = self._generate_next_steps(lesson_plan, request)

            # Prepare response
            response = PlannerResponse(
                lesson_plan=lesson_plan,
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "adk_enabled": self.adk_enabled,
                    "reasoning_engine_available": self.reasoning_engine is not None,
                    "agent_version": self.version,
                    "processing_time_sec": (datetime.now() - start_time).total_seconds(),
                    "capabilities": self.capabilities
                },
                recommendations=recommendations,
                next_steps=next_steps,
                confidence_score=confidence_score
            )

            # Log to Firestore
            await self._log_to_firestore(request, response, start_time)

            return response

        except Exception as e:
            logger.error(f"[PlannerAgent] Error: {e}")
            fallback = await self._generate_fallback_response(request, str(e))
            await self._log_to_firestore(request, fallback, start_time, error=str(e))
            return fallback

    async def _analyze_planning_context(self, request: PlannerRequest) -> Dict[str, Any]:
        context = {
            "student_insights": {},
            "curriculum_analysis": {},
            "temporal_factors": {},
        }

        if request.student_data:
            context["student_insights"] = {
                "total_students": len(request.student_data.get("students", [])),
                "average_performance": request.student_data.get("average_performance", "unknown"),
                "learning_preferences": request.student_data.get("learning_preferences", []),
                "special_considerations": request.student_data.get("special_considerations", [])
            }

        # Use ADK for enhanced reasoning
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_analysis = await self.reasoning_engine.predict(
                    input_data={
                        "task": "analyze_context",
                        "student_data": request.student_data,
                        "preferences": request.preferences,
                        "curriculum": request.curriculum_standards
                    }
                )
                context["adk_enhanced"] = adk_analysis
            except Exception as e:
                logger.warning(f"[ADK Reasoning] Context analysis failed: {e}")
                context["adk_enhanced"] = {"status": "failed", "fallback": True}

        return context

    async def _personalize_with_adk(self, lesson_plan: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Use ADK to enhance personalization"""
        if not self.reasoning_engine:
            lesson_plan["personalization_details"] = {"status": "adk_unavailable", "fallback": True}
            return lesson_plan
            
        try:
            personalization = await self.reasoning_engine.predict(
                input_data={
                    "task": "personalize_plan",
                    "lesson_plan": lesson_plan,
                    "student_insights": context.get("student_insights")
                }
            )
            lesson_plan["personalization_details"] = personalization
        except Exception as e:
            logger.warning(f"[ADK Personalization] Failed: {e}")
            lesson_plan["personalization_details"] = {"status": "failed", "fallback": True}
        
        return lesson_plan

    async def _generate_recommendations(self, request: PlannerRequest, context: Dict[str, Any], lesson_plan: Dict[str, Any]) -> List[str]:
        base_recommendations = ["Review objectives", "Include interactive elements"]
        
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_recs = await self.reasoning_engine.predict(
                    input_data={"task": "generate_recommendations", "context": context, "lesson_plan": lesson_plan}
                )
                if isinstance(adk_recs, list):
                    base_recommendations.extend(adk_recs)
                else:
                    logger.warning("[ADK Recommendations] Invalid response format")
            except Exception as e:
                logger.warning(f"[ADK Recommendations] Failed: {e}")
        
        return base_recommendations[:5]  # Limit to top 5

    def _calculate_confidence(self, lesson_plan: Dict[str, Any], context: Dict[str, Any]) -> float:
        base_score = 0.7
        if self.adk_enabled:
            base_score += 0.2
        if context.get("student_insights"):
            base_score += 0.1
        return round(min(base_score, 1.0), 2)

    def _generate_next_steps(self, lesson_plan: Dict[str, Any], request: PlannerRequest) -> List[str]:
        return ["Customize the plan", "Prepare multimedia content", "Monitor engagement"]

    async def _log_to_firestore(self, request: PlannerRequest, response: PlannerResponse, start_time: datetime, error: Optional[str] = None):
        """Log agent analytics to Firestore asynchronously"""
        if not self.firestore_client:
            logger.warning("[Firestore] Client not available for logging")
            return
            
        try:
            doc = {
                "agent": "planner",
                "timestamp": datetime.utcnow().isoformat(),
                "teacher_id": request.teacher_id,
                "class_id": request.class_id,
                "plan_type": request.plan_type,
                "duration": request.duration,
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
            logger.debug(f"[Firestore] Analytics logged for {request.class_id}")
        except Exception as e:
            logger.warning(f"[Firestore Log Error]: {str(e)}")

    async def _generate_fallback_response(self, request: PlannerRequest, error: str) -> PlannerResponse:
        basic_plan = {"lessons": [{"day": i+1, "topic": f"Lesson {i+1}"} for i in range(min(request.duration, 5))]}
        return PlannerResponse(
            lesson_plan=basic_plan,
            metadata={"fallback_mode": True, "error": error},
            recommendations=["Review manually"],
            next_steps=["Add details"],
            confidence_score=0.4
        )

# =============================
# ADK App Entry Point
# =============================

# Global instance (must be created before ADK handler)
planner_agent = PlannerAgent()

# ADK App initialization
try:
    planner_app = AdkApp()
except Exception as e:
    logger.warning(f"[ADK] AdkApp initialization failed: {e}")
    planner_app = None

if planner_app:
    @planner_app.handle_message()
    async def planner_handler(message):
        """ADK-compliant message handler for planner agent"""
        try:
            logger.info(f"[ADK Handler] Processing message: {message.data.get('class_id', 'unknown')}")
            request = PlannerRequest(**message.data)
            response = await planner_agent.handle_planning_request(request)
            return response.dict()
        except Exception as e:
            logger.error(f"[ADK Handler Error]: {str(e)}")
            return {"error": str(e), "status": "adk_handler_error"}

# Backward compatibility function
async def handle_plan(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backward compatible function for handling planning requests
    """
    try:
        request = PlannerRequest(**request_data)
        response = await planner_agent.handle_planning_request(request)
        return response.dict()
    except Exception as e:
        logger.error(f"Error in handle_plan: {str(e)}")
        return {
            "error": str(e),
            "lesson_plan": {},
            "status": "error"
        }
