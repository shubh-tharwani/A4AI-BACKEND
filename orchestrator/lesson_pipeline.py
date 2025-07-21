"""
Advanced Lesson Pipeline - ADK Orchestration
Complete educational content pipeline using Google ADK workflow orchestration
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

# Google ADK Orchestration (using available ADK components)
from vertexai.preview.reasoning_engines import AdkApp
from google.cloud import firestore

# Agent imports
from agents.planner_agent import planner_app
from agents.content_agent import content_app
from agents.assessment_agent import assessment_app
from agents.visual_aid_agent import visual_aid_app

# Internal imports
from config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =============================
# Pipeline Models
# =============================
class LessonPipelineRequest(BaseModel):
    teacher_id: str
    class_id: str
    topic: str
    grade_level: str = "elementary"
    duration: int = 60  # minutes
    lesson_type: str = "complete"  # complete, planning_only, content_only, assessment_only
    curriculum_standards: Optional[List[str]] = None
    learning_objectives: Optional[List[str]] = None
    student_data: Optional[Dict[str, Any]] = None
    include_visual_aids: bool = True
    assessment_required: bool = True
    preferences: Optional[Dict[str, Any]] = None

class LessonPipelineResponse(BaseModel):
    lesson_plan: Dict[str, Any]
    content: Dict[str, Any]
    assessment: Optional[Dict[str, Any]] = None
    visual_aids: Optional[List[Dict[str, Any]]] = None
    pipeline_metadata: Dict[str, Any]
    execution_summary: Dict[str, Any]
    recommendations: List[str]
    next_steps: List[str]

# =============================
# Enhanced Lesson Pipeline
# =============================
class LessonPipeline:
    def __init__(self):
        self.name = "advanced_lesson_pipeline"
        self.version = "2.0.0"
        self.firestore_client = None
        self._initialize_pipeline()

    def _initialize_pipeline(self):
        """Initialize pipeline components"""
        try:
            # Initialize Firestore for pipeline logging
            self.firestore_client = firestore.Client(project=Config.PROJECT_ID)
            
            # Define pipeline steps configuration
            self.pipeline_steps = {
                "complete": [
                    {
                        "name": "planning",
                        "app": planner_app,
                        "handler": "planner_handler",
                        "required": True,
                        "description": "Generate comprehensive lesson plan"
                    },
                    {
                        "name": "content_generation", 
                        "app": content_app,
                        "handler": "content_handler",
                        "required": True,
                        "depends_on": ["planning"],
                        "description": "Create educational content based on lesson plan"
                    },
                    {
                        "name": "visual_aids",
                        "app": visual_aid_app,
                        "handler": "visual_aid_handler", 
                        "required": False,
                        "depends_on": ["planning", "content_generation"],
                        "description": "Generate visual aids and multimedia content"
                    },
                    {
                        "name": "assessment_creation",
                        "app": assessment_app,
                        "handler": "assessment_handler",
                        "required": False,
                        "depends_on": ["planning", "content_generation"],
                        "description": "Create assessments and rubrics"
                    }
                ],
                "planning_only": [
                    {
                        "name": "planning",
                        "app": planner_app,
                        "handler": "planner_handler",
                        "required": True,
                        "description": "Generate lesson plan only"
                    }
                ],
                "content_only": [
                    {
                        "name": "content_generation",
                        "app": content_app,
                        "handler": "content_handler",
                        "required": True,
                        "description": "Generate content only"
                    }
                ]
            }
            
            logger.info(f"[Pipeline] {self.name} v{self.version} initialized successfully")
            
        except Exception as e:
            logger.error(f"[Pipeline Init Error]: {str(e)}")
            self.firestore_client = None

    async def execute_pipeline(self, request: LessonPipelineRequest) -> LessonPipelineResponse:
        """Execute the lesson pipeline based on request type"""
        start_time = datetime.now()
        
        try:
            logger.info(f"[Pipeline] Starting {request.lesson_type} pipeline for topic: {request.topic}")
            
            # Prepare pipeline context
            context = await self._prepare_pipeline_context(request)
            
            # Select and execute appropriate workflow
            workflow_result = await self._execute_workflow(request, context)
            
            # Post-process results
            processed_result = await self._process_workflow_result(workflow_result, request)
            
            # Generate pipeline response
            response = await self._create_pipeline_response(processed_result, request, start_time)
            
            # Log pipeline execution
            await self._log_pipeline_execution(request, response, start_time)
            
            logger.info(f"[Pipeline] Successfully completed {request.lesson_type} pipeline")
            return response
            
        except Exception as e:
            logger.error(f"[Pipeline] Execution error: {str(e)}")
            return await self._create_error_response(request, str(e), start_time)

    async def _prepare_pipeline_context(self, request: LessonPipelineRequest) -> Dict[str, Any]:
        """Prepare context for pipeline execution"""
        context = {
            "pipeline_id": f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "teacher_id": request.teacher_id,
            "class_id": request.class_id,
            "topic": request.topic,
            "grade_level": request.grade_level,
            "duration": request.duration,
            "curriculum_standards": request.curriculum_standards,
            "learning_objectives": request.learning_objectives,
            "student_data": request.student_data,
            "preferences": request.preferences,
            "pipeline_config": {
                "include_visual_aids": request.include_visual_aids,
                "assessment_required": request.assessment_required,
                "lesson_type": request.lesson_type
            }
        }
        
        return context

    async def _execute_workflow(self, request: LessonPipelineRequest, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the appropriate workflow based on lesson type"""
        
        # Get pipeline steps for the requested lesson type
        steps = self.pipeline_steps.get(request.lesson_type, [])
        if not steps:
            raise ValueError(f"Unknown lesson type: {request.lesson_type}")
        
        # Filter steps based on request configuration
        active_steps = []
        for step in steps:
            if step["name"] == "visual_aids" and not request.include_visual_aids:
                continue
            if step["name"] == "assessment_creation" and not request.assessment_required:
                continue
            active_steps.append(step)
        
        # Execute steps in dependency order
        results = {}
        execution_order = self._resolve_step_dependencies(active_steps)
        
        for step_name in execution_order:
            step_config = next(s for s in active_steps if s["name"] == step_name)
            try:
                logger.info(f"[Pipeline] Executing step: {step_name}")
                
                # Prepare step-specific context
                step_context = await self._prepare_step_context(step_config, context, results)
                
                # Execute the step
                step_result = await self._execute_step(step_config, step_context)
                results[step_name] = step_result
                
                logger.info(f"[Pipeline] Step {step_name} completed successfully")
                
            except Exception as e:
                logger.error(f"[Pipeline] Step {step_name} failed: {str(e)}")
                if step_config["required"]:
                    raise e
                else:
                    results[step_name] = {"error": str(e), "status": "failed"}
        
        return {
            "step_results": results,
            "execution_details": {
                "steps_executed": list(results.keys()),
                "execution_order": execution_order,
                "total_steps": len(active_steps)
            }
        }

    def _resolve_step_dependencies(self, steps: List[Dict[str, Any]]) -> List[str]:
        """Resolve step execution order based on dependencies"""
        step_map = {step["name"]: step for step in steps}
        resolved = []
        remaining = list(step_map.keys())
        
        while remaining:
            # Find steps with no unresolved dependencies
            ready_steps = []
            for step_name in remaining:
                step = step_map[step_name]
                dependencies = step.get("depends_on", [])
                if all(dep in resolved for dep in dependencies):
                    ready_steps.append(step_name)
            
            if not ready_steps:
                # Circular dependency or missing dependency
                logger.warning(f"[Pipeline] Could not resolve dependencies for: {remaining}")
                ready_steps = remaining  # Execute remaining steps anyway
            
            # Add ready steps to resolved list
            for step_name in ready_steps:
                resolved.append(step_name)
                remaining.remove(step_name)
        
        return resolved

    async def _prepare_step_context(self, step_config: Dict[str, Any], base_context: Dict[str, Any], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for a specific step"""
        step_context = base_context.copy()
        
        # Add results from dependent steps
        dependencies = step_config.get("depends_on", [])
        for dep in dependencies:
            if dep in previous_results:
                step_context[f"{dep}_result"] = previous_results[dep]
        
        # Add step-specific data based on step name
        step_name = step_config["name"]
        
        if step_name == "content_generation":
            # Content generation needs lesson plan data
            if "planning" in previous_results:
                planning_result = previous_results["planning"]
                step_context.update({
                    "lesson_plan": planning_result.get("lesson_plan", {}),
                    "content_type": "lesson",
                    "topic": step_context["topic"]
                })
        
        elif step_name == "visual_aids":
            # Visual aids need lesson plan and content data
            step_context.update({
                "visual_type": "infographic",
                "purpose": "explanation",
                "topic": step_context["topic"]
            })
            
        elif step_name == "assessment_creation":
            # Assessment needs lesson plan data
            step_context.update({
                "assessment_type": "quiz",
                "topic": step_context["topic"],
                "question_count": 10
            })
        
        return step_context

    async def _execute_step(self, step_config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single pipeline step"""
        step_name = step_config["name"]
        handler_name = step_config["handler"]
        
        # Create a message object that the ADK handler expects
        class MockMessage:
            def __init__(self, data):
                self.data = data
        
        message = MockMessage(context)
        
        # Get the appropriate handler function
        if step_name == "planning":
            from agents.planner_agent import planner_handler
            result = await planner_handler(message)
            
        elif step_name == "content_generation":
            from agents.content_agent import content_handler
            result = await content_handler(message)
            
        elif step_name == "visual_aids":
            from agents.visual_aid_agent import visual_aid_handler
            result = await visual_aid_handler(message)
            
        elif step_name == "assessment_creation":
            from agents.assessment_agent import assessment_handler
            result = await assessment_handler(message)
            
        else:
            raise ValueError(f"Unknown step: {step_name}")
        
        return result

    async def _process_workflow_result(self, workflow_result: Dict[str, Any], request: LessonPipelineRequest) -> Dict[str, Any]:
        """Post-process workflow results"""
        processed = {
            "lesson_plan": {},
            "content": {},
            "assessment": None,
            "visual_aids": None,
            "execution_details": workflow_result.get("execution_details", {}),
            "step_results": workflow_result.get("step_results", {})
        }
        
        # Extract results from each step
        step_results = workflow_result.get("step_results", {})
        
        if "planning" in step_results:
            processed["lesson_plan"] = step_results["planning"].get("lesson_plan", {})
            
        if "content_generation" in step_results:
            processed["content"] = step_results["content_generation"].get("content", {})
            
        if "assessment_creation" in step_results and request.assessment_required:
            processed["assessment"] = step_results["assessment_creation"].get("assessment", {})
            
        if "visual_aids" in step_results and request.include_visual_aids:
            processed["visual_aids"] = step_results["visual_aids"].get("visual_content", [])
        
        return processed

    async def _create_pipeline_response(self, processed_result: Dict[str, Any], request: LessonPipelineRequest, start_time: datetime) -> LessonPipelineResponse:
        """Create comprehensive pipeline response"""
        
        # Generate recommendations based on pipeline results
        recommendations = await self._generate_pipeline_recommendations(processed_result, request)
        
        # Generate next steps
        next_steps = self._generate_pipeline_next_steps(processed_result, request)
        
        # Create execution summary
        execution_summary = {
            "total_processing_time": (datetime.now() - start_time).total_seconds(),
            "steps_executed": list(processed_result.get("step_results", {}).keys()),
            "success_rate": self._calculate_success_rate(processed_result),
            "components_generated": {
                "lesson_plan": bool(processed_result.get("lesson_plan")),
                "content": bool(processed_result.get("content")),
                "assessment": bool(processed_result.get("assessment")),
                "visual_aids": bool(processed_result.get("visual_aids"))
            }
        }
        
        response = LessonPipelineResponse(
            lesson_plan=processed_result.get("lesson_plan", {}),
            content=processed_result.get("content", {}),
            assessment=processed_result.get("assessment"),
            visual_aids=processed_result.get("visual_aids"),
            pipeline_metadata={
                "pipeline_version": self.version,
                "execution_time": execution_summary["total_processing_time"],
                "lesson_type": request.lesson_type,
                "topic": request.topic,
                "grade_level": request.grade_level
            },
            execution_summary=execution_summary,
            recommendations=recommendations,
            next_steps=next_steps
        )
        
        return response

    async def _generate_pipeline_recommendations(self, processed_result: Dict[str, Any], request: LessonPipelineRequest) -> List[str]:
        """Generate recommendations based on pipeline execution"""
        recommendations = []
        
        # Check lesson plan quality
        if processed_result.get("lesson_plan"):
            recommendations.append("Review lesson plan for alignment with learning objectives")
        
        # Check content completeness
        if processed_result.get("content"):
            recommendations.append("Customize content for your specific classroom needs")
        
        # Visual aids recommendations
        if request.include_visual_aids and not processed_result.get("visual_aids"):
            recommendations.append("Consider adding visual aids to enhance student engagement")
        
        # Assessment recommendations
        if request.assessment_required and not processed_result.get("assessment"):
            recommendations.append("Create assessment tools to measure student understanding")
        
        # General recommendations
        recommendations.extend([
            "Pilot test the lesson with a small group before full implementation",
            "Gather student feedback to improve future lessons"
        ])
        
        return recommendations[:5]  # Limit to top 5

    def _generate_pipeline_next_steps(self, processed_result: Dict[str, Any], request: LessonPipelineRequest) -> List[str]:
        """Generate next steps for lesson implementation"""
        next_steps = [
            "Review all generated components for accuracy and relevance",
            "Prepare required materials and resources"
        ]
        
        if processed_result.get("visual_aids"):
            next_steps.append("Set up visual aids and multimedia equipment")
        
        if processed_result.get("assessment"):
            next_steps.append("Prepare assessment materials and rubrics")
        
        next_steps.extend([
            "Schedule lesson delivery and assessment dates",
            "Monitor student engagement and understanding during delivery"
        ])
        
        return next_steps

    def _calculate_success_rate(self, processed_result: Dict[str, Any]) -> float:
        """Calculate pipeline execution success rate"""
        step_results = processed_result.get("step_results", {})
        if not step_results:
            return 0.0
        
        successful_steps = sum(1 for result in step_results.values() if not result.get("error"))
        total_steps = len(step_results)
        
        return round(successful_steps / total_steps, 2) if total_steps > 0 else 0.0

    async def _log_pipeline_execution(self, request: LessonPipelineRequest, response: LessonPipelineResponse, start_time: datetime):
        """Log pipeline execution to Firestore"""
        if not self.firestore_client:
            return
        
        try:
            log_data = {
                "pipeline": "lesson_pipeline",
                "timestamp": datetime.utcnow().isoformat(),
                "teacher_id": request.teacher_id,
                "class_id": request.class_id,
                "topic": request.topic,
                "lesson_type": request.lesson_type,
                "grade_level": request.grade_level,
                "request": request.dict(),
                "response_summary": {
                    "success_rate": response.execution_summary["success_rate"],
                    "total_time": response.execution_summary["total_processing_time"],
                    "components_generated": response.execution_summary["components_generated"]
                },
                "pipeline_version": self.version
            }
            
            doc_ref = self.firestore_client.collection("pipeline_logs").document()
            doc_ref.set(log_data)
            logger.debug(f"[Pipeline] Execution logged for {request.topic}")
            
        except Exception as e:
            logger.warning(f"[Pipeline Log Error]: {str(e)}")

    async def _create_error_response(self, request: LessonPipelineRequest, error: str, start_time: datetime) -> LessonPipelineResponse:
        """Create error response when pipeline fails"""
        return LessonPipelineResponse(
            lesson_plan={"error": error, "status": "failed"},
            content={"error": error, "status": "failed"},
            assessment=None,
            visual_aids=None,
            pipeline_metadata={
                "pipeline_version": self.version,
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "lesson_type": request.lesson_type,
                "error": error
            },
            execution_summary={
                "total_processing_time": (datetime.now() - start_time).total_seconds(),
                "steps_executed": [],
                "success_rate": 0.0,
                "components_generated": {
                    "lesson_plan": False,
                    "content": False,
                    "assessment": False,
                    "visual_aids": False
                }
            },
            recommendations=["Check system logs for error details", "Retry with simpler parameters"],
            next_steps=["Review error and adjust request", "Contact support if issue persists"]
        )

# =============================
# Global Pipeline Instance
# =============================
lesson_pipeline = LessonPipeline()

# =============================
# Convenience Functions
# =============================
async def run_complete_pipeline(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run complete lesson pipeline"""
    request = LessonPipelineRequest(**request_data)
    response = await lesson_pipeline.execute_pipeline(request)
    return response.dict()

async def run_planning_only(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run planning-only pipeline"""
    request_data["lesson_type"] = "planning_only"
    request = LessonPipelineRequest(**request_data)
    response = await lesson_pipeline.execute_pipeline(request)
    return response.dict()

async def run_content_only(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run content-only pipeline"""
    request_data["lesson_type"] = "content_only"
    request = LessonPipelineRequest(**request_data)
    response = await lesson_pipeline.execute_pipeline(request)
    return response.dict()

# Legacy function for backward compatibility
async def run_pipeline(context: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy pipeline runner for backward compatibility"""
    try:
        # Convert legacy context to new request format
        request_data = {
            "teacher_id": context.get("teacher_id", "unknown"),
            "class_id": context.get("class_id", "unknown"),
            "topic": context.get("topic", "General Topic"),
            "grade_level": context.get("grade_level", "elementary"),
            "lesson_type": "complete"
        }
        
        return await run_complete_pipeline(request_data)
        
    except Exception as e:
        logger.error(f"[Legacy Pipeline] Error: {str(e)}")
        return {
            "error": str(e),
            "lesson_plan": {},
            "content": {},
            "status": "error"
        }
