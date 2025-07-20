"""
Assessment Data Access Object (DAO)
Handles all Firestore operations related to assessments and user performance
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from google.cloud import firestore

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from firestore_config import get_firestore_db, get_firestore_collection, get_document_reference

# Set up logging
logger = logging.getLogger(__name__)

class AssessmentDAO:
    """Data Access Object for Assessment-related Firestore operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        
    # Collections
    ASSESSMENTS_COLLECTION = "assessments"
    USERS_COLLECTION = "users"
    USER_PERFORMANCE_COLLECTION = "user_performance"
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists by trying to read from it
        
        Args:
            collection_name: Name of the collection to check
            
        Returns:
            bool: True if collection exists (has documents), False otherwise
        """
        try:
            # Try to get the first document from the collection
            collection_ref = self.db.collection(collection_name)
            docs = collection_ref.limit(1).stream()
            
            # Check if any documents exist
            for doc in docs:
                logger.info(f"Collection '{collection_name}' exists with documents")
                return True
            
            logger.info(f"Collection '{collection_name}' does not exist or is empty")
            return False
            
        except Exception as e:
            logger.error(f"Failed to check collection '{collection_name}': {str(e)}")
            return False
    
    def create_collection_if_not_exists(self, collection_name: str) -> bool:
        """
        Create a collection if it doesn't exist (by adding a temporary document)
        
        Args:
            collection_name: Name of the collection to create
            
        Returns:
            bool: True if collection was created/exists, False if error occurred
        """
        try:
            # Check if collection already exists
            if self.collection_exists(collection_name):
                logger.info(f"Collection '{collection_name}' already exists")
                return True
            
            # Firestore collections are created implicitly when you add documents
            # We'll add a temporary document to ensure the collection exists
            temp_doc_ref = self.db.collection(collection_name).document("_temp_init")
            temp_doc_ref.set({"initialized": True, "created_at": firestore.SERVER_TIMESTAMP})
            
            # Delete the temporary document
            temp_doc_ref.delete()
            
            logger.info(f"Collection '{collection_name}' initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {str(e)}")
            return False
    
    def check_assessments_collection(self) -> Dict[str, Any]:
        """
        Check the status of the assessments collection
        
        Returns:
            dict: Collection status information
        """
        try:
            collection_ref = self.db.collection(self.ASSESSMENTS_COLLECTION)
            
            # Count documents in the collection
            docs = list(collection_ref.stream())
            doc_count = len(docs)
            
            # Get collection info
            collection_info = {
                "collection_name": self.ASSESSMENTS_COLLECTION,
                "exists": doc_count > 0,
                "document_count": doc_count,
                "status": "exists_with_documents" if doc_count > 0 else "empty_or_nonexistent"
            }
            
            # If documents exist, get some sample info
            if doc_count > 0:
                # Get first and last documents
                first_doc = docs[0]
                last_doc = docs[-1]
                
                collection_info.update({
                    "first_document_id": first_doc.id,
                    "last_document_id": last_doc.id,
                    "sample_fields": list(first_doc.to_dict().keys()) if first_doc.to_dict() else []
                })
            
            logger.info(f"Assessments collection status: {collection_info}")
            return collection_info
            
        except Exception as e:
            error_info = {
                "collection_name": self.ASSESSMENTS_COLLECTION,
                "exists": False,
                "error": str(e),
                "status": "error_checking"
            }
            logger.error(f"Failed to check assessments collection: {str(e)}")
            return error_info
    
    def initialize_collections(self) -> Dict[str, bool]:
        """
        Initialize all required collections for the assessment module
        
        Returns:
            dict: Status of each collection initialization
        """
        collections = [
            self.ASSESSMENTS_COLLECTION,
            self.USER_PERFORMANCE_COLLECTION
        ]
        
        results = {}
        for collection_name in collections:
            results[collection_name] = self.create_collection_if_not_exists(collection_name)
        
        logger.info(f"Collection initialization results: {results}")
        return results
    
    def save_assessment(self, user_id: str, assessment_data: Dict[str, Any]) -> Optional[str]:
        """
        Save assessment to Firestore
        
        Args:
            user_id: User identifier
            assessment_data: Assessment data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            assessment_ref = self.db.collection(self.ASSESSMENTS_COLLECTION).document()
            
            # Add metadata
            assessment_data.update({
                "user_id": user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            assessment_ref.set(assessment_data)
            
            logger.info(f"Assessment saved successfully for user {user_id}, document ID: {assessment_ref.id}")
            return assessment_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save assessment for user {user_id}: {str(e)}")
            return None
    
    def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get assessment by ID
        
        Args:
            assessment_id: Assessment document ID
            
        Returns:
            dict: Assessment data if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.ASSESSMENTS_COLLECTION).document(assessment_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"Assessment {assessment_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get assessment {assessment_id}: {str(e)}")
            return None
    
    def get_user_assessments(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all assessments for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of assessments to return
            
        Returns:
            list: List of assessment data
        """
        try:
            assessments_ref = self.db.collection(self.ASSESSMENTS_COLLECTION)
            query = assessments_ref.where("user_id", "==", user_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            
            assessments = []
            for doc in query.stream():
                assessment_data = doc.to_dict()
                assessment_data["id"] = doc.id
                assessments.append(assessment_data)
            
            logger.info(f"Retrieved {len(assessments)} assessments for user {user_id}")
            return assessments
            
        except Exception as e:
            logger.error(f"Failed to get assessments for user {user_id}: {str(e)}")
            return []
    
    def save_user_performance(self, user_id: str, performance_data: Dict[str, Any]) -> bool:
        """
        Save or update user performance data
        
        Args:
            user_id: User identifier
            performance_data: Performance data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PERFORMANCE_COLLECTION).document(user_id)
            
            # Add metadata
            performance_data.update({
                "user_id": user_id,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            # Merge with existing data
            doc_ref.set(performance_data, merge=True)
            
            logger.info(f"Performance data saved successfully for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save performance data for user {user_id}: {str(e)}")
            return False
    
    def get_user_performance(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user performance data
        
        Args:
            user_id: User identifier
            
        Returns:
            dict: Performance data if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PERFORMANCE_COLLECTION).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            else:
                logger.info(f"No performance data found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get performance data for user {user_id}: {str(e)}")
            return None
    
    def update_user_performance_stats(self, user_id: str, correct_count: int, total_questions: int) -> bool:
        """
        Update user performance statistics
        
        Args:
            user_id: User identifier
            correct_count: Number of correct answers
            total_questions: Total number of questions
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.USER_PERFORMANCE_COLLECTION).document(user_id)
            
            # Get existing data
            doc = doc_ref.get()
            if doc.exists:
                existing_data = doc.to_dict()
                
                # Update cumulative statistics
                total_assessments = existing_data.get("total_assessments", 0) + 1
                total_correct = existing_data.get("total_correct", 0) + correct_count
                total_answered = existing_data.get("total_answered", 0) + total_questions
                
                average_score = (total_correct / total_answered) * 100 if total_answered > 0 else 0
                
                performance_data = {
                    "total_assessments": total_assessments,
                    "total_correct": total_correct,
                    "total_answered": total_answered,
                    "average_score": round(average_score, 2),
                    "last_assessment_score": round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0,
                    "last_assessment_date": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
            else:
                # First assessment
                score = round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0
                performance_data = {
                    "user_id": user_id,
                    "total_assessments": 1,
                    "total_correct": correct_count,
                    "total_answered": total_questions,
                    "average_score": score,
                    "last_assessment_score": score,
                    "last_assessment_date": firestore.SERVER_TIMESTAMP,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }
            
            doc_ref.set(performance_data, merge=True)
            
            logger.info(f"Performance statistics updated for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update performance statistics for user {user_id}: {str(e)}")
            return False
    
    def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get user assessment analytics for specified time period
        
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
            
            # Get assessments in date range
            assessments_ref = self.db.collection(self.ASSESSMENTS_COLLECTION)
            query = assessments_ref.where("user_id", "==", user_id).where("created_at", ">=", start_date).where("created_at", "<=", end_date)
            
            assessments = []
            total_score = 0
            total_questions = 0
            
            for doc in query.stream():
                assessment_data = doc.to_dict()
                assessments.append(assessment_data)
                
                # Calculate scores if available
                if "score" in assessment_data:
                    total_score += assessment_data["score"]
                if "total_questions" in assessment_data:
                    total_questions += assessment_data["total_questions"]
            
            # Calculate analytics
            average_score = (total_score / len(assessments)) if assessments else 0
            
            analytics = {
                "user_id": user_id,
                "period": f"last_{days}_days",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_assessments": len(assessments),
                "average_score": round(average_score, 2),
                "total_questions_answered": total_questions,
                "assessments": assessments
            }
            
            logger.info(f"Analytics generated for user {user_id} (last {days} days)")
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to generate analytics for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "period": f"last_{days}_days",
                "error": str(e),
                "total_assessments": 0,
                "average_score": 0.0
            }
    
    def delete_assessment(self, assessment_id: str) -> bool:
        """
        Delete an assessment
        
        Args:
            assessment_id: Assessment document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.ASSESSMENTS_COLLECTION).document(assessment_id)
            doc_ref.delete()
            
            logger.info(f"Assessment {assessment_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete assessment {assessment_id}: {str(e)}")
            return False
    
    def get_all_collections_status(self) -> Dict[str, Any]:
        """
        Get status of all collections used by AssessmentDAO
        
        Returns:
            dict: Status of all collections
        """
        collections_status = {}
        
        for collection_name in [self.ASSESSMENTS_COLLECTION, self.USER_PERFORMANCE_COLLECTION]:
            try:
                collection_ref = self.db.collection(collection_name)
                docs = list(collection_ref.stream())
                
                collections_status[collection_name] = {
                    "exists": len(docs) > 0,
                    "document_count": len(docs),
                    "status": "active" if len(docs) > 0 else "empty"
                }
                
            except Exception as e:
                collections_status[collection_name] = {
                    "exists": False,
                    "error": str(e),
                    "status": "error"
                }
        
        logger.info(f"All collections status: {collections_status}")
        return collections_status

# Create a singleton instance
assessment_dao = AssessmentDAO()
