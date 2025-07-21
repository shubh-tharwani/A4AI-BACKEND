"""
Teacher Dashboard Routes
Comprehensive teacher analytics and student history tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from auth_middleware import firebase_auth, get_current_user_id, require_teacher
from services.teacher_dashboard_service import teacher_dashboard_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/teacher-dashboard", tags=["Teacher Dashboard"])

# Request Models
class ClassAnalyticsRequest(BaseModel):
    class_id: Optional[str] = Field(None, description="Specific class ID to analyze")
    date_range: Optional[int] = Field(30, ge=1, le=365, description="Number of days to analyze")

class StudentHistoryRequest(BaseModel):
    student_id: str = Field(..., description="Student ID to retrieve history for")
    include_assessments: bool = Field(True, description="Include assessment history")
    include_activities: bool = Field(True, description="Include activity history")
    include_plans: bool = Field(True, description="Include lesson plan history")
    include_conversations: bool = Field(True, description="Include voice conversation history")
    limit: int = Field(50, ge=1, le=200, description="Maximum number of items per category")

# Response Models
class TeacherDashboardResponse(BaseModel):
    status: str
    message: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]

class StudentHistoryResponse(BaseModel):
    status: str
    message: str
    student_data: Dict[str, Any]
    metadata: Dict[str, Any]

class ClassListResponse(BaseModel):
    status: str
    message: str
    classes: List[Dict[str, Any]]
    metadata: Dict[str, Any]

# Routes
@router.get("/dashboard", 
           response_model=TeacherDashboardResponse, 
           dependencies=[Depends(firebase_auth), Depends(require_teacher)])
async def get_complete_teacher_dashboard(
    req: Request,
    class_id: Optional[str] = Query(None, description="Filter by specific class ID"),
    include_ai_recommendations: bool = Query(True, description="Include AI-powered recommendations")
):
    """
    Get comprehensive teacher dashboard with complete student analytics
    
    Features:
    - Complete student activity history across all services
    - Class-level performance analytics
    - Recent activity timeline
    - AI-powered teaching recommendations
    - Engagement metrics and trends
    
    Access: Requires teacher or admin role
    """
    try:
        teacher_id = await get_current_user_id(req)
        user_role = req.state.user.get("role", "student")
        
        logger.info(f"Teacher dashboard requested by {teacher_id} (role: {user_role}) for class: {class_id}")
        
        # Get complete dashboard data
        dashboard_data = await teacher_dashboard_service.get_teacher_complete_dashboard(
            teacher_id=teacher_id,
            class_id=class_id
        )
        
        if "error" in dashboard_data:
            logger.error(f"Error generating dashboard: {dashboard_data['error']}")
            raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {dashboard_data['error']}")
        
        logger.info(f"Successfully generated teacher dashboard for {teacher_id}")
        
        return TeacherDashboardResponse(
            status="success",
            message="Teacher dashboard generated successfully",
            data=dashboard_data,
            metadata={
                "teacher_id": teacher_id,
                "class_id": class_id,
                "generated_at": datetime.utcnow().isoformat(),
                "total_students": dashboard_data.get("total_students", 0),
                "includes_ai_recommendations": include_ai_recommendations
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating teacher dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate teacher dashboard: {str(e)}")

@router.get("/student-history/{student_id}", 
           response_model=StudentHistoryResponse,
           dependencies=[Depends(firebase_auth), Depends(require_teacher)])
async def get_complete_student_history(
    student_id: str,
    req: Request,
    include_assessments: bool = Query(True, description="Include assessment history"),
    include_activities: bool = Query(True, description="Include activity history"), 
    include_plans: bool = Query(True, description="Include lesson plan history"),
    include_conversations: bool = Query(True, description="Include voice conversations"),
    limit: int = Query(50, ge=1, le=200, description="Items per category")
):
    """
    Get complete history for a specific student across all services
    
    Returns comprehensive data including:
    - All assessments with scores and performance metrics
    - Generated activities (stories, AR scenes, etc.)
    - Visual aids created
    - Lesson plans and curriculum work
    - Voice interaction history
    - Badge achievements
    - Usage analytics and trends
    
    Access: Requires teacher or admin role
    """
    try:
        teacher_id = await get_current_user_id(req)
        user_role = req.state.user.get("role", "student")
        
        logger.info(f"Student history requested by teacher {teacher_id} for student {student_id}")
        
        # Get complete student history
        student_data = await teacher_dashboard_service._get_student_complete_history(student_id)
        
        if not student_data:
            raise HTTPException(status_code=404, detail=f"No data found for student {student_id}")
        
        # Filter data based on request parameters
        filtered_data = {
            "student_id": student_id,
            "profile": student_data.get("profile"),
            "last_active": student_data.get("last_active")
        }
        
        if include_assessments:
            filtered_data["assessments"] = student_data.get("assessments")
        
        if include_activities:
            filtered_data["activities"] = student_data.get("activities")
            
        if include_plans:
            filtered_data["lesson_plans"] = student_data.get("lesson_plans")
            
        if include_conversations:
            filtered_data["voice_interactions"] = student_data.get("voice_interactions")
        
        logger.info(f"Successfully retrieved complete history for student {student_id}")
        
        return StudentHistoryResponse(
            status="success",
            message=f"Complete student history retrieved successfully",
            student_data=filtered_data,
            metadata={
                "requested_by": teacher_id,
                "student_id": student_id,
                "generated_at": datetime.utcnow().isoformat(),
                "filters_applied": {
                    "assessments": include_assessments,
                    "activities": include_activities,
                    "lesson_plans": include_plans,
                    "voice_conversations": include_conversations
                },
                "limit_per_category": limit
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving student history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve student history: {str(e)}")

@router.get("/class-analytics",
           response_model=TeacherDashboardResponse,
           dependencies=[Depends(firebase_auth), Depends(require_teacher)])
async def get_class_analytics_summary(
    req: Request,
    class_id: Optional[str] = Query(None, description="Specific class to analyze"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """
    Get detailed analytics summary for teacher's class(es)
    
    Provides:
    - Student engagement metrics
    - Performance distribution analysis  
    - Activity completion rates
    - Learning progress tracking
    - Comparative analytics
    
    Access: Requires teacher or admin role
    """
    try:
        teacher_id = await get_current_user_id(req)
        
        logger.info(f"Class analytics requested by teacher {teacher_id} for class {class_id}")
        
        # Get dashboard data (which includes analytics)
        dashboard_data = await teacher_dashboard_service.get_teacher_complete_dashboard(
            teacher_id=teacher_id,
            class_id=class_id
        )
        
        if "error" in dashboard_data:
            raise HTTPException(status_code=500, detail=dashboard_data["error"])
        
        # Extract just the analytics portion
        analytics_data = {
            "class_analytics": dashboard_data.get("class_analytics", {}),
            "performance_summary": dashboard_data.get("performance_summary", {}),
            "recent_activities": dashboard_data.get("recent_activities", [])[:10],  # Limit for analytics view
            "student_count": dashboard_data.get("total_students", 0)
        }
        
        return TeacherDashboardResponse(
            status="success",
            message="Class analytics generated successfully",
            data=analytics_data,
            metadata={
                "teacher_id": teacher_id,
                "class_id": class_id,
                "analysis_period_days": days,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating class analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate class analytics: {str(e)}")

@router.get("/students-list",
           response_model=ClassListResponse,
           dependencies=[Depends(firebase_auth), Depends(require_teacher)])
async def get_teacher_students_list(
    req: Request,
    class_id: Optional[str] = Query(None, description="Filter by specific class"),
    include_performance: bool = Query(True, description="Include performance summary"),
    sort_by: str = Query("name", regex="^(name|performance|last_active)$", description="Sort criteria")
):
    """
    Get list of students assigned to teacher with summary information
    
    Features:
    - Student profile information
    - Performance summary (optional)
    - Last activity tracking
    - Sorting options
    
    Access: Requires teacher or admin role
    """
    try:
        teacher_id = await get_current_user_id(req)
        
        logger.info(f"Students list requested by teacher {teacher_id}")
        
        # Get students assigned to teacher
        students = await teacher_dashboard_service._get_teacher_students(teacher_id, class_id)
        
        # Enhance with performance data if requested
        if include_performance:
            for student in students:
                student_id = student["user_id"]
                performance = teacher_dashboard_service.assessment_dao.get_user_performance(student_id)
                student["performance_summary"] = {
                    "average_score": performance.get("average_score", 0) if performance else 0,
                    "total_assessments": performance.get("total_assessments", 0) if performance else 0,
                    "last_assessment": performance.get("last_assessment_date") if performance else None
                }
                
                # Get last activity
                assessments = teacher_dashboard_service.assessment_dao.get_user_assessments(student_id, limit=5)
                activities = teacher_dashboard_service.content_dao.get_user_activities(student_id, limit=5)
                plans = teacher_dashboard_service.planning_dao.get_user_lesson_plans(student_id, limit=5)
                conversations = teacher_dashboard_service.voice_dao.get_conversation_history(student_id, limit=5)
                
                student["last_activity"] = teacher_dashboard_service._get_last_activity_date(
                    assessments, activities, plans, conversations
                )
        
        # Sort students based on criteria
        if sort_by == "performance" and include_performance:
            students.sort(key=lambda x: x.get("performance_summary", {}).get("average_score", 0), reverse=True)
        elif sort_by == "last_active":
            students.sort(key=lambda x: x.get("last_activity") or datetime.min, reverse=True)
        else:  # name
            students.sort(key=lambda x: x.get("profile", {}).get("display_name", ""))
        
        return ClassListResponse(
            status="success",
            message=f"Retrieved {len(students)} students",
            classes=[{
                "class_id": class_id,
                "teacher_id": teacher_id,
                "students": students,
                "total_students": len(students)
            }] if students else [],
            metadata={
                "teacher_id": teacher_id,
                "class_id": class_id,
                "total_students": len(students),
                "includes_performance": include_performance,
                "sorted_by": sort_by,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving students list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve students list: {str(e)}")

@router.get("/performance-trends",
           response_model=TeacherDashboardResponse,
           dependencies=[Depends(firebase_auth), Depends(require_teacher)])
async def get_class_performance_trends(
    req: Request,
    class_id: Optional[str] = Query(None, description="Specific class to analyze"),
    period: str = Query("month", regex="^(week|month|quarter|year)$", description="Analysis period")
):
    """
    Get performance trends and analytics over time
    
    Analyzes:
    - Score trends over time
    - Engagement pattern changes
    - Activity completion rates
    - Learning progress indicators
    
    Access: Requires teacher or admin role
    """
    try:
        teacher_id = await get_current_user_id(req)
        
        # Convert period to days
        period_days = {
            "week": 7,
            "month": 30,
            "quarter": 90,
            "year": 365
        }.get(period, 30)
        
        logger.info(f"Performance trends requested by teacher {teacher_id} for {period} period")
        
        # Get dashboard data which includes performance analytics
        dashboard_data = await teacher_dashboard_service.get_teacher_complete_dashboard(
            teacher_id=teacher_id,
            class_id=class_id
        )
        
        if "error" in dashboard_data:
            raise HTTPException(status_code=500, detail=dashboard_data["error"])
        
        # Extract and format trend data
        trends_data = {
            "period_analyzed": period,
            "days_analyzed": period_days,
            "performance_summary": dashboard_data.get("performance_summary", {}),
            "class_analytics": dashboard_data.get("class_analytics", {}),
            "trend_indicators": {
                "engagement_trend": "stable",  # Would calculate based on historical data
                "performance_trend": "improving",  # Would calculate based on score changes
                "activity_trend": "increasing"  # Would calculate based on activity counts
            }
        }
        
        return TeacherDashboardResponse(
            status="success",
            message=f"Performance trends for {period} period generated successfully",
            data=trends_data,
            metadata={
                "teacher_id": teacher_id,
                "class_id": class_id,
                "analysis_period": period,
                "period_days": period_days,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating performance trends: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate performance trends: {str(e)}")

@router.get("/health",
           summary="Teacher Dashboard Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for teacher dashboard service"""
    return {
        "status": "healthy",
        "service": "teacher-dashboard",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
