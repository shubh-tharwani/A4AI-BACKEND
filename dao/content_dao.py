"""
Content Data Access Object (DAO)
Handles all Firestore operations related to content generation and activities
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

class ContentDAO:
    """Data Access Object for Content-related Firestore operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        
    # Collections
    ACTIVITIES_COLLECTION = "activities"
    VISUAL_AIDS_COLLECTION = "visual_aids"
    CONTENT_TEMPLATES_COLLECTION = "content_templates"
    USER_CONTENT_HISTORY_COLLECTION = "user_content_history"
    
    def save_activity(self, user_id: str, activity_data: Dict[str, Any]) -> Optional[str]:
        """
        Save generated activity to Firestore
        
        Args:
            user_id: User identifier
            activity_data: Activity data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            activity_ref = self.db.collection(self.ACTIVITIES_COLLECTION).document()
            
            # Add metadata
            activity_data.update({
                "user_id": user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            activity_ref.set(activity_data)
            
            logger.info(f"Activity saved successfully for user {user_id}, document ID: {activity_ref.id}")
            return activity_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save activity for user {user_id}: {str(e)}")
            return None
    
    def save_visual_aid(self, user_id: str, visual_aid_data: Dict[str, Any]) -> Optional[str]:
        """
        Save generated visual aid to Firestore
        
        Args:
            user_id: User identifier
            visual_aid_data: Visual aid data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            visual_aid_ref = self.db.collection(self.VISUAL_AIDS_COLLECTION).document()
            
            # Add metadata
            visual_aid_data.update({
                "user_id": user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            visual_aid_ref.set(visual_aid_data)
            
            logger.info(f"Visual aid saved successfully for user {user_id}, document ID: {visual_aid_ref.id}")
            return visual_aid_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save visual aid for user {user_id}: {str(e)}")
            return None
    
    def get_user_activities(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all activities for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of activities to return
            
        Returns:
            list: List of activity data
        """
        try:
            activities_ref = self.db.collection(self.ACTIVITIES_COLLECTION)
            query = activities_ref.where("user_id", "==", user_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            
            activities = []
            for doc in query.stream():
                activity_data = doc.to_dict()
                activity_data["id"] = doc.id
                activities.append(activity_data)
            
            logger.info(f"Retrieved {len(activities)} activities for user {user_id}")
            return activities
            
        except Exception as e:
            logger.error(f"Failed to get activities for user {user_id}: {str(e)}")
            return []
    
    def get_user_visual_aids(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all visual aids for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of visual aids to return
            
        Returns:
            list: List of visual aid data
        """
        try:
            visual_aids_ref = self.db.collection(self.VISUAL_AIDS_COLLECTION)
            query = visual_aids_ref.where("user_id", "==", user_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            
            visual_aids = []
            for doc in query.stream():
                visual_aid_data = doc.to_dict()
                visual_aid_data["id"] = doc.id
                visual_aids.append(visual_aid_data)
            
            logger.info(f"Retrieved {len(visual_aids)} visual aids for user {user_id}")
            return visual_aids
            
        except Exception as e:
            logger.error(f"Failed to get visual aids for user {user_id}: {str(e)}")
            return []
    
    def save_content_template(self, template_data: Dict[str, Any]) -> Optional[str]:
        """
        Save content template to Firestore
        
        Args:
            template_data: Template data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            template_ref = self.db.collection(self.CONTENT_TEMPLATES_COLLECTION).document()
            
            # Add metadata
            template_data.update({
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            template_ref.set(template_data)
            
            logger.info(f"Content template saved successfully, document ID: {template_ref.id}")
            return template_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save content template: {str(e)}")
            return None
    
    def get_content_templates(self, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get content templates
        
        Args:
            template_type: Optional filter by template type
            
        Returns:
            list: List of template data
        """
        try:
            templates_ref = self.db.collection(self.CONTENT_TEMPLATES_COLLECTION)
            
            if template_type:
                query = templates_ref.where("type", "==", template_type)
            else:
                query = templates_ref
                
            templates = []
            for doc in query.stream():
                template_data = doc.to_dict()
                template_data["id"] = doc.id
                templates.append(template_data)
            
            logger.info(f"Retrieved {len(templates)} content templates")
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get content templates: {str(e)}")
            return []
    
    def update_content_usage_stats(self, user_id: str, content_type: str) -> bool:
        """
        Update content usage statistics for a user
        
        Args:
            user_id: User identifier
            content_type: Type of content (activity, visual_aid)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_CONTENT_HISTORY_COLLECTION).document(user_id)
            
            # Get existing data
            doc = doc_ref.get()
            if doc.exists:
                existing_data = doc.to_dict()
                
                # Update statistics
                total_content = existing_data.get("total_content_generated", 0) + 1
                content_type_count = existing_data.get(f"total_{content_type}_generated", 0) + 1
                
                usage_data = {
                    "total_content_generated": total_content,
                    f"total_{content_type}_generated": content_type_count,
                    f"last_{content_type}_generated": firestore.SERVER_TIMESTAMP,
                    "last_content_generated": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
            else:
                # First content generation
                usage_data = {
                    "user_id": user_id,
                    "total_content_generated": 1,
                    f"total_{content_type}_generated": 1,
                    f"last_{content_type}_generated": firestore.SERVER_TIMESTAMP,
                    "last_content_generated": firestore.SERVER_TIMESTAMP,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
            
            doc_ref.set(usage_data, merge=True)
            
            logger.info(f"Content usage statistics updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update content usage statistics for user {user_id}: {str(e)}")
            return False
    
    def get_content_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get content generation analytics for specified time period
        
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
            
            # Get activities in date range
            activities_ref = self.db.collection(self.ACTIVITIES_COLLECTION)
            activities_query = activities_ref.where("user_id", "==", user_id).where("created_at", ">=", start_date).where("created_at", "<=", end_date)
            
            # Get visual aids in date range
            visual_aids_ref = self.db.collection(self.VISUAL_AIDS_COLLECTION)
            visual_aids_query = visual_aids_ref.where("user_id", "==", user_id).where("created_at", ">=", start_date).where("created_at", "<=", end_date)
            
            activities_count = len([doc for doc in activities_query.stream()])
            visual_aids_count = len([doc for doc in visual_aids_query.stream()])
            
            analytics = {
                "user_id": user_id,
                "period": f"last_{days}_days",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_content_generated": activities_count + visual_aids_count,
                "activities_generated": activities_count,
                "visual_aids_generated": visual_aids_count
            }
            
            logger.info(f"Content analytics generated for user {user_id} (last {days} days)")
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to generate content analytics for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "period": f"last_{days}_days",
                "error": str(e),
                "total_content_generated": 0
            }
    
    def delete_activity(self, activity_id: str) -> bool:
        """
        Delete an activity
        
        Args:
            activity_id: Activity document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.ACTIVITIES_COLLECTION).document(activity_id)
            doc_ref.delete()
            
            logger.info(f"Activity {activity_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete activity {activity_id}: {str(e)}")
            return False
    
    def delete_visual_aid(self, visual_aid_id: str) -> bool:
        """
        Delete a visual aid
        
        Args:
            visual_aid_id: Visual aid document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.VISUAL_AIDS_COLLECTION).document(visual_aid_id)
            doc_ref.delete()
            
            logger.info(f"Visual aid {visual_aid_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete visual aid {visual_aid_id}: {str(e)}")
            return False

# Create a singleton instance
content_dao = ContentDAO()
