"""
Voice Assistant Data Access Object (DAO)
Handles all Firestore operations related to voice commands and conversation history
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

class VoiceAssistantDAO:
    """Data Access Object for Voice Assistant-related Firestore operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        
    # Collections
    VOICE_CONVERSATIONS_COLLECTION = "voice_conversations"
    VOICE_HISTORY_COLLECTION = "voice_history"
    
    def save_conversation(self, user_id: str, conversation_data: Dict[str, Any]) -> Optional[str]:
        """
        Save voice conversation to Firestore
        
        Args:
            user_id: User identifier
            conversation_data: Conversation data to save
            
        Returns:
            str: Document ID if successful, None if failed
        """
        try:
            conversation_ref = self.db.collection(self.VOICE_CONVERSATIONS_COLLECTION).document()
            
            # Add metadata
            conversation_data.update({
                "user_id": user_id,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
            
            conversation_ref.set(conversation_data)
            
            logger.info(f"Voice conversation saved successfully for user {user_id}, document ID: {conversation_ref.id}")
            return conversation_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save voice conversation for user {user_id}: {str(e)}")
            return None
    
    def get_conversation_history(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get conversation history for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip
            
        Returns:
            list: List of conversation data
        """
        try:
            conversations_ref = self.db.collection(self.VOICE_CONVERSATIONS_COLLECTION)
            query = conversations_ref.where("user_id", "==", user_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).offset(offset)
            
            conversations = []
            for doc in query.stream():
                conversation_data = doc.to_dict()
                conversation_data["id"] = doc.id
                conversations.append(conversation_data)
            
            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get conversation history for user {user_id}: {str(e)}")
            return []
    
    def update_conversation_feedback(self, conversation_id: str, feedback: Dict[str, Any]) -> bool:
        """
        Update conversation with user feedback
        
        Args:
            conversation_id: Conversation document ID
            feedback: Feedback data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.VOICE_CONVERSATIONS_COLLECTION).document(conversation_id)
            
            # Add metadata
            feedback.update({
                "feedback_updated_at": firestore.SERVER_TIMESTAMP
            })
            
            doc_ref.update(feedback)
            
            logger.info(f"Conversation feedback updated successfully for conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update conversation feedback for conversation {conversation_id}: {str(e)}")
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation
        
        Args:
            conversation_id: Conversation document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.VOICE_CONVERSATIONS_COLLECTION).document(conversation_id)
            doc_ref.delete()
            
            logger.info(f"Conversation {conversation_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {str(e)}")
            return False
    
    def get_conversation_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get voice conversation analytics for specified time period
        
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
            
            # Get conversations in date range
            conversations_ref = self.db.collection(self.VOICE_CONVERSATIONS_COLLECTION)
            query = conversations_ref.where("user_id", "==", user_id).where("created_at", ">=", start_date).where("created_at", "<=", end_date)
            
            conversations = []
            total_transcript_length = 0
            total_response_length = 0
            
            for doc in query.stream():
                conversation_data = doc.to_dict()
                conversations.append(conversation_data)
                
                # Calculate lengths if available
                if "transcript" in conversation_data:
                    total_transcript_length += len(conversation_data["transcript"])
                if "ai_response" in conversation_data:
                    total_response_length += len(conversation_data["ai_response"])
            
            # Calculate analytics
            average_transcript_length = total_transcript_length / len(conversations) if conversations else 0
            average_response_length = total_response_length / len(conversations) if conversations else 0
            
            analytics = {
                "user_id": user_id,
                "period": f"last_{days}_days",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_conversations": len(conversations),
                "average_transcript_length": round(average_transcript_length, 2),
                "average_response_length": round(average_response_length, 2),
                "total_transcript_chars": total_transcript_length,
                "total_response_chars": total_response_length
            }
            
            logger.info(f"Voice analytics generated for user {user_id} (last {days} days)")
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to generate voice analytics for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "period": f"last_{days}_days",
                "error": str(e),
                "total_conversations": 0
            }

# Create a singleton instance
voice_assistant_dao = VoiceAssistantDAO()
