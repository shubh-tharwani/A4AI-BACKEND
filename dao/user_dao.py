"""
User Data Access Object (DAO)
Handles all Firestore operations related to user management and profiles
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from google.cloud import firestore

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firestore_config import get_firestore_db

# Set up logging
logger = logging.getLogger(__name__)

class UserDAO:
    """Data Access Object for User-related Firestore operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        
    # Collections
    USERS_COLLECTION = "users"
    USER_PROFILES_COLLECTION = "user_profiles"
    USER_PREFERENCES_COLLECTION = "user_preferences"
    USER_SESSIONS_COLLECTION = "user_sessions"
    
    def create_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        Create user profile in Firestore
        
        Args:
            user_id: User identifier
            profile_data: Profile data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PROFILES_COLLECTION).document(user_id)
            
            # Add metadata
            profile_data.update({
                "user_id": user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.set(profile_data)
            
            logger.info(f"User profile created successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user profile for user {user_id}: {str(e)}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile
        
        Args:
            user_id: User identifier
            
        Returns:
            dict: Profile data if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PROFILES_COLLECTION).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.info(f"No profile found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user profile for user {user_id}: {str(e)}")
            return None
    
    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update user profile
        
        Args:
            user_id: User identifier
            update_data: Data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PROFILES_COLLECTION).document(user_id)
            
            # Add metadata
            update_data.update({
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.update(update_data)
            
            logger.info(f"User profile updated successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user profile for user {user_id}: {str(e)}")
            return False
    
    def save_user_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> bool:
        """
        Save user preferences
        
        Args:
            user_id: User identifier
            preferences_data: Preferences data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PREFERENCES_COLLECTION).document(user_id)
            
            # Add metadata
            preferences_data.update({
                "user_id": user_id,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.set(preferences_data, merge=True)
            
            logger.info(f"User preferences saved successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save user preferences for user {user_id}: {str(e)}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user preferences
        
        Args:
            user_id: User identifier
            
        Returns:
            dict: Preferences data if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PREFERENCES_COLLECTION).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.info(f"No preferences found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user preferences for user {user_id}: {str(e)}")
            return None
    
    def log_user_session(self, user_id: str, session_data: Dict[str, Any]) -> Optional[str]:
        """
        Log user session
        
        Args:
            user_id: User identifier
            session_data: Session data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            session_ref = self.db.collection(self.USER_SESSIONS_COLLECTION).document()
            
            # Add metadata
            session_data.update({
                "user_id": user_id,
                "session_start": firestore.SERVER_TIMESTAMP,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            
            session_ref.set(session_data)
            
            logger.info(f"User session logged successfully for user {user_id}, document ID: {session_ref.id}")
            return session_ref.id
            
        except Exception as e:
            logger.error(f"Failed to log user session for user {user_id}: {str(e)}")
            return None
    
    def update_session_end(self, session_id: str) -> bool:
        """
        Update session end time
        
        Args:
            session_id: Session document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_SESSIONS_COLLECTION).document(session_id)
            
            doc_ref.update({
                "session_end": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Session end time updated for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session end time for session {session_id}: {str(e)}")
            return False
    
    def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get user sessions
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            
        Returns:
            list: List of session data
        """
        try:
            sessions_ref = self.db.collection(self.USER_SESSIONS_COLLECTION)
            query = sessions_ref.where("user_id", "==", user_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            
            sessions = []
            for doc in query.stream():
                session_data = doc.to_dict()
                session_data["id"] = doc.id
                sessions.append(session_data)
            
            logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions for user {user_id}: {str(e)}")
            return []
    
    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all user data (GDPR compliance)
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            collections_to_clean = [
                self.USER_PROFILES_COLLECTION,
                self.USER_PREFERENCES_COLLECTION,
                self.USER_SESSIONS_COLLECTION
            ]
            
            for collection_name in collections_to_clean:
                try:
                    doc_ref = self.db.collection(collection_name).document(user_id)
                    doc = doc_ref.get()
                    if doc.exists:
                        doc_ref.delete()
                        logger.info(f"Deleted user data from {collection_name} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to delete from {collection_name} for user {user_id}: {str(e)}")
            
            # Also delete user-specific documents from other collections
            collections_with_user_field = [
                "assessments",
                "lesson_plans", 
                "activities",
                "visual_aids",
                "voice_conversations",
                "user_performance",
                "user_content_history",
                "user_planning_history"
            ]
            
            for collection_name in collections_with_user_field:
                try:
                    query = self.db.collection(collection_name).where("user_id", "==", user_id)
                    docs = query.stream()
                    
                    for doc in docs:
                        doc.reference.delete()
                        
                    logger.info(f"Deleted user documents from {collection_name} for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to delete user documents from {collection_name} for user {user_id}: {str(e)}")
            
            logger.info(f"User data deletion completed for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user data for user {user_id}: {str(e)}")
            return False
    
    def get_user_activity_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive user activity summary
        
        Args:
            user_id: User identifier
            
        Returns:
            dict: Activity summary data
        """
        try:
            summary = {
                "user_id": user_id,
                "profile_exists": False,
                "total_assessments": 0,
                "total_lesson_plans": 0,
                "total_activities": 0,
                "total_visual_aids": 0,
                "total_voice_conversations": 0,
                "total_sessions": 0
            }
            
            # Check if profile exists
            profile_doc = self.db.collection(self.USER_PROFILES_COLLECTION).document(user_id).get()
            summary["profile_exists"] = profile_doc.exists
            
            # Count documents in each collection
            collections_to_count = {
                "assessments": "total_assessments",
                "lesson_plans": "total_lesson_plans",
                "activities": "total_activities", 
                "visual_aids": "total_visual_aids",
                "voice_conversations": "total_voice_conversations"
            }
            
            for collection_name, summary_key in collections_to_count.items():
                try:
                    query = self.db.collection(collection_name).where("user_id", "==", user_id)
                    docs = query.stream()
                    summary[summary_key] = len(list(docs))
                except Exception as e:
                    logger.error(f"Failed to count documents in {collection_name} for user {user_id}: {str(e)}")
                    summary[summary_key] = 0
            
            # Count sessions
            try:
                sessions_query = self.db.collection(self.USER_SESSIONS_COLLECTION).where("user_id", "==", user_id)
                sessions_docs = sessions_query.stream()
                summary["total_sessions"] = len(list(sessions_docs))
            except Exception as e:
                logger.error(f"Failed to count sessions for user {user_id}: {str(e)}")
                summary["total_sessions"] = 0
            
            logger.info(f"User activity summary generated for user {user_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate user activity summary for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "error": str(e)
            }

# Create a singleton instance
user_dao = UserDAO()
