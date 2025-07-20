"""
Personalization Data Access Object (DAO)
Handles database operations for personalization and dashboard functionality
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from firestore_config import get_firestore_db
from utils.dao_error_handler import handle_dao_errors

logger = logging.getLogger(__name__)

class PersonalizationDAO:
    """Data Access Object for personalization-related operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        self.performance_collection = "user_performance"
        self.recommendations_collection = "recommendations"
        self.users_collection = "users"
    
    @handle_dao_errors("get_user_performance")
    def get_user_performance(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user performance data from database
        
        Args:
            user_id (str): User ID
            
        Returns:
            Dict[str, Any]: Performance data or None if not found
        """
        try:
            performance_ref = self.db.collection(self.performance_collection).document(user_id)
            performance_doc = performance_ref.get()
            
            if not performance_doc.exists:
                logger.warning(f"No performance data found for user: {user_id}")
                return None
                
            data = performance_doc.to_dict()
            logger.info(f"Retrieved performance data for user: {user_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error getting user performance for {user_id}: {e}")
            raise
    
    @handle_dao_errors("save_recommendations")
    def save_recommendations(self, user_id: str, recommendations: Dict[str, Any]) -> str:
        """
        Save personalized recommendations to database
        
        Args:
            user_id (str): User ID
            recommendations (Dict[str, Any]): Recommendation data
            
        Returns:
            str: Document ID of saved recommendations
        """
        try:
            # Add timestamp to recommendations
            recommendations_data = {
                **recommendations,
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Save to recommendations collection
            doc_ref = self.db.collection(self.recommendations_collection).document(user_id)
            doc_ref.set(recommendations_data)
            
            logger.info(f"Saved recommendations for user: {user_id}")
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Error saving recommendations for {user_id}: {e}")
            raise
    
    @handle_dao_errors("get_user_recommendations")
    def get_user_recommendations(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get existing recommendations for a user
        
        Args:
            user_id (str): User ID
            
        Returns:
            Dict[str, Any]: Recommendations data or None if not found
        """
        try:
            doc_ref = self.db.collection(self.recommendations_collection).document(user_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.info(f"No existing recommendations found for user: {user_id}")
                return None
                
            data = doc.to_dict()
            logger.info(f"Retrieved existing recommendations for user: {user_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error getting recommendations for {user_id}: {e}")
            raise
    
    @handle_dao_errors("get_class_performance")
    def get_class_performance(self, class_id: str) -> List[Dict[str, Any]]:
        """
        Get performance data for all students in a class
        
        Args:
            class_id (str): Class ID
            
        Returns:
            List[Dict[str, Any]]: List of student performance data
        """
        try:
            # Query all students in the class
            students_query = self.db.collection(self.performance_collection).where("class_id", "==", class_id)
            students = students_query.stream()
            
            class_data = []
            for student_doc in students:
                if student_doc.exists:
                    student_data = student_doc.to_dict()
                    student_data['user_id'] = student_doc.id
                    class_data.append(student_data)
            
            logger.info(f"Retrieved performance data for {len(class_data)} students in class: {class_id}")
            return class_data
            
        except Exception as e:
            logger.error(f"Error getting class performance for {class_id}: {e}")
            raise
    
    @handle_dao_errors("get_user_profile")
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user profile information
        
        Args:
            user_id (str): User ID
            
        Returns:
            Dict[str, Any]: User profile data or None if not found
        """
        try:
            user_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                logger.warning(f"No profile found for user: {user_id}")
                return None
                
            data = user_doc.to_dict()
            logger.info(f"Retrieved profile for user: {user_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            raise

# Singleton instance
personalization_dao = PersonalizationDAO()
