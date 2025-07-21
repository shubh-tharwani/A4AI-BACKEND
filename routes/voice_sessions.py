"""
Enhanced Voice Routes with Session Management
Additional endpoints for session-aware voice processing
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from auth_middleware import firebase_auth, get_current_user_id
from services.voice_session_service import voice_session_service
from dao.voice_assistant_dao import voice_assistant_dao

logger = logging.getLogger(__name__)

router = APIRouter()

# ===== RESPONSE MODELS =====

class SessionVoiceResponse(BaseModel):
    """Response model for session-aware voice processing"""
    status: str
    transcript: str
    ai_response: str
    audio_filename: Optional[str]
    download_url: Optional[str]
    session_info: Dict[str, Any]
    conversation_id: Optional[str]
    metadata: Dict[str, Any]

class SessionInfoResponse(BaseModel):
    """Response model for session information"""
    status: str
    session_info: Optional[Dict[str, Any]]

class UserSessionsResponse(BaseModel):
    """Response model for user's active sessions"""
    status: str
    active_sessions: List[Dict[str, Any]]
    total_count: int

# ===== SESSION-AWARE VOICE PROCESSING =====

@router.post("/session-assistant",
           summary="Session-Aware Voice Assistant", 
           description="Process voice with conversation context and session management",
           response_model=SessionVoiceResponse,
           dependencies=[Depends(firebase_auth)])
async def session_voice_assistant(
    user_request: Request,
    file: UploadFile = File(..., description="Audio file (WAV, MP3, FLAC, WebM)"),
    session_id: Optional[str] = Query(None, description="Session ID to continue conversation")
):
    """
    Enhanced voice assistant with session management and conversation context
    
    Features:
    - **Context Awareness**: Remembers previous conversation
    - **Session Management**: Maintains conversation state
    - **Topic Tracking**: Identifies and tracks conversation topics
    - **Enhanced Responses**: Uses context to provide better answers
    
    Parameters:
    - **file**: Audio file to process
    - **session_id**: Optional session ID to continue existing conversation
    """
    try:
        user_id = await get_current_user_id(user_request)
        logger.info(f"Processing session-aware voice request for user {user_id}, session: {session_id}")
        
        # Validate file
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Process with session context
        result = await voice_session_service.process_voice_with_session(
            audio_file=file,
            user_id=user_id,
            session_id=session_id
        )
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["error"])
        
        return SessionVoiceResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session voice processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process voice with session context"
        )

# ===== SESSION MANAGEMENT ENDPOINTS =====

@router.get("/sessions/{session_id}",
           summary="Get Session Information",
           description="Retrieve information about a specific voice session",
           response_model=SessionInfoResponse,
           dependencies=[Depends(firebase_auth)])
async def get_session_info(
    session_id: str,
    user_request: Request
):
    """
    Get detailed information about a voice session
    
    Returns session data including:
    - Session duration and interaction count
    - Current conversation topic
    - Context summary
    - Activity status
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        session_info = await voice_session_service.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired"
            )
        
        # Verify session belongs to user
        if session_info["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: session belongs to different user"
            )
        
        return SessionInfoResponse(
            status="success",
            session_info=session_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve session information"
        )

@router.delete("/sessions/{session_id}",
              summary="End Voice Session",
              description="Manually end an active voice session",
              dependencies=[Depends(firebase_auth)])
async def end_session(
    session_id: str,
    user_request: Request
):
    """
    Manually end an active voice session
    
    This will:
    - Remove session from active memory
    - Clear conversation context
    - Free up resources
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        # First verify session exists and belongs to user
        session_info = await voice_session_service.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail="Session not found or already expired"
            )
        
        if session_info["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: session belongs to different user"
            )
        
        # End the session
        success = await voice_session_service.end_session(session_id)
        
        return {
            "status": "success",
            "message": f"Session {session_id} ended successfully",
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to end session"
        )

@router.get("/sessions",
           summary="Get User's Active Sessions",
           description="Retrieve all active voice sessions for the current user",
           response_model=UserSessionsResponse,
           dependencies=[Depends(firebase_auth)])
async def get_user_sessions(
    user_request: Request
):
    """
    Get all active voice sessions for the current user
    
    Useful for:
    - Resuming previous conversations
    - Managing multiple concurrent sessions
    - Session analytics and monitoring
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        active_sessions = await voice_session_service.get_user_active_sessions(user_id)
        
        return UserSessionsResponse(
            status="success",
            active_sessions=active_sessions,
            total_count=len(active_sessions)
        )
        
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user sessions"
        )

# ===== CONVERSATION ANALYTICS =====

@router.get("/sessions/{session_id}/analytics",
           summary="Get Session Analytics",
           description="Get detailed analytics for a specific session",
           dependencies=[Depends(firebase_auth)])
async def get_session_analytics(
    session_id: str,
    user_request: Request
):
    """
    Get analytics for a specific voice session
    
    Includes:
    - Interaction patterns
    - Topic evolution
    - Response quality metrics
    - Usage statistics
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        # Verify session access
        session_info = await voice_session_service.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(
                status_code=404,
                detail="Session not found or expired"
            )
        
        if session_info["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: session belongs to different user"
            )
        
        # Get conversation history for this session
        conversations = voice_assistant_dao.get_conversation_history(
            user_id=user_id,
            limit=100  # Get all conversations for this session
        )
        
        # Filter conversations by session_id
        session_conversations = [
            conv for conv in conversations 
            if conv.get("session_id") == session_id
        ]
        
        # Calculate analytics
        if not session_conversations:
            analytics = {
                "session_id": session_id,
                "total_interactions": 0,
                "average_transcript_length": 0,
                "average_response_length": 0,
                "topic": session_info.get("topic", "Unknown"),
                "session_duration_minutes": session_info.get("session_duration_minutes", 0)
            }
        else:
            total_transcript_length = sum(len(conv.get("transcript", "")) for conv in session_conversations)
            total_response_length = sum(len(conv.get("ai_response", "")) for conv in session_conversations)
            
            analytics = {
                "session_id": session_id,
                "total_interactions": len(session_conversations),
                "average_transcript_length": round(total_transcript_length / len(session_conversations), 2),
                "average_response_length": round(total_response_length / len(session_conversations), 2),
                "topic": session_info.get("topic", "Unknown"),
                "session_duration_minutes": session_info.get("session_duration_minutes", 0),
                "context_summary": session_info.get("context_summary", ""),
                "first_interaction": session_conversations[-1].get("created_at") if session_conversations else None,
                "last_interaction": session_conversations[0].get("created_at") if session_conversations else None
            }
        
        return {
            "status": "success",
            "analytics": analytics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve session analytics"
        )
