"""
Visual Aid Data Access Object (DAO)
Handles database operations for visual aids, images, and generated content
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from firestore_config import get_firestore_db
from utils.dao_error_handler import handle_dao_errors
from google.cloud import firestore

logger = logging.getLogger(__name__)

class VisualAidDAO:
    """Data Access Object for visual aid-related operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        self.visual_aids_collection = "visual_aids"
        self.user_visual_aids_collection = "user_visual_aids"
        self.templates_collection = "visual_aid_templates"
    
    @handle_dao_errors("save_visual_aid")
    def save_visual_aid(self, visual_aid_data: Dict[str, Any]) -> str:
        """
        Save visual aid data to database
        
        Args:
            visual_aid_data (Dict[str, Any]): Visual aid data to save
            
        Returns:
            str: Document ID of saved visual aid
        """
        try:
            # Generate unique visual aid ID
            visual_aid_id = str(uuid.uuid4())
            
            # Add metadata
            visual_aid_data_with_meta = {
                **visual_aid_data,
                "visual_aid_id": visual_aid_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Save to database
            doc_ref = self.db.collection(self.visual_aids_collection).document(visual_aid_id)
            doc_ref.set(visual_aid_data_with_meta)
            
            logger.info(f"Saved visual aid with ID: {visual_aid_id}")
            return visual_aid_id
            
        except Exception as e:
            logger.error(f"Error saving visual aid: {e}")
            raise
    
    @handle_dao_errors("get_visual_aid")
    def get_visual_aid(self, visual_aid_id: str) -> Optional[Dict[str, Any]]:
        """
        Get visual aid by ID
        
        Args:
            visual_aid_id (str): Visual aid ID
            
        Returns:
            Optional[Dict[str, Any]]: Visual aid data or None if not found
        """
        try:
            doc_ref = self.db.collection(self.visual_aids_collection).document(visual_aid_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"Visual aid not found: {visual_aid_id}")
                return None
                
            data = doc.to_dict()
            logger.info(f"Retrieved visual aid: {visual_aid_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error getting visual aid {visual_aid_id}: {e}")
            raise
    
    @handle_dao_errors("get_user_visual_aids")
    def get_user_visual_aids(self, user_id: str, limit: int = 10, asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get visual aids for a user
        
        Args:
            user_id (str): User ID
            limit (int): Maximum number of visual aids to retrieve
            asset_type (str, optional): Filter by asset type
            
        Returns:
            List[Dict[str, Any]]: List of user visual aids
        """
        try:
            query = (self.db.collection(self.visual_aids_collection)
                    .where("user_id", "==", user_id)
                    .where("status", "==", "active")
                    .order_by("created_at", direction="DESCENDING")
                    .limit(limit))
            
            # Add asset type filter if specified
            if asset_type:
                query = query.where("asset_type", "==", asset_type)
            
            visual_aids = []
            for doc in query.stream():
                if doc.exists:
                    visual_aid_data = doc.to_dict()
                    visual_aid_data['visual_aid_id'] = doc.id
                    visual_aids.append(visual_aid_data)
            
            logger.info(f"Retrieved {len(visual_aids)} visual aids for user: {user_id}")
            return visual_aids
            
        except Exception as e:
            logger.error(f"Error getting visual aids for user {user_id}: {e}")
            raise
    
    @handle_dao_errors("search_visual_aids")
    def search_visual_aids(self, topic: str, asset_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search visual aids by topic
        
        Args:
            topic (str): Topic to search for
            asset_type (str, optional): Filter by asset type
            limit (int): Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: List of matching visual aids
        """
        try:
            # Note: In a production system, you'd want to implement full-text search
            # For now, we'll do a simple topic match
            query = (self.db.collection(self.visual_aids_collection)
                    .where("status", "==", "active")
                    .where("topic", ">=", topic.lower())
                    .where("topic", "<=", topic.lower() + "\uf8ff")
                    .limit(limit))
            
            if asset_type:
                query = query.where("asset_type", "==", asset_type)
            
            visual_aids = []
            for doc in query.stream():
                if doc.exists:
                    visual_aid_data = doc.to_dict()
                    visual_aid_data['visual_aid_id'] = doc.id
                    visual_aids.append(visual_aid_data)
            
            logger.info(f"Found {len(visual_aids)} visual aids for topic: {topic}")
            return visual_aids
            
        except Exception as e:
            logger.error(f"Error searching visual aids for topic {topic}: {e}")
            raise
    
    @handle_dao_errors("save_visual_aid_template")
    def save_visual_aid_template(self, template_data: Dict[str, Any]) -> str:
        """
        Save a visual aid template for reuse
        
        Args:
            template_data (Dict[str, Any]): Template data to save
            
        Returns:
            str: Document ID of saved template
        """
        try:
            template_id = str(uuid.uuid4())
            
            template_data_with_meta = {
                **template_data,
                "template_id": template_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "status": "active",
                "usage_count": 0
            }
            
            doc_ref = self.db.collection(self.templates_collection).document(template_id)
            doc_ref.set(template_data_with_meta)
            
            logger.info(f"Saved visual aid template with ID: {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Error saving visual aid template: {e}")
            raise
    
    @handle_dao_errors("get_visual_aid_templates")
    def get_visual_aid_templates(self, category: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get visual aid templates
        
        Args:
            category (str, optional): Filter by category
            limit (int): Maximum number of templates
            
        Returns:
            List[Dict[str, Any]]: List of templates
        """
        try:
            query = (self.db.collection(self.templates_collection)
                    .where("status", "==", "active")
                    .order_by("usage_count", direction="DESCENDING")
                    .limit(limit))
            
            if category:
                query = query.where("category", "==", category)
            
            templates = []
            for doc in query.stream():
                if doc.exists:
                    template_data = doc.to_dict()
                    template_data['template_id'] = doc.id
                    templates.append(template_data)
            
            logger.info(f"Retrieved {len(templates)} visual aid templates")
            return templates
            
        except Exception as e:
            logger.error(f"Error getting visual aid templates: {e}")
            raise
    
    @handle_dao_errors("update_template_usage")
    def update_template_usage(self, template_id: str) -> bool:
        """
        Increment usage count for a template
        
        Args:
            template_id (str): Template ID
            
        Returns:
            bool: Success status
        """
        try:
            doc_ref = self.db.collection(self.templates_collection).document(template_id)
            doc_ref.update({
                "usage_count": firestore.Increment(1),
                "last_used": datetime.utcnow()
            })
            
            logger.info(f"Updated usage count for template: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating template usage {template_id}: {e}")
            raise
    
    @handle_dao_errors("delete_visual_aid")
    def delete_visual_aid(self, visual_aid_id: str) -> bool:
        """
        Soft delete a visual aid (mark as inactive)
        
        Args:
            visual_aid_id (str): Visual aid ID
            
        Returns:
            bool: Success status
        """
        try:
            doc_ref = self.db.collection(self.visual_aids_collection).document(visual_aid_id)
            doc_ref.update({
                "status": "deleted",
                "deleted_at": datetime.utcnow()
            })
            
            logger.info(f"Soft deleted visual aid: {visual_aid_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting visual aid {visual_aid_id}: {e}")
            raise

# Singleton instance
visual_aid_dao = VisualAidDAO()
