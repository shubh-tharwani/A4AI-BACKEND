"""
Authentication Data Access Object (DAO)
Handles supplementary user data that complements Firebase Authentication
NOTE: Core auth data (email, password, tokens) remains in Firebase Auth
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

class AuthDAO:
    """
    Data Access Object for Authentication supplementary data
    
    NOTE: This DAO is for supplementary user data only.
    Core authentication (email, password, tokens) is handled by Firebase Auth.
    """
    
    def __init__(self):
        self.db = get_firestore_db()
        
    # Collections for supplementary auth data
    USER_PROFILES_COLLECTION = "user_profiles"
    USER_LOGIN_HISTORY_COLLECTION = "user_login_history" 
    USER_ROLES_COLLECTION = "user_roles"
    USER_PREFERENCES_COLLECTION = "user_preferences"
    
    def create_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        Create supplementary user profile data
        
        Args:
            user_id: Firebase UID
            profile_data: Additional profile information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PROFILES_COLLECTION).document(user_id)
            
            # Add metadata
            profile_data.update({
                "firebase_uid": user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.set(profile_data)
            
            logger.info(f"User profile created for Firebase UID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user profile for {user_id}: {str(e)}")
            return False
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get supplementary user profile data
        
        Args:
            user_id: Firebase UID
            
        Returns:
            dict: Profile data if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PROFILES_COLLECTION).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user profile for {user_id}: {str(e)}")
            return None
    
    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update supplementary user profile data
        
        Args:
            user_id: Firebase UID
            update_data: Data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PROFILES_COLLECTION).document(user_id)
            
            update_data.update({
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.update(update_data)
            
            logger.info(f"User profile updated for Firebase UID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user profile for {user_id}: {str(e)}")
            return False
    
    def log_user_login(self, user_id: str, login_data: Dict[str, Any]) -> Optional[str]:
        """
        Log user login for analytics and security
        
        Args:
            user_id: Firebase UID
            login_data: Login information (IP, device, etc.)
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            login_ref = self.db.collection(self.USER_LOGIN_HISTORY_COLLECTION).document()
            
            login_data.update({
                "firebase_uid": user_id,
                "login_time": firestore.SERVER_TIMESTAMP,
                "created_at": firestore.SERVER_TIMESTAMP
            })
            
            login_ref.set(login_data)
            
            logger.info(f"Login logged for Firebase UID: {user_id}")
            return login_ref.id
            
        except Exception as e:
            logger.error(f"Failed to log login for {user_id}: {str(e)}")
            return None
    
    def get_user_login_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get user login history for security/analytics
        
        Args:
            user_id: Firebase UID
            limit: Maximum number of login records to return
            
        Returns:
            list: List of login records
        """
        try:
            logins_ref = self.db.collection(self.USER_LOGIN_HISTORY_COLLECTION)
            query = logins_ref.where("firebase_uid", "==", user_id).order_by("login_time", direction=firestore.Query.DESCENDING).limit(limit)
            
            logins = []
            for doc in query.stream():
                login_data = doc.to_dict()
                login_data["id"] = doc.id
                logins.append(login_data)
            
            return logins
            
        except Exception as e:
            logger.error(f"Failed to get login history for {user_id}: {str(e)}")
            return []
    
    def save_user_role_preferences(self, user_id: str, role_data: Dict[str, Any]) -> bool:
        """
        Save role-specific preferences and settings
        
        Args:
            user_id: Firebase UID
            role_data: Role-specific settings
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_ROLES_COLLECTION).document(user_id)
            
            role_data.update({
                "firebase_uid": user_id,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.set(role_data, merge=True)
            
            logger.info(f"Role preferences saved for Firebase UID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save role preferences for {user_id}: {str(e)}")
            return False
    
    def get_user_role_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get role-specific preferences and settings
        
        Args:
            user_id: Firebase UID
            
        Returns:
            dict: Role preferences if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_ROLES_COLLECTION).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get role preferences for {user_id}: {str(e)}")
            return None
    
    def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Save user application preferences
        
        Args:
            user_id: Firebase UID
            preferences: User preferences (theme, notifications, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PREFERENCES_COLLECTION).document(user_id)
            
            preferences.update({
                "firebase_uid": user_id,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.set(preferences, merge=True)
            
            logger.info(f"User preferences saved for Firebase UID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save preferences for {user_id}: {str(e)}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user application preferences
        
        Args:
            user_id: Firebase UID
            
        Returns:
            dict: User preferences if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PREFERENCES_COLLECTION).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get preferences for {user_id}: {str(e)}")
            return None
    
    def get_user_complete_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete user profile combining all supplementary data
        
        Args:
            user_id: Firebase UID
            
        Returns:
            dict: Complete profile data
        """
        try:
            profile = {
                "firebase_uid": user_id,
                "profile": self.get_user_profile(user_id),
                "role_preferences": self.get_user_role_preferences(user_id),
                "preferences": self.get_user_preferences(user_id),
                "recent_logins": self.get_user_login_history(user_id, limit=5)
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to get complete profile for {user_id}: {str(e)}")
            return {
                "firebase_uid": user_id,
                "error": str(e)
            }
    
    def delete_user_supplementary_data(self, user_id: str) -> bool:
        """
        Delete all supplementary user data (GDPR compliance)
        NOTE: This does NOT delete the Firebase Auth user - that must be done separately
        
        Args:
            user_id: Firebase UID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            collections_to_clean = [
                self.USER_PROFILES_COLLECTION,
                self.USER_ROLES_COLLECTION,
                self.USER_PREFERENCES_COLLECTION
            ]
            
            for collection_name in collections_to_clean:
                try:
                    doc_ref = self.db.collection(collection_name).document(user_id)
                    doc = doc_ref.get()
                    if doc.exists:
                        doc_ref.delete()
                        logger.info(f"Deleted user data from {collection_name} for Firebase UID: {user_id}")
                except Exception as e:
                    logger.error(f"Failed to delete from {collection_name} for {user_id}: {str(e)}")
            
            # Delete login history
            try:
                login_query = self.db.collection(self.USER_LOGIN_HISTORY_COLLECTION).where("firebase_uid", "==", user_id)
                login_docs = login_query.stream()
                
                for doc in login_docs:
                    doc.reference.delete()
                    
                logger.info(f"Deleted login history for Firebase UID: {user_id}")
            except Exception as e:
                logger.error(f"Failed to delete login history for {user_id}: {str(e)}")
            
            logger.info(f"Supplementary user data deletion completed for Firebase UID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete supplementary user data for {user_id}: {str(e)}")
            return False

# Create a singleton instance
auth_dao = AuthDAO()
