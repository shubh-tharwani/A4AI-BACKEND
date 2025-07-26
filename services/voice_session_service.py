"""
Enhanced Voice Session Service
Manages conversation sessions, context awareness, and multi-turn dialogue
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict

from dao.voice_assistant_dao import voice_assistant_dao
from services.voice_assistant_service import process_voice_command as base_process_voice_command, process_text_command
from services.voice_assistant_service import model, tts_client, AUDIO_FILES_DIR
from google.cloud import texttospeech
import uuid
import os

logger = logging.getLogger(__name__)

@dataclass
class ConversationContext:
    """Represents the context of an ongoing conversation"""
    session_id: str
    user_id: str
    created_at: datetime
    last_interaction_at: datetime
    conversation_history: List[Dict[str, Any]]
    context_summary: str = ""
    topic: str = ""
    total_interactions: int = 0
    session_duration_minutes: float = 0.0

class VoiceSessionService:
    """Enhanced voice service with session management and context awareness"""
    
    def __init__(self):
        self.active_sessions: Dict[str, ConversationContext] = {}
        self.session_timeout_minutes = 30  # Sessions expire after 30 minutes
        self.max_context_history = 10  # Keep last 10 interactions for context
        self.max_sessions_per_user = 5  # Maximum concurrent sessions per user
        self.session_recovery_window_hours = 24  # Time window for session recovery
        self.auto_save_interval_minutes = 5  # Auto-save session state interval
        self._last_auto_save: Dict[str, datetime] = {}  # Track last auto-save per session
        
    async def create_session(self, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Explicitly create a new session with optional metadata
        
        Args:
            user_id: User identifier
            metadata: Optional metadata to associate with the session
            
        Returns:
            Dict containing session information
        """
        # Check concurrent session limit
        user_sessions = await self.get_user_active_sessions(user_id)
        if len(user_sessions) >= self.max_sessions_per_user:
            return {
                "status": "error",
                "message": f"Maximum number of concurrent sessions ({self.max_sessions_per_user}) reached",
                "code": "MAX_SESSIONS_EXCEEDED"
            }
        
        # Create new session
        session = await self._get_or_create_session(user_id)
        
        # Add metadata if provided
        if metadata:
            session.metadata = metadata
        
        return {
            "status": "success",
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "metadata": metadata or {}
        }
        
    async def pause_session(self, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Pause a session without deleting it
        
        Args:
            session_id: Session to pause
            user_id: Optional user ID for verification
            
        Returns:
            Dict containing operation status
        """
        try:
            if session_id not in self.active_sessions:
                return {"status": "error", "message": "Session not found"}
                
            session = self.active_sessions[session_id]
            
            if user_id and session.user_id != user_id:
                return {"status": "error", "message": "Unauthorized"}
            
            # Save session state
            await self._auto_save_session(session)
            
            # Mark as paused but keep in memory
            session.is_paused = True
            session.paused_at = datetime.utcnow()
            
            return {
                "status": "success",
                "message": "Session paused successfully",
                "session_id": session_id,
                "paused_at": session.paused_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error pausing session: {e}")
            return {"status": "error", "message": str(e)}
            
    async def resume_session(self, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Resume a paused session
        
        Args:
            session_id: Session to resume
            user_id: Optional user ID for verification
            
        Returns:
            Dict containing operation status and session info
        """
        try:
            session = self.active_sessions.get(session_id)
            
            if not session:
                # Try to recover from storage
                session = await self._recover_session(session_id, user_id)
                if not session:
                    return {"status": "error", "message": "Session not found"}
            
            if user_id and session.user_id != user_id:
                return {"status": "error", "message": "Unauthorized"}
            
            if hasattr(session, 'is_paused'):
                session.is_paused = False
                del session.paused_at
            
            session.last_interaction_at = datetime.utcnow()
            
            return {
                "status": "success",
                "message": "Session resumed successfully",
                "session_info": await self.get_session_info(session_id)
            }
            
        except Exception as e:
            logger.error(f"Error resuming session: {e}")
            return {"status": "error", "message": str(e)}
        
    async def process_session_voice_command(self, audio_file, user_id: str, session_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        print("Processing Voice Command")
        """
        Process voice command with session context and conversation history
        
        Args:
            audio_file: Uploaded audio file
            user_id: User identifier
            session_id: Optional session ID for continuing conversation
            context: Optional dictionary containing additional context
            
        Returns:
            dict: Enhanced response with session information
        """
        try:
            # Get or create session
            session = await self._get_or_create_session(user_id, session_id)
            
            # Add context to session metadata if provided
            if context:
                if not hasattr(session, 'metadata'):
                    session.metadata = {}
                session.metadata.update(context)
            
            # Process the voice command using base service
            base_result = await base_process_voice_command(audio_file)
            
            if base_result["status"] == "error":
                return base_result
            
            # Enhance AI response with conversation context
            enhanced_response = await self._enhance_response_with_context(
                transcript=base_result["transcript"],
                base_response=base_result["ai_response"],
                session=session
            )
            
            # Update session with new interaction
            await self._update_session_context(session, base_result["transcript"], enhanced_response)
            
            # Generate enhanced audio response
            enhanced_audio = await self._generate_contextual_audio(enhanced_response)
            
            # Save conversation with session context
            conversation_data = {
                "user_id": user_id,
                "session_id": session.session_id,
                "transcript": base_result["transcript"],
                "ai_response": enhanced_response,
                "audio_filename": enhanced_audio["filename"],
                "context_used": True,
                "interaction_number": session.total_interactions,
                "topic": session.topic,
                "created_at": datetime.utcnow(),
                "metadata": {
                    "session_duration_minutes": session.session_duration_minutes,
                    "context_summary": session.context_summary[:200] + "..." if len(session.context_summary) > 200 else session.context_summary
                }
            }
            
            # Store in database
            conversation_id = voice_assistant_dao.save_conversation(user_id, conversation_data)
            
            return {
                "status": "success",
                "transcript": base_result["transcript"],
                "ai_response": enhanced_response,
                "audio_filename": enhanced_audio["filename"],
                "audio_file_path": enhanced_audio["path"],
                "download_url": f"/voice/download-audio/{enhanced_audio['filename']}",
                "session_info": {
                    "session_id": session.session_id,
                    "interaction_number": session.total_interactions,
                    "topic": session.topic,
                    "session_duration_minutes": round(session.session_duration_minutes, 2),
                    "context_used": len(session.conversation_history) > 1
                },
                "conversation_id": conversation_id,
                "metadata": {
                    "processed_at": datetime.utcnow().isoformat(),
                    "enhanced_with_context": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error in session-aware voice processing: {e}")
            return {
                "status": "error",
                "error": str(e),
                "ai_response": "I encountered an error processing your request. Please try again."
            }
    
    async def _get_or_create_session(self, user_id: str, session_id: Optional[str] = None) -> ConversationContext:
        """Get existing session or create new one"""
        
        # Clean up expired sessions
        await self._cleanup_expired_sessions()
        
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            # Update last interaction time
            session.last_interaction_at = datetime.utcnow()
            session.session_duration_minutes = (session.last_interaction_at - session.created_at).total_seconds() / 60
            return session
        
        # Create new session
        new_session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow()
        
        session = ConversationContext(
            session_id=new_session_id,
            user_id=user_id,
            created_at=now,
            last_interaction_at=now,
            conversation_history=[],
            total_interactions=0
        )
        
        self.active_sessions[new_session_id] = session
        logger.info(f"Created new voice session {new_session_id} for user {user_id}")
        
        return session
    
    async def _enhance_response_with_context(self, transcript: str, base_response: str, session: ConversationContext) -> str:
        """Enhance AI response using conversation context"""
        
        if not session.conversation_history:
            # First interaction - just return base response but identify topic
            await self._identify_conversation_topic(transcript, session)
            return base_response
        
        # Build context from conversation history
        context_messages = []
        for interaction in session.conversation_history[-self.max_context_history:]:
            context_messages.append(f"User said: {interaction['user_message']}")
            context_messages.append(f"Assistant said: {interaction['assistant_response']}")
        
        context_prompt = f"""
Previous conversation context:
{chr(10).join(context_messages)}

Current topic: {session.topic}
Conversation summary: {session.context_summary}

Teacher now said: "{transcript}"

Provide a contextually aware response that:
1. References previous conversation if relevant
2. Maintains conversation flow
3. Shows understanding of the ongoing topic
4. Responds helpfully to the teacher's current request

Respond in this JSON format:
{{"answer": "Your contextually aware response for the teacher."}}
"""
        
        try:
            ai_response = model.generate_content(context_prompt)
            raw_text = ai_response.text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.strip("`").replace("json", "").strip()
            
            parsed_response = json.loads(raw_text)
            enhanced_response = parsed_response.get("answer", base_response).strip()
            
            return enhanced_response if enhanced_response else base_response
            
        except Exception as e:
            logger.warning(f"Context enhancement failed, using base response: {e}")
            return base_response
    
    async def _identify_conversation_topic(self, transcript: str, session: ConversationContext):
        """Identify and set the conversation topic"""
        
        topic_prompt = f"""
Analyze this teacher's voice message and identify the main topic/subject:
"{transcript}"

Return just the topic in 2-3 words (e.g., "Math Education", "Classroom Management", "Student Assessment").
"""
        
        try:
            topic_response = model.generate_content(topic_prompt)
            topic = topic_response.text.strip().replace('"', '')[:50]  # Limit length
            session.topic = topic
            logger.info(f"Identified conversation topic: {topic}")
        except Exception as e:
            logger.warning(f"Topic identification failed: {e}")
            session.topic = "General Education"
    
    async def _update_session_context(self, session: ConversationContext, transcript: str, ai_response: str):
        """Update session with new interaction"""
        
        # Add to conversation history
        interaction = {
            "user_message": transcript,
            "assistant_response": ai_response,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        session.conversation_history.append(interaction)
        session.total_interactions += 1
        
        # Keep only recent interactions for context
        if len(session.conversation_history) > self.max_context_history:
            session.conversation_history = session.conversation_history[-self.max_context_history:]
        
        # Update context summary periodically
        if session.total_interactions % 3 == 0:  # Every 3 interactions
            await self._update_context_summary(session)
    
    async def _update_context_summary(self, session: ConversationContext):
        """Generate a summary of the conversation context"""
        
        if len(session.conversation_history) < 2:
            return
        
        # Create summary of recent interactions
        recent_messages = []
        for interaction in session.conversation_history[-6:]:  # Last 6 interactions
            recent_messages.append(f"User: {interaction['user_message']}")
            recent_messages.append(f"Assistant: {interaction['assistant_response']}")
        
        summary_prompt = f"""
Summarize this conversation in 1-2 sentences, focusing on the main topics and context:

{chr(10).join(recent_messages)}

Summary:"""
        
        try:
            summary_response = model.generate_content(summary_prompt)
            session.context_summary = summary_response.text.strip()[:300]  # Limit length
        except Exception as e:
            logger.warning(f"Context summary update failed: {e}")
    
    async def _generate_contextual_audio(self, text: str) -> Dict[str, str]:
        """Generate audio with appropriate voice settings for contextual response"""
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Use a slightly different voice for contextual responses
        voice_params = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Journey-F"  # More natural voice for conversations
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, 
            voice=voice_params, 
            audio_config=audio_config
        )
        
        # Save audio file
        unique_filename = f"session_response_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_output_path = os.path.join(AUDIO_FILES_DIR, unique_filename)
        
        with open(audio_output_path, "wb") as out:
            out.write(tts_response.audio_content)
        
        return {
            "filename": unique_filename,
            "path": audio_output_path
        }
    
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions from memory"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.session_timeout_minutes)
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if session.last_interaction_at < cutoff_time:
                # Don't expire paused sessions
                if hasattr(session, 'is_paused') and session.is_paused:
                    continue
                    
                expired_sessions.append(session_id)
                # Auto-save before expiring
                try:
                    await self._auto_save_session(session)
                except Exception as e:
                    logger.error(f"Failed to auto-save expired session {session_id}: {e}")
        
        for session_id in expired_sessions:
            await self.delete_session(session_id)
            logger.info(f"Expired session {session_id} cleaned up")
            
    async def _auto_save_session(self, session: ConversationContext):
        """Automatically save session state to persistent storage"""
        now = datetime.utcnow()
        last_save = self._last_auto_save.get(session.session_id)
        
        # Check if it's time to auto-save
        if (not last_save or 
            (now - last_save).total_seconds() > self.auto_save_interval_minutes * 60):
            
            try:
                session_state = {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "created_at": session.created_at.isoformat(),
                    "last_interaction_at": session.last_interaction_at.isoformat(),
                    "conversation_history": session.conversation_history,
                    "context_summary": session.context_summary,
                    "topic": session.topic,
                    "total_interactions": session.total_interactions,
                    "session_duration_minutes": session.session_duration_minutes,
                    "is_paused": getattr(session, 'is_paused', False),
                    "metadata": getattr(session, 'metadata', {}),
                    "last_saved_at": now.isoformat()
                }
                
                await voice_assistant_dao.save_session_state(session_state)
                self._last_auto_save[session.session_id] = now
                logger.debug(f"Auto-saved session {session.session_id}")
                
            except Exception as e:
                logger.error(f"Failed to auto-save session {session.session_id}: {e}")
                
    async def _recover_session(self, session_id: str, user_id: Optional[str] = None) -> Optional[ConversationContext]:
        """Attempt to recover a session from persistent storage"""
        try:
            stored_state = await voice_assistant_dao.get_session_state(session_id)
            
            if not stored_state:
                return None
                
            if user_id and stored_state["user_id"] != user_id:
                return None
                
            # Check if within recovery window
            last_saved = datetime.fromisoformat(stored_state["last_saved_at"])
            if (datetime.utcnow() - last_saved).total_seconds() > self.session_recovery_window_hours * 3600:
                return None
                
            # Reconstruct session
            session = ConversationContext(
                session_id=stored_state["session_id"],
                user_id=stored_state["user_id"],
                created_at=datetime.fromisoformat(stored_state["created_at"]),
                last_interaction_at=datetime.utcnow(),  # Reset last interaction time
                conversation_history=stored_state["conversation_history"],
                context_summary=stored_state["context_summary"],
                topic=stored_state["topic"],
                total_interactions=stored_state["total_interactions"],
                session_duration_minutes=stored_state["session_duration_minutes"]
            )
            
            # Restore additional attributes
            session.is_paused = stored_state.get("is_paused", False)
            session.metadata = stored_state.get("metadata", {})
            
            # Add to active sessions
            self.active_sessions[session_id] = session
            logger.info(f"Successfully recovered session {session_id}")
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to recover session {session_id}: {e}")
            return None
            
    async def get_session_analytics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get analytics data for sessions
        
        Args:
            user_id: Optional user ID to filter analytics for specific user
            
        Returns:
            Dict containing analytics data
        """
        try:
            sessions = self.active_sessions.values()
            if user_id:
                sessions = [s for s in sessions if s.user_id == user_id]
                
            total_sessions = len(sessions)
            total_interactions = sum(s.total_interactions for s in sessions)
            avg_duration = sum(s.session_duration_minutes for s in sessions) / total_sessions if total_sessions > 0 else 0
            
            topics = {}
            for session in sessions:
                topics[session.topic] = topics.get(session.topic, 0) + 1
                
            return {
                "status": "success",
                "analytics": {
                    "total_active_sessions": total_sessions,
                    "total_interactions": total_interactions,
                    "average_session_duration": round(avg_duration, 2),
                    "topics_distribution": topics,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating session analytics: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about an active session"""
        
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "created_at": session.created_at.isoformat(),
            "last_interaction_at": session.last_interaction_at.isoformat(),
            "total_interactions": session.total_interactions,
            "topic": session.topic,
            "session_duration_minutes": round(session.session_duration_minutes, 2),
            "context_summary": session.context_summary,
            "is_active": True
        }
    
    async def delete_session(self, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete a session and clean up associated resources
        
        Args:
            session_id: ID of the session to delete
            user_id: Optional user ID to verify session ownership
            
        Returns:
            Dict containing status and message
        """
        try:
            if session_id not in self.active_sessions:
                return {
                    "status": "error",
                    "message": "Session not found",
                    "code": "SESSION_NOT_FOUND"
                }
            
            session = self.active_sessions[session_id]
            
            # Verify session ownership if user_id provided
            if user_id and session.user_id != user_id:
                return {
                    "status": "error",
                    "message": "Unauthorized to delete this session",
                    "code": "UNAUTHORIZED"
                }
            
            # Archive session data before deletion
            try:
                archive_data = {
                    "session_id": session_id,
                    "user_id": session.user_id,
                    "created_at": session.created_at.isoformat(),
                    "ended_at": datetime.utcnow().isoformat(),
                    "total_interactions": session.total_interactions,
                    "topic": session.topic,
                    "context_summary": session.context_summary,
                    "session_duration_minutes": session.session_duration_minutes,
                    "conversation_history": session.conversation_history
                }
                
                # Store in database for history
                await voice_assistant_dao.archive_session(archive_data)
                
            except Exception as e:
                logger.error(f"Failed to archive session data: {e}")
                # Continue with deletion even if archiving fails
            
            # Delete from active sessions
            del self.active_sessions[session_id]
            logger.info(f"Session {session_id} deleted successfully")
            
            return {
                "status": "success",
                "message": "Session deleted successfully",
                "session_id": session_id,
                "archived": True
            }
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to delete session: {str(e)}",
                "code": "DELETE_ERROR"
            }
    
    async def end_session(self, session_id: str) -> bool:
        """Legacy method for backward compatibility"""
        result = await self.delete_session(session_id)
        return result["status"] == "success"
    
    async def get_user_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        
        user_sessions = []
        for session_id, session in self.active_sessions.items():
            if session.user_id == user_id:
                session_info = await self.get_session_info(session_id)
                if session_info:
                    user_sessions.append(session_info)
        
        return user_sessions
    
    async def get_conversation_context(self, session_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return the conversation context for a given session_id"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        # If user_id is provided, verify it matches the session
        if user_id and session.user_id != user_id:
            return None
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "topic": session.topic,
            "context_summary": session.context_summary,
            "conversation_history": session.conversation_history,
            "total_interactions": session.total_interactions,
            "created_at": session.created_at.isoformat(),
            "last_interaction_at": session.last_interaction_at.isoformat(),
            "session_duration_minutes": round(session.session_duration_minutes, 2)
        }

    async def process_session_text_command(self, text: str, user_id: str, session_id: Optional[str] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process text command with session context and conversation history
        
        Args:
            text: Text message to process
            user_id: User identifier
            session_id: Optional session ID for continuing conversation
            context: Additional context data
            
        Returns:
            Dict containing AI response and session information
        """
        try:
            logger.info(f"Processing text command with session for user {user_id}")
            
            # Clean up expired sessions
            await self._cleanup_expired_sessions()
            
            # Get or create session
            session = await self._get_or_create_session(user_id, session_id)
            
            # Process the text with text command service (not voice command)
            base_response = await process_text_command(text, context or {})
            
            # Extract AI response from base response
            ai_response = base_response.get("ai_response", "I'm here to help with your educational needs.")
            
            # Enhance response with conversation context
            enhanced_response = await self._enhance_response_with_context(
                text, ai_response, session
            )
            
            # Update session context
            await self._update_session_context(session, text, enhanced_response)
            
            # Update topic if needed
            await self._identify_conversation_topic(text, session)
            
            # Save session to storage
            try:
                session_data = {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "transcript": text,
                    "ai_response": enhanced_response,
                    "context": context or {},
                    "timestamp": datetime.now().isoformat(),
                    "interaction_type": "text",
                    "topic": session.topic,
                    "total_interactions": session.total_interactions
                }
                await voice_assistant_dao.save_voice_session(session_data)
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
            
            return {
                "session_id": session.session_id,
                "ai_response": enhanced_response,
                "context_summary": session.context_summary,
                "topic": session.topic,
                "total_interactions": session.total_interactions,
                "session_duration_minutes": round(session.session_duration_minutes, 2),
                "input_type": "text",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing text command with session: {str(e)}")
            return {
                "session_id": session_id,
                "ai_response": "I apologize, but I encountered an issue processing your request. Please try again.",
                "error": str(e),
                "input_type": "text",
                "timestamp": datetime.now().isoformat()
            }

# Create singleton instance
voice_session_service = VoiceSessionService()
