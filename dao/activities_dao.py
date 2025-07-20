"""
Activities Data Access Object (DAO)
Handles database operations for interactive activities, badges, and AR/VR content
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from firestore_config import get_firestore_db
from utils.dao_error_handler import handle_dao_errors

logger = logging.getLogger(__name__)

class ActivitiesDAO:
    """Data Access Object for activities-related operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        self.activities_collection = "activities"
        self.user_badges_collection = "user_badges"
        self.ar_scenes_collection = "ar_scenes"
        self.stories_collection = "interactive_stories"
    
    @handle_dao_errors("save_activity")
    def save_activity(self, activity_data: Dict[str, Any]) -> str:
        """
        Save activity data to database
        
        Args:
            activity_data (Dict[str, Any]): Activity data to save
            
        Returns:
            str: Document ID of saved activity
        """
        try:
            # Generate unique activity ID
            activity_id = str(uuid.uuid4())
            
            # Add metadata
            activity_data_with_meta = {
                **activity_data,
                "activity_id": activity_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Save to database
            doc_ref = self.db.collection(self.activities_collection).document(activity_id)
            doc_ref.set(activity_data_with_meta)
            
            logger.info(f"Saved activity with ID: {activity_id}")
            return activity_id
            
        except Exception as e:
            logger.error(f"Error saving activity: {e}")
            raise
    
    @handle_dao_errors("save_interactive_story")
    def save_interactive_story(self, story_data: Dict[str, Any]) -> str:
        """
        Save interactive story to database
        
        Args:
            story_data (Dict[str, Any]): Story data to save
            
        Returns:
            str: Document ID of saved story
        """
        try:
            story_id = str(uuid.uuid4())
            
            story_data_with_meta = {
                **story_data,
                "story_id": story_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "type": "interactive_story"
            }
            
            doc_ref = self.db.collection(self.stories_collection).document(story_id)
            doc_ref.set(story_data_with_meta)
            
            logger.info(f"Saved interactive story with ID: {story_id}")
            return story_id
            
        except Exception as e:
            logger.error(f"Error saving interactive story: {e}")
            raise
    
    @handle_dao_errors("save_ar_scene")
    def save_ar_scene(self, scene_data: Dict[str, Any]) -> str:
        """
        Save AR/VR scene data to database
        
        Args:
            scene_data (Dict[str, Any]): AR scene data to save
            
        Returns:
            str: Document ID of saved scene
        """
        try:
            scene_id = str(uuid.uuid4())
            
            scene_data_with_meta = {
                **scene_data,
                "scene_id": scene_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "type": "ar_scene"
            }
            
            doc_ref = self.db.collection(self.ar_scenes_collection).document(scene_id)
            doc_ref.set(scene_data_with_meta)
            
            logger.info(f"Saved AR scene with ID: {scene_id}")
            return scene_id
            
        except Exception as e:
            logger.error(f"Error saving AR scene: {e}")
            raise
    
    @handle_dao_errors("assign_user_badge")
    def assign_user_badge(self, user_id: str, badge_data: Dict[str, Any]) -> str:
        """
        Assign a badge to a user
        
        Args:
            user_id (str): User ID
            badge_data (Dict[str, Any]): Badge data to assign
            
        Returns:
            str: Document ID of assigned badge
        """
        try:
            # Add metadata
            badge_data_with_meta = {
                **badge_data,
                "user_id": user_id,
                "assigned_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Save to user's badges subcollection
            badges_collection = self.db.collection(self.user_badges_collection).document(user_id).collection("badges")
            doc_ref = badges_collection.add(badge_data_with_meta)
            
            logger.info(f"Assigned badge '{badge_data.get('badge', 'unknown')}' to user: {user_id}")
            return doc_ref[1].id
            
        except Exception as e:
            logger.error(f"Error assigning badge to user {user_id}: {e}")
            raise
    
    @handle_dao_errors("get_user_badges")
    def get_user_badges(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all badges for a user
        
        Args:
            user_id (str): User ID
            
        Returns:
            List[Dict[str, Any]]: List of user badges
        """
        try:
            badges_collection = self.db.collection(self.user_badges_collection).document(user_id).collection("badges")
            badges_query = badges_collection.where("status", "==", "active").stream()
            
            badges = []
            for badge_doc in badges_query:
                if badge_doc.exists:
                    badge_data = badge_doc.to_dict()
                    badge_data['badge_id'] = badge_doc.id
                    badges.append(badge_data)
            
            logger.info(f"Retrieved {len(badges)} badges for user: {user_id}")
            return badges
            
        except Exception as e:
            logger.error(f"Error getting badges for user {user_id}: {e}")
            raise
    
    @handle_dao_errors("get_activity")
    def get_activity(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get activity by ID
        
        Args:
            activity_id (str): Activity ID
            
        Returns:
            Dict[str, Any]: Activity data or None if not found
        """
        try:
            doc_ref = self.db.collection(self.activities_collection).document(activity_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"Activity not found: {activity_id}")
                return None
                
            data = doc.to_dict()
            logger.info(f"Retrieved activity: {activity_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error getting activity {activity_id}: {e}")
            raise
    
    @handle_dao_errors("get_user_activities")
    def get_user_activities(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent activities for a user
        
        Args:
            user_id (str): User ID
            limit (int): Maximum number of activities to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of user activities
        """
        try:
            # Query activities with user_id field (if stored) or get all recent activities
            activities_query = (self.db.collection(self.activities_collection)
                              .where("status", "==", "active")
                              .order_by("created_at", direction="DESCENDING")
                              .limit(limit))
            
            activities = []
            for activity_doc in activities_query.stream():
                if activity_doc.exists:
                    activity_data = activity_doc.to_dict()
                    activity_data['activity_id'] = activity_doc.id
                    activities.append(activity_data)
            
            logger.info(f"Retrieved {len(activities)} activities for user: {user_id}")
            return activities
            
        except Exception as e:
            logger.error(f"Error getting activities for user {user_id}: {e}")
            raise

# Singleton instance
activities_dao = ActivitiesDAO()
