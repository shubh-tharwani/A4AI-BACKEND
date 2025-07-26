"""
Planning Service
Handles AI-powered lesson planning, scheduling, and educational content planning
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import json

from dao.planning_dao import planning_dao
from services.vertex_ai import vertex_ai_service
from utils.dao_error_handler import handle_service_dao_errors, ensure_document_id
from config import PROJECT_ID

logger = logging.getLogger(__name__)


@handle_service_dao_errors("generate_lesson_plan")
async def generate_lesson_plan(
    class_id: str,
    plan_type: str = "weekly",
    duration: int = 7,
    user_id: Optional[str] = 'current user',
    curriculum_standards: Optional[List[str]] = None,
    learning_objectives: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Auto-generate comprehensive lesson plan based on class data, holidays, and engagement
    
    Args:
        class_id (str): Class identifier
        plan_type (str): Type of plan ("daily", "weekly", "monthly")
        duration (int): Number of days for the plan
        user_id (str, optional): User creating the plan
        curriculum_standards (List[str], optional): Relevant curriculum standards
        learning_objectives (List[str], optional): Specific learning objectives
        
    Returns:
        Dict[str, Any]: Generated lesson plan with metadata
        
    Raises:
        ServiceError: If lesson plan generation fails
        DAOError: If database operations fail
    """
    logger.info(f"Generating {plan_type} lesson plan for class {class_id}, duration: {duration} days")
    
    # Validate inputs
    class_id = ensure_document_id(class_id, "class_id")
    if plan_type not in ["daily", "weekly", "monthly"]:
        raise ValueError("Plan type must be 'daily', 'weekly', or 'monthly'")
    if duration < 1 or duration > 365:
        raise ValueError("Duration must be between 1 and 365 days")
    
    try:
        # Fetch class details
        class_info = planning_dao.get_class_details(class_id)
        if not class_info:
            raise ValueError(f"Class details not found for class: {class_id}")
        
        # Calculate date range for planning
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration)
        
        # Fetch relevant data
        holidays = planning_dao.get_holidays(start_date, end_date)
        engagement_metrics = planning_dao.get_engagement_metrics(class_id, limit=30)
        
        # Get existing lesson plans for context
        existing_plans = planning_dao.get_class_lesson_plans(class_id, limit=5)
        
        # Generate enhanced lesson plan using AI
        plan_data = await _generate_ai_lesson_plan(
            class_info=class_info,
            plan_type=plan_type,
            duration=duration,
            holidays=holidays,
            engagement_metrics=engagement_metrics,
            existing_plans=existing_plans,
            curriculum_standards=curriculum_standards,
            learning_objectives=learning_objectives
        )
        
        # Prepare lesson plan data for storage
        lesson_plan_data = {
            "class_id": class_id,
            "plan_type": plan_type,
            "duration": duration,
            "content": plan_data,
            "user_id": user_id,
            "curriculum_standards": curriculum_standards or [],
            "learning_objectives": learning_objectives or [],
            "metadata": {
                "generation_method": "ai_enhanced",
                "holidays_considered": len(holidays),
                "engagement_data_points": len(engagement_metrics),
                "existing_plans_referenced": len(existing_plans),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        # Save to database
        plan_id = planning_dao.save_lesson_plan(lesson_plan_data)
        
        # Prepare response
        result = {
            "status": "success",
            "plan_id": plan_id,
            "lesson_plan": plan_data,
            "metadata": lesson_plan_data["metadata"],
            "class_info": {
                "class_id": class_id,
                "size": class_info.get("size", 0),
                "subjects": class_info.get("subjects", [])
            }
        }
        
        logger.info(f"Successfully generated lesson plan: {plan_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating lesson plan for class {class_id}: {e}")
        # Return fallback response
        return await _create_fallback_lesson_plan(class_id, plan_type, duration)


@handle_service_dao_errors("generate_detailed_curriculum_plan")
async def generate_detailed_curriculum_plan(
    class_id: str,
    subject: str,
    grade_level: int,
    semester_duration: int = 90,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive curriculum plan for a subject over a semester
    
    Args:
        class_id (str): Class identifier
        subject (str): Subject area
        grade_level (int): Grade level (1-12)
        semester_duration (int): Duration in days (default 90 days)
        user_id (str, optional): User creating the plan
        
    Returns:
        Dict[str, Any]: Generated curriculum plan
    """
    logger.info(f"Generating curriculum plan for {subject}, grade {grade_level}")
    
    # Validate inputs
    class_id = ensure_document_id(class_id, "class_id")
    if not subject or not subject.strip():
        raise ValueError("Subject cannot be empty")
    if grade_level < 1 or grade_level > 12:
        raise ValueError("Grade level must be between 1 and 12")
    if semester_duration < 30 or semester_duration > 365:
        raise ValueError("Semester duration must be between 30 and 365 days")
    
    try:
        # Get class information
        class_info = planning_dao.get_class_details(class_id)
        if not class_info:
            raise ValueError(f"Class details not found for class: {class_id}")
        
        # Generate comprehensive curriculum using AI
        curriculum_prompt = f"""
        Create a comprehensive {semester_duration}-day curriculum plan for {subject} at grade {grade_level}.
        
        Class Information:
        - Class size: {class_info.get('size', 'Unknown')} students
        - Available subjects: {', '.join(class_info.get('subjects', []))}
        
        Requirements:
        - Age-appropriate content for grade {grade_level}
        - Progressive skill building throughout the semester
        - Regular assessments and milestones
        - Interactive and engaging activities
        - Alignment with common core standards where applicable
        - Integration opportunities with other subjects
        - Accommodation for different learning styles
        
        Structure the response as JSON:
        {{
            "curriculum_overview": {{
                "subject": "{subject}",
                "grade_level": {grade_level},
                "duration_days": {semester_duration},
                "learning_outcomes": ["outcome1", "outcome2", "..."],
                "key_concepts": ["concept1", "concept2", "..."]
            }},
            "units": [
                {{
                    "unit_number": 1,
                    "title": "Unit Title",
                    "duration_days": 15,
                    "learning_objectives": ["objective1", "objective2"],
                    "key_topics": ["topic1", "topic2"],
                    "activities": ["activity1", "activity2"],
                    "assessments": ["assessment1", "assessment2"],
                    "resources": ["resource1", "resource2"]
                }}
            ],
            "assessment_strategy": {{
                "formative_assessments": ["method1", "method2"],
                "summative_assessments": ["method1", "method2"],
                "grading_rubrics": ["rubric1", "rubric2"]
            }},
            "resources": {{
                "required_materials": ["material1", "material2"],
                "recommended_tools": ["tool1", "tool2"],
                "external_resources": ["resource1", "resource2"]
            }}
        }}
        """
        
        # Use centralized Vertex AI service
        response = await vertex_ai_service.generate_content(curriculum_prompt)
        curriculum_data = _parse_curriculum_response(response, subject, grade_level)
        
        # Prepare curriculum plan data for storage
        curriculum_plan_data = {
            "class_id": class_id,
            "subject": subject,
            "grade_level": grade_level,
            "semester_duration": semester_duration,
            "content": curriculum_data,
            "user_id": user_id,
            "plan_type": "curriculum",
            "metadata": {
                "generation_method": "ai_curriculum_planner",
                "total_units": len(curriculum_data.get("units", [])),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        # Save to database
        plan_id = planning_dao.save_lesson_plan(curriculum_plan_data)
        
        result = {
            "status": "success",
            "plan_id": plan_id,
            "curriculum_plan": curriculum_data,
            "metadata": curriculum_plan_data["metadata"]
        }
        
        logger.info(f"Successfully generated curriculum plan: {plan_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating curriculum plan: {e}")
        raise


@handle_service_dao_errors("get_lesson_plan")
async def get_lesson_plan(plan_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve lesson plan by ID
    
    Args:
        plan_id (str): Lesson plan ID
        user_id (str, optional): User requesting the plan
        
    Returns:
        Dict[str, Any]: Lesson plan data
    """
    plan_id = ensure_document_id(plan_id, "plan_id")
    
    plan_data = planning_dao.get_lesson_plan(plan_id)
    if not plan_data:
        raise ValueError("Lesson plan not found")
    
    # Check ownership if user_id provided
    if user_id and plan_data.get("user_id") != user_id:
        # In a real implementation, check user role/permissions here
        logger.warning(f"User {user_id} attempted to access plan {plan_id} owned by {plan_data.get('user_id')}")
    
    return plan_data


@handle_service_dao_errors("get_class_lesson_plans")
async def get_class_lesson_plans(
    class_id: str,
    limit: int = 10,
    plan_type: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get lesson plans for a class
    
    Args:
        class_id (str): Class ID
        limit (int): Maximum number of plans to retrieve
        plan_type (str, optional): Filter by plan type
        user_id (str, optional): User requesting the plans
        
    Returns:
        List[Dict[str, Any]]: List of lesson plans
    """
    class_id = ensure_document_id(class_id, "class_id")
    
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100")
    
    plans = planning_dao.get_class_lesson_plans(class_id, limit, plan_type)
    
    # Enhance plans with display metadata
    enhanced_plans = []
    for plan in plans:
        enhanced_plan = {
            **plan,
            "display_title": _generate_plan_title(plan),
            "summary": _generate_plan_summary(plan),
            "created_date": plan.get("created_at", "").split("T")[0] if plan.get("created_at") else None
        }
        enhanced_plans.append(enhanced_plan)
    
    return enhanced_plans


@handle_service_dao_errors("update_lesson_plan")
async def update_lesson_plan(
    plan_id: str,
    updates: Dict[str, Any],
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update lesson plan
    
    Args:
        plan_id (str): Lesson plan ID
        updates (Dict[str, Any]): Fields to update
        user_id (str, optional): User making the update
        
    Returns:
        Dict[str, Any]: Update result
    """
    plan_id = ensure_document_id(plan_id, "plan_id")
    
    # Verify ownership if user_id provided
    if user_id:
        existing_plan = planning_dao.get_lesson_plan(plan_id)
        if not existing_plan:
            raise ValueError("Lesson plan not found")
        if existing_plan.get("user_id") != user_id:
            raise PermissionError("Not authorized to update this lesson plan")
    
    # Add update metadata
    updates_with_meta = {
        **updates,
        "last_modified_by": user_id,
        "last_modified_at": datetime.utcnow().isoformat()
    }
    
    success = planning_dao.update_lesson_plan(plan_id, updates_with_meta)
    
    return {
        "status": "success" if success else "failed",
        "plan_id": plan_id,
        "message": "Lesson plan updated successfully" if success else "Failed to update lesson plan"
    }


@handle_service_dao_errors("delete_lesson_plan")
async def delete_lesson_plan(plan_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Delete lesson plan
    
    Args:
        plan_id (str): Lesson plan ID
        user_id (str, optional): User requesting deletion
        
    Returns:
        Dict[str, Any]: Deletion result
    """
    plan_id = ensure_document_id(plan_id, "plan_id")
    
    # Verify ownership if user_id provided
    if user_id:
        existing_plan = planning_dao.get_lesson_plan(plan_id)
        if not existing_plan:
            raise ValueError("Lesson plan not found")
        if existing_plan.get("user_id") != user_id:
            raise PermissionError("Not authorized to delete this lesson plan")
    
    success = planning_dao.delete_lesson_plan(plan_id)
    
    return {
        "status": "success" if success else "failed",
        "plan_id": plan_id,
        "message": "Lesson plan deleted successfully" if success else "Failed to delete lesson plan"
    }


# Helper functions

async def _generate_ai_lesson_plan(
    class_info: Dict[str, Any],
    plan_type: str,
    duration: int,
    holidays: List[Dict[str, Any]],
    engagement_metrics: List[Dict[str, Any]],
    existing_plans: List[Dict[str, Any]],
    curriculum_standards: Optional[List[str]] = None,
    learning_objectives: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Generate lesson plan using AI with comprehensive context"""
    
    # Prepare context information
    holiday_dates = [h.get("date", "") for h in holidays if h.get("date")]
    engagement_summary = _analyze_engagement_metrics(engagement_metrics)
    subjects = class_info.get("subjects", [])
    class_size = class_info.get("size", 0)
    
    # Create enhanced AI prompt
    prompt = f"""
    You are an expert AI Lesson Planning Assistant specializing in educational curriculum design.
    
    Create a comprehensive {plan_type} lesson plan with the following specifications:
    
    CLASS INFORMATION:
    - Class ID: {class_info.get('class_id', 'Unknown')}
    - Number of students: {class_size}
    - Subjects to cover: {', '.join(subjects)}
    - Plan duration: {duration} days
    - Plan type: {plan_type}
    
    CONTEXT DATA:
    - Holidays to consider: {', '.join(holiday_dates) if holiday_dates else 'None'}
    - Student engagement trends: {engagement_summary}
    - Number of existing plans: {len(existing_plans)}
    
    CURRICULUM REQUIREMENTS:
    - Standards alignment: {', '.join(curriculum_standards) if curriculum_standards else 'General standards'}
    - Learning objectives: {', '.join(learning_objectives) if learning_objectives else 'Grade-appropriate objectives'}
    
    PLANNING GUIDELINES:
    1. Create age-appropriate activities for the grade level
    2. Balance different subject areas effectively
    3. Include interactive and engaging elements
    4. Account for holidays and breaks in scheduling
    5. Incorporate assessment opportunities
    6. Allow flexibility for different learning styles
    7. Include both individual and group activities
    8. Ensure proper progression of difficulty
    
    FORMAT REQUIREMENTS:
    Provide response as valid JSON with this exact structure:
    {{
        "plan_overview": {{
            "title": "Descriptive plan title",
            "description": "Brief plan description",
            "total_days": {duration},
            "subjects_covered": {subjects},
            "key_themes": ["theme1", "theme2"],
            "learning_outcomes": ["outcome1", "outcome2"]
        }},
        "daily_schedule": [
            {{
                "day": 1,
                "date": "2025-07-21",
                "is_holiday": false,
                "activities": [
                    {{
                        "time": "09:00-09:45",
                        "subject": "Mathematics",
                        "topic": "Specific topic",
                        "activity_type": "direct_instruction|group_work|individual_practice|assessment",
                        "description": "Detailed activity description",
                        "materials_needed": ["material1", "material2"],
                        "learning_objective": "What students will learn",
                        "assessment_method": "How progress will be measured"
                    }}
                ],
                "homework": "Optional homework assignment",
                "notes": "Special considerations for this day"
            }}
        ],
        "assessment_plan": {{
            "formative_assessments": ["method1", "method2"],
            "summative_assessments": ["method1", "method2"],
            "grading_criteria": ["criteria1", "criteria2"]
        }},
        "resources": {{
            "required_materials": ["material1", "material2"],
            "digital_tools": ["tool1", "tool2"],
            "reference_books": ["book1", "book2"]
        }},
        "differentiation": {{
            "advanced_learners": ["strategy1", "strategy2"],
            "struggling_learners": ["support1", "support2"],
            "english_language_learners": ["accommodation1", "accommodation2"]
        }}
    }}
    """
    
    try:
        # Use centralized Vertex AI service
        response = await vertex_ai_service.generate_content(prompt)
        
        # Parse and validate response
        plan_data = _parse_lesson_plan_response(response, plan_type, duration)
        
        return plan_data
        
    except Exception as e:
        logger.error(f"Error generating AI lesson plan: {e}")
        return _create_fallback_plan_data(class_info, plan_type, duration)


def _parse_lesson_plan_response(response: str, plan_type: str, duration: int) -> Dict[str, Any]:
    """Parse and validate lesson plan response from AI"""
    try:
        plan_data = json.loads(response)
        
        # Ensure required fields exist
        if "plan_overview" not in plan_data:
            plan_data["plan_overview"] = {
                "title": f"{plan_type.title()} Lesson Plan",
                "description": f"Comprehensive {plan_type} educational plan",
                "total_days": duration
            }
        
        if "daily_schedule" not in plan_data:
            plan_data["daily_schedule"] = []
        
        return plan_data
        
    except json.JSONDecodeError:
        logger.warning("Failed to parse lesson plan response as JSON, creating fallback")
        return _create_fallback_plan_data({}, plan_type, duration)


def _parse_curriculum_response(response: str, subject: str, grade_level: int) -> Dict[str, Any]:
    """Parse and validate curriculum response from AI"""
    try:
        curriculum_data = json.loads(response)
        
        # Ensure required fields exist
        if "curriculum_overview" not in curriculum_data:
            curriculum_data["curriculum_overview"] = {
                "subject": subject,
                "grade_level": grade_level,
                "learning_outcomes": []
            }
        
        if "units" not in curriculum_data:
            curriculum_data["units"] = []
        
        return curriculum_data
        
    except json.JSONDecodeError:
        logger.warning("Failed to parse curriculum response as JSON, creating fallback")
        return {
            "curriculum_overview": {
                "subject": subject,
                "grade_level": grade_level,
                "learning_outcomes": [f"Master key concepts in {subject}"]
            },
            "units": [],
            "assessment_strategy": {},
            "resources": {}
        }


async def _create_fallback_lesson_plan(class_id: str, plan_type: str, duration: int) -> Dict[str, Any]:
    """Create fallback lesson plan when AI generation fails"""
    logger.warning("Creating fallback lesson plan")
    
    return {
        "status": "fallback",
        "plan_id": str(uuid.uuid4()),
        "lesson_plan": {
            "plan_overview": {
                "title": f"Basic {plan_type.title()} Plan",
                "description": f"Fallback {plan_type} educational plan",
                "total_days": duration
            },
            "daily_schedule": [{
                "day": 1,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "activities": [{
                    "time": "09:00-09:45",
                    "subject": "General",
                    "topic": "Review and Assessment",
                    "description": "General review activities"
                }]
            }]
        },
        "metadata": {
            "fallback": True,
            "generated_at": datetime.utcnow().isoformat()
        },
        "message": "Generated fallback plan due to service unavailability"
    }


def _create_fallback_plan_data(class_info: Dict[str, Any], plan_type: str, duration: int) -> Dict[str, Any]:
    """Create fallback plan data"""
    return {
        "plan_overview": {
            "title": f"Basic {plan_type.title()} Plan",
            "description": f"Simple {plan_type} educational plan",
            "total_days": duration
        },
        "daily_schedule": [],
        "assessment_plan": {},
        "resources": {}
    }


def _analyze_engagement_metrics(metrics: List[Dict[str, Any]]) -> str:
    """Analyze engagement metrics to provide context"""
    if not metrics:
        return "No engagement data available"
    
    # Simple analysis - in a real implementation, this would be more sophisticated
    total_metrics = len(metrics)
    avg_engagement = sum(m.get("engagement_score", 0) for m in metrics) / total_metrics if total_metrics > 0 else 0
    
    if avg_engagement > 0.8:
        return "High student engagement - maintain current activity levels"
    elif avg_engagement > 0.6:
        return "Moderate engagement - consider adding more interactive elements"
    else:
        return "Low engagement - focus on hands-on activities and varied instructional methods"


def _generate_plan_title(plan: Dict[str, Any]) -> str:
    """Generate display title for plan"""
    plan_type = plan.get("plan_type", "lesson")
    duration = plan.get("duration", 1)
    return f"{plan_type.title()} Plan ({duration} days)"


def _generate_plan_summary(plan: Dict[str, Any]) -> str:
    """Generate summary for plan"""
    content = plan.get("content", {})
    overview = content.get("plan_overview", {})
    return overview.get("description", "Educational lesson plan")
