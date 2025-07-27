"""
Advanced Orchestrator Agent - Enhanced with Google ADK
AI-powered orchestration of multiple educational agents with Vertex AI & Firestore Analytics
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
from orchestrator.lesson_pipeline import LessonPipeline
from config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =============================
# Pydantic Models
# =============================
class OrchestrationRequest(BaseModel):
    topic: str
    workflow_type: str = "complete"  # complete, planning_only, content_only, assessment_only, visual_only
    grade_level: str = "elementary"
    duration: int = 60  # minutes
    curriculum_standards: Optional[List[str]] = None
    learning_objectives: Optional[List[str]] = None
    student_data: Optional[Dict[str, Any]] = None
    include_visual_aids: bool = True
    assessment_required: bool = True
    content_format: str = "text"  # text, slides, interactive, multimedia
    difficulty_level: str = "medium"  # easy, medium, hard
    question_types: Optional[List[str]] = Field(default=["multiple_choice", "short_answer"])
    visual_type: str = "infographic"  # infographic, diagram, chart, presentation
    preferences: Optional[Dict[str, Any]] = None

class OrchestrationResponse(BaseModel):
    orchestration_result: Dict[str, Any]
    workflow_metadata: Dict[str, Any]
    agent_results: Dict[str, Any]
    recommendations: List[str]
    next_steps: List[str]
    confidence_score: float

# =============================
# Orchestrator Agent
# =============================
class OrchestratorAgent:
    def __init__(self):
        self.name = "advanced_orchestrator_agent"
        self.version = "3.0.0"
        self.capabilities = [
            "multi_agent_orchestration", "workflow_management",
            "dynamic_pipeline_execution", "agent_coordination",
            "result_aggregation", "error_handling",
            "adaptive_workflows", "parallel_processing",
            "dependency_resolution", "quality_assurance"
        ]
        self.adk_enabled = False
        self.firestore_client = None
        self.reasoning_engine = None
        self.lesson_pipeline = None
        self._initialize_adk()

    def _initialize_adk(self):
        """Initialize ADK + Firestore"""
        try:
            # Init Vertex AI
            aiplatform.init(project=Config.PROJECT_ID, location=Config.LOCATION)

            # Firestore
            self.firestore_client = firestore.Client(project=Config.PROJECT_ID)

            # Initialize lesson pipeline
            self.lesson_pipeline = LessonPipeline()

            # Create ADK Reasoning Engine (with proper error handling)
            try:
                self.reasoning_engine = ReasoningEngine(
                    display_name="orchestrator-reasoning-engine",
                    description="Handles reasoning for multi-agent orchestration",
                    spec={
                        "class_path": "orchestrator_reasoning_engine",
                        "requirements": ["google-cloud-aiplatform", "vertexai"]
                    }
                )
                logger.info("[ADK] Orchestrator Reasoning Engine created successfully.")
            except Exception as re_error:
                logger.warning(f"[ADK] Orchestrator Reasoning Engine creation failed: {re_error}")
                self.reasoning_engine = None

            self.adk_enabled = True
            logger.info("[ADK] Orchestrator Agent initialized successfully.")
        except Exception as e:
            logger.error(f"[ADK Init Error]: {str(e)}")
            self.adk_enabled = False
            self.firestore_client = None
            self.reasoning_engine = None

    async def handle_orchestration_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        start_time = datetime.now()
        try:
            # Analyze orchestration context
            context = await self._analyze_orchestration_context(request)

            # Determine optimal workflow
            workflow_plan = await self._plan_workflow(request, context)

            # Execute orchestration
            orchestration_result = await self._execute_orchestration(request, workflow_plan, context)

            # Enhance with ADK
            if self.adk_enabled:
                orchestration_result = await self._enhance_with_adk(orchestration_result, context, request)

            # Generate recommendations & next steps
            recommendations = await self._generate_recommendations(request, context, orchestration_result)
            confidence_score = self._calculate_confidence(orchestration_result, context)
            next_steps = self._generate_next_steps(orchestration_result, request)

            # Prepare response
            response = OrchestrationResponse(
                orchestration_result=orchestration_result,
                workflow_metadata={
                    "generated_at": datetime.now().isoformat(),
                    "adk_enabled": self.adk_enabled,
                    "reasoning_engine_available": self.reasoning_engine is not None,
                    "agent_version": self.version,
                    "processing_time_sec": (datetime.now() - start_time).total_seconds(),
                    "capabilities": self.capabilities,
                    "workflow_type": request.workflow_type,
                    "pipeline_version": getattr(self.lesson_pipeline, 'version', '2.0.0')
                },
                agent_results=orchestration_result.get("agent_results", {}),
                recommendations=recommendations,
                next_steps=next_steps,
                confidence_score=confidence_score
            )

            # Log to Firestore
            await self._log_to_firestore(request, response, start_time)

            return response

        except Exception as e:
            logger.error(f"[OrchestratorAgent] Error: {e}")
            fallback = await self._generate_fallback_response(request, str(e))
            await self._log_to_firestore(request, fallback, start_time, error=str(e))
            return fallback

    async def _analyze_orchestration_context(self, request: OrchestrationRequest) -> Dict[str, Any]:
        context = {
            "workflow_analysis": {},
            "agent_requirements": {},
            "optimization_factors": {},
        }

        # Analyze workflow requirements
        context["workflow_analysis"] = {
            "type": request.workflow_type,
            "complexity": self._assess_complexity(request),
            "estimated_duration": self._estimate_duration(request),
            "required_agents": self._determine_required_agents(request)
        }

        # Agent requirements analysis
        context["agent_requirements"] = {
            "planner": request.workflow_type in ["complete", "planning_only"],
            "content": request.workflow_type in ["complete", "content_only"],
            "assessment": request.assessment_required and request.workflow_type in ["complete", "assessment_only"],
            "visual_aid": request.include_visual_aids and request.workflow_type in ["complete", "visual_only"]
        }

        # Use ADK for enhanced reasoning
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_analysis = await self.reasoning_engine.predict(
                    input_data={
                        "task": "analyze_orchestration_context",
                        "topic": request.topic,
                        "workflow_type": request.workflow_type,
                        "grade_level": request.grade_level,
                        "learning_objectives": request.learning_objectives,
                        "student_data": request.student_data
                    }
                )
                context["adk_enhanced"] = adk_analysis
            except Exception as e:
                logger.warning(f"[ADK Orchestration Reasoning] Context analysis failed: {e}")
                context["adk_enhanced"] = {"status": "failed", "fallback": True}

        return context

    def _assess_complexity(self, request: OrchestrationRequest) -> str:
        """Assess workflow complexity"""
        complexity_score = 0
        
        if request.workflow_type == "complete":
            complexity_score += 3
        elif request.workflow_type in ["content_only", "assessment_only"]:
            complexity_score += 2
        else:
            complexity_score += 1
            
        if request.learning_objectives and len(request.learning_objectives) > 3:
            complexity_score += 1
            
        if request.student_data and len(request.student_data) > 0:
            complexity_score += 1
            
        if complexity_score <= 2:
            return "simple"
        elif complexity_score <= 4:
            return "moderate"
        else:
            return "complex"

    def _estimate_duration(self, request: OrchestrationRequest) -> int:
        """Estimate processing duration in seconds"""
        base_time = 30  # Base processing time
        
        if request.workflow_type == "complete":
            base_time += 60  # Additional time for full workflow
        elif request.workflow_type in ["content_only", "assessment_only"]:
            base_time += 30
            
        if request.include_visual_aids:
            base_time += 20
            
        if request.assessment_required:
            base_time += 15
            
        return base_time

    def _determine_required_agents(self, request: OrchestrationRequest) -> List[str]:
        """Determine which agents are required for the workflow"""
        agents = []
        
        if request.workflow_type in ["complete", "planning_only"]:
            agents.append("planner")
            
        if request.workflow_type in ["complete", "content_only"]:
            agents.append("content")
            
        if request.assessment_required and request.workflow_type in ["complete", "assessment_only"]:
            agents.append("assessment")
            
        if request.include_visual_aids and request.workflow_type in ["complete", "visual_only"]:
            agents.append("visual_aid")
            
        return agents

    async def _plan_workflow(self, request: OrchestrationRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan the optimal workflow execution strategy"""
        workflow_plan = {
            "execution_strategy": "sequential",  # sequential or parallel
            "agent_sequence": [],
            "dependencies": {},
            "optimization_flags": {}
        }
        
        required_agents = context["agent_requirements"]
        
        # Determine execution sequence
        if required_agents.get("planner"):
            workflow_plan["agent_sequence"].append("planner")
            
        if required_agents.get("content"):
            workflow_plan["agent_sequence"].append("content")
            if "planner" in workflow_plan["agent_sequence"]:
                workflow_plan["dependencies"]["content"] = ["planner"]
                
        # Visual aids and assessment can run in parallel after content
        parallel_agents = []
        if required_agents.get("visual_aid"):
            parallel_agents.append("visual_aid")
            workflow_plan["dependencies"]["visual_aid"] = ["content"] if "content" in workflow_plan["agent_sequence"] else []
            
        if required_agents.get("assessment"):
            parallel_agents.append("assessment")
            workflow_plan["dependencies"]["assessment"] = ["content"] if "content" in workflow_plan["agent_sequence"] else []
            
        workflow_plan["agent_sequence"].extend(parallel_agents)
        
        # Set optimization flags
        complexity = context["workflow_analysis"]["complexity"]
        if complexity == "simple":
            workflow_plan["optimization_flags"]["fast_mode"] = True
        elif complexity == "complex":
            workflow_plan["optimization_flags"]["quality_mode"] = True
            
        return workflow_plan

    async def _execute_orchestration(self, request: OrchestrationRequest, workflow_plan: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the orchestration workflow"""
        try:
            # Convert to lesson pipeline request format
            pipeline_request = self._convert_to_pipeline_request(request)
            
            # Execute using the lesson pipeline
            pipeline_response = await self.lesson_pipeline.execute_pipeline(pipeline_request)
            
            # Convert back to orchestrator format
            orchestration_result = {
                "lesson_plan": pipeline_response.lesson_plan,
                "content": pipeline_response.content,
                "assessment": pipeline_response.assessment,
                "visual_aids": pipeline_response.visual_aids,
                "execution_summary": pipeline_response.execution_summary,
                "pipeline_metadata": pipeline_response.pipeline_metadata,
                "agent_results": {
                    "planner": {"lesson_plan": pipeline_response.lesson_plan} if pipeline_response.lesson_plan else None,
                    "content": {"content": pipeline_response.content} if pipeline_response.content else None,
                    "assessment": {"assessment": pipeline_response.assessment} if pipeline_response.assessment else None,
                    "visual_aid": {"visual_aids": pipeline_response.visual_aids} if pipeline_response.visual_aids else None
                },
                "workflow_plan": workflow_plan,
                "orchestration_metadata": {
                    "workflow_type": request.workflow_type,
                    "agents_used": workflow_plan["agent_sequence"],
                    "execution_strategy": workflow_plan["execution_strategy"]
                }
            }
            
            return orchestration_result
            
        except Exception as e:
            logger.error(f"[Orchestration Execution] Error: {e}")
            return {
                "error": str(e),
                "status": "execution_failed",
                "workflow_plan": workflow_plan,
                "fallback_mode": True
            }

    def _convert_to_pipeline_request(self, request: OrchestrationRequest):
        """Convert orchestration request to lesson pipeline request"""
        # Import here to avoid circular imports
        from orchestrator.lesson_pipeline import LessonPipelineRequest
        
        return LessonPipelineRequest(
            teacher_id="orchestrator_agent",  # Required by pipeline but not used
            class_id="orchestrator_class",   # Required by pipeline but not used
            topic=request.topic,
            grade_level=request.grade_level,
            duration=request.duration,
            lesson_type=request.workflow_type,
            curriculum_standards=request.curriculum_standards,
            learning_objectives=request.learning_objectives,
            student_data=request.student_data,
            include_visual_aids=request.include_visual_aids,
            assessment_required=request.assessment_required,
            preferences=request.preferences
        )

    async def _enhance_with_adk(self, orchestration_result: Dict[str, Any], context: Dict[str, Any], request: OrchestrationRequest) -> Dict[str, Any]:
        """Use ADK to enhance orchestration results"""
        if not self.reasoning_engine:
            orchestration_result["adk_enhancement"] = {"status": "adk_unavailable", "fallback": True}
            return orchestration_result
            
        try:
            enhancement = await self.reasoning_engine.predict(
                input_data={
                    "task": "enhance_orchestration_result",
                    "result": orchestration_result,
                    "context": context,
                    "workflow_type": request.workflow_type,
                    "topic": request.topic
                }
            )
            orchestration_result["adk_enhancement"] = enhancement
            
            # Add quality assessment
            quality_score = await self._assess_result_quality(orchestration_result, request)
            orchestration_result["quality_assessment"] = quality_score
            
        except Exception as e:
            logger.warning(f"[ADK Orchestration Enhancement] Failed: {e}")
            orchestration_result["adk_enhancement"] = {"status": "failed", "fallback": True}
        
        return orchestration_result

    async def _assess_result_quality(self, orchestration_result: Dict[str, Any], request: OrchestrationRequest) -> Dict[str, Any]:
        """Assess the quality of orchestration results"""
        quality_metrics = {
            "completeness": 0.0,
            "coherence": 0.0,
            "alignment": 0.0,
            "overall": 0.0
        }
        
        # Check completeness
        expected_components = []
        if request.workflow_type in ["complete", "planning_only"]:
            expected_components.append("lesson_plan")
        if request.workflow_type in ["complete", "content_only"]:
            expected_components.append("content")
        if request.assessment_required:
            expected_components.append("assessment")
        if request.include_visual_aids:
            expected_components.append("visual_aids")
            
        completed_components = sum(1 for comp in expected_components if orchestration_result.get(comp))
        quality_metrics["completeness"] = completed_components / len(expected_components) if expected_components else 1.0
        
        # Basic coherence and alignment scores (could be enhanced with ML models)
        quality_metrics["coherence"] = 0.8  # Placeholder
        quality_metrics["alignment"] = 0.85  # Placeholder
        
        quality_metrics["overall"] = (
            quality_metrics["completeness"] * 0.4 +
            quality_metrics["coherence"] * 0.3 +
            quality_metrics["alignment"] * 0.3
        )
        
        return quality_metrics

    async def _generate_recommendations(self, request: OrchestrationRequest, context: Dict[str, Any], orchestration_result: Dict[str, Any]) -> List[str]:
        base_recommendations = [
            "Review generated content for curriculum alignment",
            "Test workflow with target audience"
        ]
        
        # Workflow-specific recommendations
        if request.workflow_type == "complete":
            base_recommendations.append("Ensure all components work together cohesively")
        elif request.workflow_type == "content_only":
            base_recommendations.append("Consider adding visual aids for better engagement")
        elif not request.assessment_required:
            base_recommendations.append("Add assessment components to measure learning outcomes")
        
        if self.adk_enabled and self.reasoning_engine:
            try:
                adk_recs = await self.reasoning_engine.predict(
                    input_data={"task": "generate_orchestration_recommendations", "context": context, "result": orchestration_result}
                )
                if isinstance(adk_recs, list):
                    base_recommendations.extend(adk_recs)
                else:
                    logger.warning("[ADK Orchestration Recommendations] Invalid response format")
            except Exception as e:
                logger.warning(f"[ADK Orchestration Recommendations] Failed: {e}")
        
        return base_recommendations[:5]  # Limit to top 5

    def _calculate_confidence(self, orchestration_result: Dict[str, Any], context: Dict[str, Any]) -> float:
        base_score = 0.7
        if self.adk_enabled:
            base_score += 0.15
        if orchestration_result.get("quality_assessment", {}).get("overall", 0) > 0.8:
            base_score += 0.1
        if not orchestration_result.get("error"):
            base_score += 0.05
        return round(min(base_score, 1.0), 2)

    def _generate_next_steps(self, orchestration_result: Dict[str, Any], request: OrchestrationRequest) -> List[str]:
        next_steps = []
        
        if orchestration_result.get("lesson_plan"):
            next_steps.append("Review and customize lesson plan")
        if orchestration_result.get("content"):
            next_steps.append("Prepare content materials for delivery")
        if orchestration_result.get("assessment"):
            next_steps.append("Set up assessment environment")
        if orchestration_result.get("visual_aids"):
            next_steps.append("Integrate visual aids into lesson")
            
        next_steps.append("Test complete workflow before implementation")
        
        return next_steps

    async def _log_to_firestore(self, request: OrchestrationRequest, response: OrchestrationResponse, start_time: datetime, error: Optional[str] = None):
        """Log agent analytics to Firestore asynchronously"""
        if not self.firestore_client:
            logger.warning("[Firestore] Client not available for logging")
            return
            
        try:
            doc = {
                "agent": "orchestrator",
                "timestamp": datetime.utcnow().isoformat(),
                "topic": request.topic,
                "workflow_type": request.workflow_type,
                "grade_level": request.grade_level,
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
            logger.debug(f"[Firestore] Orchestrator analytics logged for {request.topic}")
        except Exception as e:
            logger.warning(f"[Firestore Log Error]: {str(e)}")

    async def _generate_fallback_response(self, request: OrchestrationRequest, error: str) -> OrchestrationResponse:
        basic_result = {
            "lesson_plan": {
                "title": f"Basic Lesson: {request.topic}",
                "topic": request.topic,
                "grade_level": request.grade_level,
                "status": "fallback_generated"
            },
            "content": {
                "topic": request.topic,
                "materials": ["Basic materials"],
                "status": "fallback_generated"
            },
            "status": "fallback_mode",
            "error": error
        }
        
        return OrchestrationResponse(
            orchestration_result=basic_result,
            workflow_metadata={"fallback_mode": True, "error": error},
            agent_results={},
            recommendations=["Review and enhance manually"],
            next_steps=["Add missing components", "Test thoroughly"],
            confidence_score=0.3
        )

# =============================
# ADK App Entry Point
# =============================

# Global instance (must be created before ADK handler)
orchestrator_agent = OrchestratorAgent()

# ADK App initialization
try:
    orchestrator_app = AdkApp()
except Exception as e:
    logger.warning(f"[ADK] AdkApp initialization failed: {e}")
    orchestrator_app = None

if orchestrator_app:
    @orchestrator_app.handle_message()
    async def orchestrator_handler(message):
        """ADK-compliant message handler for orchestrator agent"""
        try:
            logger.info(f"[ADK Orchestrator Handler] Processing message: {message.data.get('topic', 'unknown')}")
            request = OrchestrationRequest(**message.data)
            response = await orchestrator_agent.handle_orchestration_request(request)
            return response.dict()
        except Exception as e:
            logger.error(f"[ADK Orchestrator Handler Error]: {str(e)}")
            return {"error": str(e), "status": "adk_handler_error"}

# Backward compatibility function
async def handle_orchestration(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Backward compatible function for handling orchestration requests
    """
    try:
        request = OrchestrationRequest(**request_data)
        response = await orchestrator_agent.handle_orchestration_request(request)
        return response.dict()
    except Exception as e:
        logger.error(f"Error in handle_orchestration: {str(e)}")
        return {
            "error": str(e),
            "orchestration_result": {},
            "status": "error"
        }
