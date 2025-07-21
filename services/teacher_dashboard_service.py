"""
Teacher Dashboard Service
Provides comprehensive analytics and history tracking for teachers
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from dao.user_dao import user_dao
from dao.assessment_dao import assessment_dao
from dao.content_dao import content_dao
from dao.planning_dao import planning_dao
from dao.voice_assistant_dao import voice_assistant_dao
from services.vertex_ai import get_vertex_ai_client

logger = logging.getLogger(__name__)

class TeacherDashboardService:
    """Service for teacher dashboard analytics and history tracking"""
    
    def __init__(self):
        self.user_dao = user_dao
        self.assessment_dao = assessment_dao
        self.content_dao = content_dao
        self.planning_dao = planning_dao
        self.voice_dao = voice_assistant_dao
        self.ai_client = get_vertex_ai_client()

    async def get_teacher_complete_dashboard(self, teacher_id: str, class_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive teacher dashboard with all student activities
        
        Args:
            teacher_id: Teacher's user ID
            class_id: Optional class filter
            
        Returns:
            Complete dashboard data with analytics
        """
        try:
            # Get all students (or filter by class if provided)
            students = await self._get_teacher_students(teacher_id, class_id)
            
            dashboard_data = {
                "teacher_id": teacher_id,
                "class_id": class_id,
                "generated_at": datetime.utcnow().isoformat(),
                "total_students": len(students),
                "students": [],
                "class_analytics": {},
                "recent_activities": [],
                "performance_summary": {},
                "recommendations": []
            }
            
            # Process each student
            for student in students:
                student_id = student["user_id"]
                student_data = await self._get_student_complete_history(student_id)
                dashboard_data["students"].append(student_data)
            
            # Generate class-level analytics
            dashboard_data["class_analytics"] = await self._generate_class_analytics(students)
            
            # Get recent activities across all students
            dashboard_data["recent_activities"] = await self._get_recent_class_activities(students, limit=20)
            
            # Generate performance summary
            dashboard_data["performance_summary"] = await self._generate_performance_summary(students)
            
            # Generate AI-powered recommendations
            dashboard_data["recommendations"] = await self._generate_teacher_recommendations(dashboard_data)
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error generating teacher dashboard: {e}")
            return {
                "error": str(e),
                "teacher_id": teacher_id,
                "generated_at": datetime.utcnow().isoformat()
            }

    async def _get_student_complete_history(self, student_id: str) -> Dict[str, Any]:
        """Get complete history for a single student"""
        
        # Get assessments
        assessments = self.assessment_dao.get_user_assessments(student_id, limit=50)
        performance = self.assessment_dao.get_user_performance(student_id)
        
        # Get activities and badges
        activities = self.content_dao.get_user_activities(student_id, limit=50)
        visual_aids = self.content_dao.get_user_visual_aids(student_id, limit=50)
        
        # Get lesson plans
        lesson_plans = self.planning_dao.get_user_lesson_plans(student_id, limit=50)
        
        # Get voice conversations
        conversations = self.voice_dao.get_conversation_history(student_id, limit=30)
        
        # Get user profile
        profile = self.user_dao.get_user_profile(student_id)
        
        return {
            "student_id": student_id,
            "profile": profile,
            "assessments": {
                "history": assessments,
                "performance": performance,
                "total_count": len(assessments)
            },
            "activities": {
                "activities": activities,
                "visual_aids": visual_aids,
                "total_activities": len(activities),
                "total_visual_aids": len(visual_aids)
            },
            "lesson_plans": {
                "plans": lesson_plans,
                "total_count": len(lesson_plans)
            },
            "voice_interactions": {
                "conversations": conversations,
                "total_conversations": len(conversations)
            },
            "last_active": self._get_last_activity_date(assessments, activities, lesson_plans, conversations)
        }

    async def _get_teacher_students(self, teacher_id: str, class_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get students assigned to teacher"""
        # This would be implemented based on your class/student assignment system
        # For now, returning a placeholder - you'll need to implement based on your requirements
        
        # Example implementation:
        try:
            # If you have a classes collection with student assignments
            if class_id:
                # Get specific class students
                students_query = self.user_dao.db.collection("class_assignments").where("class_id", "==", class_id).where("teacher_id", "==", teacher_id)
            else:
                # Get all students assigned to this teacher
                students_query = self.user_dao.db.collection("class_assignments").where("teacher_id", "==", teacher_id)
            
            students = []
            for doc in students_query.stream():
                student_data = doc.to_dict()
                # Get full student profile
                profile = self.user_dao.get_user_profile(student_data["student_id"])
                if profile:
                    students.append({
                        "user_id": student_data["student_id"],
                        "class_id": student_data.get("class_id"),
                        "profile": profile
                    })
            
            return students
            
        except Exception as e:
            logger.error(f"Error getting teacher students: {e}")
            # Fallback: return all students (for demo purposes)
            # In production, you should implement proper class assignments
            return []

    async def _generate_class_analytics(self, students: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate analytics for the entire class"""
        
        total_students = len(students)
        if total_students == 0:
            return {"message": "No students found"}
        
        # Aggregate statistics
        total_assessments = 0
        total_activities = 0
        total_lesson_plans = 0
        total_conversations = 0
        average_scores = []
        
        active_students = 0
        inactive_students = 0
        
        for student in students:
            student_id = student["user_id"]
            
            # Count activities
            assessments = self.assessment_dao.get_user_assessments(student_id, limit=100)
            activities = self.content_dao.get_user_activities(student_id, limit=100)
            plans = self.planning_dao.get_user_lesson_plans(student_id, limit=100)
            conversations = self.voice_dao.get_conversation_history(student_id, limit=100)
            
            total_assessments += len(assessments)
            total_activities += len(activities)
            total_lesson_plans += len(plans)
            total_conversations += len(conversations)
            
            # Get performance data
            performance = self.assessment_dao.get_user_performance(student_id)
            if performance and performance.get("average_score"):
                average_scores.append(performance["average_score"])
            
            # Check if student is active (activity in last 7 days)
            last_activity = self._get_last_activity_date(assessments, activities, plans, conversations)
            if last_activity:
                days_since_activity = (datetime.utcnow() - last_activity).days
                if days_since_activity <= 7:
                    active_students += 1
                else:
                    inactive_students += 1
        
        class_average_score = sum(average_scores) / len(average_scores) if average_scores else 0
        
        return {
            "total_students": total_students,
            "active_students": active_students,
            "inactive_students": inactive_students,
            "total_assessments": total_assessments,
            "total_activities": total_activities,
            "total_lesson_plans": total_lesson_plans,
            "total_voice_conversations": total_conversations,
            "class_average_score": round(class_average_score, 2),
            "engagement_rate": round((active_students / total_students * 100), 2) if total_students > 0 else 0,
            "average_assessments_per_student": round(total_assessments / total_students, 2) if total_students > 0 else 0,
            "average_activities_per_student": round(total_activities / total_students, 2) if total_students > 0 else 0
        }

    async def _get_recent_class_activities(self, students: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent activities across all students in the class"""
        
        all_activities = []
        
        for student in students:
            student_id = student["user_id"]
            profile = student.get("profile", {})
            student_name = profile.get("display_name", f"Student {student_id[:8]}")
            
            # Get recent assessments
            assessments = self.assessment_dao.get_user_assessments(student_id, limit=5)
            for assessment in assessments:
                all_activities.append({
                    "type": "assessment",
                    "student_id": student_id,
                    "student_name": student_name,
                    "activity": f"Completed assessment: {assessment.get('topic', 'Unknown')}",
                    "score": assessment.get("score"),
                    "timestamp": assessment.get("created_at"),
                    "details": assessment
                })
            
            # Get recent activities
            activities = self.content_dao.get_user_activities(student_id, limit=5)
            for activity in activities:
                all_activities.append({
                    "type": "activity",
                    "student_id": student_id,
                    "student_name": student_name,
                    "activity": f"Created {activity.get('activity_type', 'activity')}: {activity.get('title', 'Untitled')}",
                    "timestamp": activity.get("created_at"),
                    "details": activity
                })
            
            # Get recent lesson plans
            plans = self.planning_dao.get_user_lesson_plans(student_id, limit=3)
            for plan in plans:
                all_activities.append({
                    "type": "lesson_plan",
                    "student_id": student_id,
                    "student_name": student_name,
                    "activity": f"Created lesson plan: {plan.get('title', 'Untitled')}",
                    "timestamp": plan.get("created_at"),
                    "details": plan
                })
        
        # Sort by timestamp (most recent first) and limit
        all_activities.sort(key=lambda x: x.get("timestamp") or datetime.min, reverse=True)
        return all_activities[:limit]

    async def _generate_performance_summary(self, students: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate performance summary for the class"""
        
        if not students:
            return {"message": "No students to analyze"}
        
        high_performers = []
        struggling_students = []
        average_performers = []
        
        for student in students:
            student_id = student["user_id"]
            profile = student.get("profile", {})
            
            performance = self.assessment_dao.get_user_performance(student_id)
            if performance:
                avg_score = performance.get("average_score", 0)
                
                student_perf = {
                    "student_id": student_id,
                    "name": profile.get("display_name", f"Student {student_id[:8]}"),
                    "average_score": avg_score,
                    "total_assessments": performance.get("total_assessments", 0)
                }
                
                if avg_score >= 80:
                    high_performers.append(student_perf)
                elif avg_score < 60:
                    struggling_students.append(student_perf)
                else:
                    average_performers.append(student_perf)
        
        return {
            "high_performers": sorted(high_performers, key=lambda x: x["average_score"], reverse=True),
            "struggling_students": sorted(struggling_students, key=lambda x: x["average_score"]),
            "average_performers": sorted(average_performers, key=lambda x: x["average_score"], reverse=True),
            "performance_distribution": {
                "high": len(high_performers),
                "average": len(average_performers),
                "struggling": len(struggling_students)
            }
        }

    async def _generate_teacher_recommendations(self, dashboard_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate AI-powered recommendations for teachers"""
        
        try:
            # Prepare data for AI analysis
            class_analytics = dashboard_data.get("class_analytics", {})
            performance_summary = dashboard_data.get("performance_summary", {})
            
            prompt = f"""
            As an AI education assistant, analyze this class data and provide actionable recommendations for the teacher:
            
            Class Overview:
            - Total Students: {class_analytics.get('total_students', 0)}
            - Active Students: {class_analytics.get('active_students', 0)}
            - Class Average Score: {class_analytics.get('class_average_score', 0)}%
            - Engagement Rate: {class_analytics.get('engagement_rate', 0)}%
            
            Performance Distribution:
            - High Performers: {performance_summary.get('performance_distribution', {}).get('high', 0)}
            - Average Performers: {performance_summary.get('performance_distribution', {}).get('average', 0)}
            - Struggling Students: {performance_summary.get('performance_distribution', {}).get('struggling', 0)}
            
            Provide 3-5 specific, actionable recommendations in the following format:
            1. [Category] - [Specific Recommendation]
            
            Focus on: engagement strategies, differentiated instruction, assessment methods, and intervention strategies.
            """
            
            if self.ai_client:
                response = self.ai_client.generate_content(prompt)
                recommendations_text = response.text
                
                # Parse AI response into structured recommendations
                recommendations = []
                lines = recommendations_text.strip().split('\n')
                
                for line in lines:
                    if line.strip() and (line.strip().startswith(tuple('123456789'))):
                        # Parse recommendation
                        parts = line.split(' - ', 1)
                        if len(parts) == 2:
                            category = parts[0].strip('1234567890. []')
                            recommendation = parts[1].strip()
                            recommendations.append({
                                "category": category,
                                "recommendation": recommendation,
                                "priority": "high" if "struggling" in recommendation.lower() or "urgent" in recommendation.lower() else "medium"
                            })
                
                return recommendations
            
        except Exception as e:
            logger.error(f"Error generating AI recommendations: {e}")
        
        # Fallback recommendations based on data
        fallback_recommendations = []
        
        if class_analytics.get("engagement_rate", 0) < 50:
            fallback_recommendations.append({
                "category": "Engagement",
                "recommendation": "Consider implementing more interactive activities to increase student engagement",
                "priority": "high"
            })
        
        struggling_count = performance_summary.get('performance_distribution', {}).get('struggling', 0)
        if struggling_count > 0:
            fallback_recommendations.append({
                "category": "Intervention",
                "recommendation": f"Provide additional support for {struggling_count} struggling students through personalized learning plans",
                "priority": "high"
            })
        
        if class_analytics.get("class_average_score", 0) > 85:
            fallback_recommendations.append({
                "category": "Challenge",
                "recommendation": "Consider providing more challenging content for high-performing students",
                "priority": "medium"
            })
        
        return fallback_recommendations

    def _get_last_activity_date(self, assessments: List[Dict], activities: List[Dict], 
                              plans: List[Dict], conversations: List[Dict]) -> Optional[datetime]:
        """Get the most recent activity date across all activity types"""
        
        dates = []
        
        # Extract dates from all activity types
        for item in assessments + activities + plans + conversations:
            if "created_at" in item and item["created_at"]:
                try:
                    if isinstance(item["created_at"], str):
                        dates.append(datetime.fromisoformat(item["created_at"].replace('Z', '+00:00')))
                    else:
                        dates.append(item["created_at"])
                except:
                    continue
        
        return max(dates) if dates else None

# Create singleton instance
teacher_dashboard_service = TeacherDashboardService()
