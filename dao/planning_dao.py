"""
Planning Data Access Object (DAO)
Handles all Firestore operations related to lesson planning and schedules
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from google.cloud import firestore

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firestore_config import get_firestore_db

# Set up logging
logger = logging.getLogger(__name__)

class PlanningDAO:
    """Data Access Object for Planning-related Firestore operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        
    # Collections
    LESSON_PLANS_COLLECTION = "lesson_plans"
    LESSON_TEMPLATES_COLLECTION = "lesson_templates"
    USER_PLANNING_HISTORY_COLLECTION = "user_planning_history"
    CURRICULUM_STANDARDS_COLLECTION = "curriculum_standards"
    
    def save_lesson_plan(self, user_id: str, lesson_plan_data: Dict[str, Any]) -> Optional[str]:
        """
        Save lesson plan to Firestore
        
        Args:
            user_id: User identifier
            lesson_plan_data: Lesson plan data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            lesson_plan_ref = self.db.collection(self.LESSON_PLANS_COLLECTION).document()
            
            # Add metadata
            lesson_plan_data.update({
                "user_id": user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            lesson_plan_ref.set(lesson_plan_data)
            
            logger.info(f"Lesson plan saved successfully for user {user_id}, document ID: {lesson_plan_ref.id}")
            return lesson_plan_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save lesson plan for user {user_id}: {str(e)}")
            return None
    
    def get_lesson_plan(self, lesson_plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get lesson plan by ID
        
        Args:
            lesson_plan_id: Lesson plan document ID
            
        Returns:
            dict: Lesson plan data if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.LESSON_PLANS_COLLECTION).document(lesson_plan_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"Lesson plan {lesson_plan_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get lesson plan {lesson_plan_id}: {str(e)}")
            return None
    
    def get_user_lesson_plans(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all lesson plans for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of lesson plans to return
            
        Returns:
            list: List of lesson plan data
        """
        try:
            lesson_plans_ref = self.db.collection(self.LESSON_PLANS_COLLECTION)
            query = lesson_plans_ref.where("user_id", "==", user_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            
            lesson_plans = []
            for doc in query.stream():
                lesson_plan_data = doc.to_dict()
                lesson_plan_data["id"] = doc.id
                lesson_plans.append(lesson_plan_data)
            
            logger.info(f"Retrieved {len(lesson_plans)} lesson plans for user {user_id}")
            return lesson_plans
            
        except Exception as e:
            logger.error(f"Failed to get lesson plans for user {user_id}: {str(e)}")
            return []
    
    def update_lesson_plan(self, lesson_plan_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update lesson plan
        
        Args:
            lesson_plan_id: Lesson plan document ID
            update_data: Data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.LESSON_PLANS_COLLECTION).document(lesson_plan_id)
            
            # Add metadata
            update_data.update({
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.update(update_data)
            
            logger.info(f"Lesson plan {lesson_plan_id} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update lesson plan {lesson_plan_id}: {str(e)}")
            return False
    
    def save_lesson_template(self, template_data: Dict[str, Any]) -> Optional[str]:
        """
        Save lesson template to Firestore
        
        Args:
            template_data: Template data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            template_ref = self.db.collection(self.LESSON_TEMPLATES_COLLECTION).document()
            
            # Add metadata
            template_data.update({
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            template_ref.set(template_data)
            
            logger.info(f"Lesson template saved successfully, document ID: {template_ref.id}")
            return template_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save lesson template: {str(e)}")
            return None
    
    def get_lesson_templates(self, template_type: Optional[str] = None, grade_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get lesson templates with optional filters
        
        Args:
            template_type: Optional filter by template type
            grade_level: Optional filter by grade level
            
        Returns:
            list: List of template data
        """
        try:
            templates_ref = self.db.collection(self.LESSON_TEMPLATES_COLLECTION)
            query = templates_ref
            
            if template_type:
                query = query.where("type", "==", template_type)
            if grade_level:
                query = query.where("grade_level", "==", grade_level)
                
            templates = []
            for doc in query.stream():
                template_data = doc.to_dict()
                template_data["id"] = doc.id
                templates.append(template_data)
            
            logger.info(f"Retrieved {len(templates)} lesson templates")
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get lesson templates: {str(e)}")
            return []
    
    def update_planning_usage_stats(self, user_id: str, plan_type: str = "lesson_plan") -> bool:
        """
        Update planning usage statistics for a user
        
        Args:
            user_id: User identifier
            plan_type: Type of plan created
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PLANNING_HISTORY_COLLECTION).document(user_id)
            
            # Get existing data
            doc = doc_ref.get()
            if doc.exists:
                existing_data = doc.to_dict()
                
                # Update statistics
                total_plans = existing_data.get("total_plans_created", 0) + 1
                plan_type_count = existing_data.get(f"total_{plan_type}_created", 0) + 1
                
                usage_data = {
                    "total_plans_created": total_plans,
                    f"total_{plan_type}_created": plan_type_count,
                    f"last_{plan_type}_created": firestore.SERVER_TIMESTAMP,
                    "last_plan_created": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
            else:
                # First plan creation
                usage_data = {
                    "user_id": user_id,
                    "total_plans_created": 1,
                    f"total_{plan_type}_created": 1,
                    f"last_{plan_type}_created": firestore.SERVER_TIMESTAMP,
                    "last_plan_created": firestore.SERVER_TIMESTAMP,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
            
            doc_ref.set(usage_data, merge=True)
            
            logger.info(f"Planning usage statistics updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update planning usage statistics for user {user_id}: {str(e)}")
            return False
    
    def get_planning_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get planning analytics for specified time period
        
        Args:
            user_id: User identifier
            days: Number of days to analyze
            
        Returns:
            dict: Analytics data
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get lesson plans in date range
            lesson_plans_ref = self.db.collection(self.LESSON_PLANS_COLLECTION)
            query = lesson_plans_ref.where("user_id", "==", user_id).where("created_at", ">=", start_date).where("created_at", "<=", end_date)
            
            lesson_plans = []
            subjects = set()
            grade_levels = set()
            
            for doc in query.stream():
                lesson_plan_data = doc.to_dict()
                lesson_plans.append(lesson_plan_data)
                
                # Collect subjects and grade levels
                if "subject" in lesson_plan_data:
                    subjects.add(lesson_plan_data["subject"])
                if "grades" in lesson_plan_data:
                    if isinstance(lesson_plan_data["grades"], list):
                        grade_levels.update(lesson_plan_data["grades"])
                    else:
                        grade_levels.add(lesson_plan_data["grades"])
            
            analytics = {
                "user_id": user_id,
                "period": f"last_{days}_days",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_lesson_plans": len(lesson_plans),
                "unique_subjects": len(subjects),
                "unique_grade_levels": len(grade_levels),
                "subjects_taught": list(subjects),
                "grade_levels_taught": list(grade_levels)
            }
            
            logger.info(f"Planning analytics generated for user {user_id} (last {days} days)")
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to generate planning analytics for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "period": f"last_{days}_days",
                "error": str(e),
                "total_lesson_plans": 0
            }
    
    def save_curriculum_standard(self, standard_data: Dict[str, Any]) -> Optional[str]:
        """
        Save curriculum standard to Firestore
        
        Args:
            standard_data: Standard data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            standard_ref = self.db.collection(self.CURRICULUM_STANDARDS_COLLECTION).document()
            
            # Add metadata
            standard_data.update({
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            standard_ref.set(standard_data)
            
            logger.info(f"Curriculum standard saved successfully, document ID: {standard_ref.id}")
            return standard_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save curriculum standard: {str(e)}")
            return None
    
    def get_curriculum_standards(self, subject: Optional[str] = None, grade_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get curriculum standards with optional filters
        
        Args:
            subject: Optional filter by subject
            grade_level: Optional filter by grade level
            
        Returns:
            list: List of standard data
        """
        try:
            standards_ref = self.db.collection(self.CURRICULUM_STANDARDS_COLLECTION)
            query = standards_ref
            
            if subject:
                query = query.where("subject", "==", subject)
            if grade_level:
                query = query.where("grade_level", "==", grade_level)
                
            standards = []
            for doc in query.stream():
                standard_data = doc.to_dict()
                standard_data["id"] = doc.id
                standards.append(standard_data)
            
            logger.info(f"Retrieved {len(standards)} curriculum standards")
            return standards
            
        except Exception as e:
            logger.error(f"Failed to get curriculum standards: {str(e)}")
            return []
    
    def delete_lesson_plan(self, lesson_plan_id: str) -> bool:
        """
        Delete a lesson plan
        
        Args:
            lesson_plan_id: Lesson plan document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.LESSON_PLANS_COLLECTION).document(lesson_plan_id)
            doc_ref.delete()
            
            logger.info(f"Lesson plan {lesson_plan_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete lesson plan {lesson_plan_id}: {str(e)}")
            return False

# Create a singleton instance
planning_dao = PlanningDAO()
