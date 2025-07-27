"""
Advanced Assessment Agent - Enhanced with Google ADK
AI-powered educational assessment generation with Vertex AI & Firestore Analytics
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
from services.assessment_agent import (
    generate_assessment,
    analyze_assessment_results,
    generate_rubric
)
from config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =============================
# Pydantic Models
# =============================
class AssessmentRequest(BaseModel):
    teacher_id: str
    class_id: str
    assessment_type: str = "quiz"  # quiz, test, assignment, project, rubric
    topic: str
    grade_level: str = "elementary"
    duration: int = 30  # minutes
    question_count: int = 10
    difficulty_level: str = "medium"  # easy, medium, hard
    question_types: List[str] = Field(default=["multiple_choice", "short_answer"])
    learning_objectives: Optional[List[str]] = None
    curriculum_standards: Optional[List[str]] = None
    student_data: Optional[Dict[str, Any]] = None
    adaptive: bool = False  # Whether to create adaptive assessment
    preferences: Optional[Dict[str, Any]] = None

class AssessmentResponse(BaseModel):
    assessment: Dict[str, Any]
    rubric: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]
    recommendations: List[str]
    next_steps: List[str]
    confidence_score: float

# =============================
# Assessment Agent
# =============================
class AssessmentAgent:
    def __init__(self):
        self.name = "advanced_assessment_agent"
        self.version = "3.0.0"
        self.capabilities = [
            "assessment_generation", "rubric_creation",
            "adaptive_testing", "performance_analysis",
            "question_bank_management", "auto_grading",
            "visual_aid_integration", "lesson_plan_alignment",
            "real_time_feedback", "multimedia_assessment"
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
                    display_name="assessment-reasoning-engine",
                    description="Handles reasoning for educational assessment generation",
                    spec={
                        "class_path": "assessment_reasoning_engine",
                        "requirements": ["google-cloud-aiplatform", "vertexai"]
                    }
                )
                logger.info("[ADK] Assessment Reasoning Engine created successfully.")
            except Exception as re_error:
                logger.warning(f"[ADK] Assessment Reasoning Engine creation failed: {re_error}")
                self.reasoning_engine = None

            self.adk_enabled = True
            logger.info("[ADK] Assessment Agent initialized successfully.")
        except Exception as e:
            logger.error(f"[ADK Init Error]: {str(e)}")
            self.adk_enabled = False
            self.firestore_client = None
            self.reasoning_engine = None

    async def handle_assessment_request(self, request: AssessmentRequest) -> AssessmentResponse:
        start_time = datetime.now()
        try:
            # Analyze assessment context
            context = await self._analyze_assessment_context(request)

            # Generate assessment
            assessment = await generate_assessment(
                topic=request.topic,
                assessment_type=request.assessment_type,
                grade_level=request.grade_level,
                question_count=request.question_count,
                difficulty_level=request.difficulty_level,
                question_types=request.question_types,
                learning_objectives=request.learning_objectives,
                curriculum_standards=request.curriculum_standards,
                duration=request.duration
            )

            # Generate rubric if needed
            rubric = None
            if request.assessment_type in ["assignment", "project", "essay"]:
                rubric = await generate_rubric(
                    assessment=assessment,
                    learning_objectives=request.learning_objectives
                )

            # Enhance with ADK
            if self.adk_enabled:
                assessment = await self._enhance_with_adk(assessment, context, request)
                if rubric:
                    rubric = await self._enhance_rubric_with_adk(rubric, context, request)

            # Generate recommendations & next steps
            recommendations = await self._generate_recommendations(request, context, assessment)
            confidence_score = self._calculate_confidence(assessment, context)
            next_steps = self._generate_next_steps(assessment, request)

            # Prepare response
            response = AssessmentResponse(
                assessment=assessment,
                rubric=rubric,
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "adk_enabled": self.adk_enabled,
                    "reasoning_engine_available": self.reasoning_engine is not None,
                    "agent_version": self.version,
                    "processing_time_sec": (datetime.now() - start_time).total_seconds(),
                    "capabilities": self.capabilities,
                    "assessment_type": request.assessment_type,
                    "question_count": len(assessment.get("questions", []))
                },
                recommendations=recommendations,
                next_steps=next_steps,
                confidence_score=confidence_score
            )

            # Log to Firestore
            await self._log_to_firestore(request, response, start_time)

            return response

        except Exception as e:
            logger.error(f"[AssessmentAgent] Error: {e}")
            fallback = await self._generate_fallback_response(request, str(e))
            await self._log_to_firestore(request, fallback, start_time, error=str(e))
            return fallback

    async def _analyze_assessment_context(self, request: AssessmentRequest) -> Dict[str, Any]:
        context = {
            "assessment_analysis": {},
            "cognitive_load": {},
            "alignment_factors": {},
        }

        # Analyze assessment requirements
        context["assessment_analysis"] = {
            "type": request.assessment_type,
            "difficulty": request.difficulty_level,
            "question_types": request.question_types,
            "duration": request.duration,
            "adaptive": request.adaptive
        }

        # Use ADK for enhanced reasoning
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_analysis = await self.reasoning_engine.predict(
                    input_data={
                        "task": "analyze_assessment_context",
                        "topic": request.topic,
                        "assessment_type": request.assessment_type,
                        "grade_level": request.grade_level,
                        "student_data": request.student_data,
                        "learning_objectives": request.learning_objectives
                    }
                )
                context["adk_enhanced"] = adk_analysis
            except Exception as e:
                logger.warning(f"[ADK Assessment Reasoning] Context analysis failed: {e}")
                context["adk_enhanced"] = {"status": "failed", "fallback": True}

        return context

    async def _enhance_with_adk(self, assessment: Dict[str, Any], context: Dict[str, Any], request: AssessmentRequest) -> Dict[str, Any]:
        """Use ADK to enhance assessment quality and validity"""
        if not self.reasoning_engine:
            assessment["adk_enhancement"] = {"status": "adk_unavailable", "fallback": True}
            return assessment
            
        try:
            enhancement = await self.reasoning_engine.predict(
                input_data={
                    "task": "enhance_assessment",
                    "assessment": assessment,
                    "context": context,
                    "assessment_type": request.assessment_type,
                    "grade_level": request.grade_level,
                    "adaptive": request.adaptive
                }
            )
            assessment["adk_enhancement"] = enhancement
            
            # Add adaptive features if requested
            if request.adaptive:
                adaptive_features = await self._generate_adaptive_features(assessment, request)
                assessment["adaptive_features"] = adaptive_features
                
        except Exception as e:
            logger.warning(f"[ADK Assessment Enhancement] Failed: {e}")
            assessment["adk_enhancement"] = {"status": "failed", "fallback": True}
        
        return assessment

    async def _enhance_rubric_with_adk(self, rubric: Dict[str, Any], context: Dict[str, Any], request: AssessmentRequest) -> Dict[str, Any]:
        """Use ADK to enhance rubric quality"""
        if not self.reasoning_engine:
            return rubric
            
        try:
            enhancement = await self.reasoning_engine.predict(
                input_data={
                    "task": "enhance_rubric",
                    "rubric": rubric,
                    "context": context,
                    "grade_level": request.grade_level
                }
            )
            rubric["adk_enhancement"] = enhancement
        except Exception as e:
            logger.warning(f"[ADK Rubric Enhancement] Failed: {e}")
        
        return rubric

    async def _generate_adaptive_features(self, assessment: Dict[str, Any], request: AssessmentRequest) -> Dict[str, Any]:
        """Generate adaptive assessment features"""
        adaptive_features = {
            "branching_logic": "Adjust difficulty based on performance",
            "personalization": "Customize content based on learning style",
            "real_time_feedback": "Provide immediate feedback on answers"
        }
        
        if self.reasoning_engine:
            try:
                adk_adaptive = await self.reasoning_engine.predict(
                    input_data={
                        "task": "generate_adaptive_features",
                        "assessment": assessment,
                        "grade_level": request.grade_level,
                        "student_data": request.student_data
                    }
                )
                adaptive_features.update(adk_adaptive)
            except Exception as e:
                logger.warning(f"[ADK Adaptive Features] Failed: {e}")
        
        return adaptive_features

    async def _generate_recommendations(self, request: AssessmentRequest, context: Dict[str, Any], assessment: Dict[str, Any]) -> List[str]:
        base_recommendations = [
            "Review questions for clarity and bias",
            "Ensure alignment with learning objectives"
        ]
        
        # Assessment-specific recommendations
        if request.assessment_type == "quiz":
            base_recommendations.append("Include immediate feedback for each question")
        elif request.assessment_type == "project":
            base_recommendations.append("Provide clear milestones and deadlines")
        elif request.adaptive:
            base_recommendations.append("Test adaptive logic with sample responses")
        
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_recs = await self.reasoning_engine.predict(
                    input_data={"task": "generate_assessment_recommendations", "context": context, "assessment": assessment}
                )
                if isinstance(adk_recs, list):
                    base_recommendations.extend(adk_recs)
                else:
                    logger.warning("[ADK Assessment Recommendations] Invalid response format")
            except Exception as e:
                logger.warning(f"[ADK Assessment Recommendations] Failed: {e}")
        
        return base_recommendations[:5]  # Limit to top 5

    def _calculate_confidence(self, assessment: Dict[str, Any], context: Dict[str, Any]) -> float:
        base_score = 0.8
        if self.adk_enabled:
            base_score += 0.1
        if assessment.get("questions") and len(assessment["questions"]) >= 5:
            base_score += 0.1
        return round(min(base_score, 1.0), 2)

    def _generate_next_steps(self, assessment: Dict[str, Any], request: AssessmentRequest) -> List[str]:
        next_steps = [
            f"Review and finalize the {request.assessment_type}",
            "Set up assessment delivery platform"
        ]
        
        if request.assessment_type in ["assignment", "project"]:
            next_steps.append("Create detailed rubric for grading")
        if request.adaptive:
            next_steps.append("Configure adaptive assessment settings")
        
        next_steps.append("Pilot test with small group of students")
        
        return next_steps

    async def _log_to_firestore(self, request: AssessmentRequest, response: AssessmentResponse, start_time: datetime, error: Optional[str] = None):
        """Log agent analytics to Firestore asynchronously"""
        if not self.firestore_client:
            logger.warning("[Firestore] Client not available for logging")
            return
            
        try:
            doc = {
                "agent": "assessment",
                "timestamp": datetime.utcnow().isoformat(),
                "teacher_id": request.teacher_id,
                "class_id": request.class_id,
                "assessment_type": request.assessment_type,
                "topic": request.topic,
                "grade_level": request.grade_level,
                "question_count": request.question_count,
                "difficulty_level": request.difficulty_level,
                "adaptive": request.adaptive,
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
            logger.debug(f"[Firestore] Assessment analytics logged for {request.topic}")
        except Exception as e:
            logger.warning(f"[Firestore Log Error]: {str(e)}")

    async def _generate_fallback_response(self, request: AssessmentRequest, error: str) -> AssessmentResponse:
        basic_assessment = {
            "title": f"Basic {request.assessment_type} for {request.topic}",
            "type": request.assessment_type,
            "questions": [
                {"id": i+1, "question": f"Question {i+1} about {request.topic}", "type": "short_answer"}
                for i in range(min(request.question_count, 5))
            ],
            "duration": request.duration,
            "status": "fallback_generated"
        }
        return AssessmentResponse(
            assessment=basic_assessment,
            metadata={"fallback_mode": True, "error": error},
            recommendations=["Review and enhance questions manually"],
            next_steps=["Add detailed questions", "Create answer keys"],
            confidence_score=0.4
        )

# =============================
# ADK App Entry Point
# =============================

# Global instance (must be created before ADK handler)
assessment_agent = AssessmentAgent()

# ADK App initialization
try:
    assessment_app = AdkApp()
except Exception as e:
    logger.warning(f"[ADK] AdkApp initialization failed: {e}")
    assessment_app = None

@assessment_app.handle_message()
async def assessment_handler(message):
    """ADK-compliant message handler for assessment agent"""
    try:
        logger.info(f"[ADK Assessment Handler] Processing message: {message.data.get('topic', 'unknown')}")
        request = AssessmentRequest(**message.data)
        response = await assessment_agent.handle_assessment_request(request)
        return response.dict()
    except Exception as e:
        logger.error(f"[ADK Assessment Handler Error]: {str(e)}")
        return {"error": str(e), "status": "adk_handler_error"}

# Backward compatibility function
async def handle_assessment(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backward compatible function for handling assessment requests
    """
    try:
        request = AssessmentRequest(**request_data)
        response = await assessment_agent.handle_assessment_request(request)
        return response.dict()
    except Exception as e:
        logger.error(f"Error in handle_assessment: {str(e)}")
        return {
            "error": str(e),
            "assessment": {},
            "status": "error"
        }
