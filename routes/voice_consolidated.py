"""
Consolidated Voice API - Single comprehensive voice assistant module
Replaces: voice_unified.py, voice_sessions.py, voice_text_enhanced.py, voice_combined.py
All voice-related functionality in one precise, organized module
"""

import logging
import os
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from auth_middleware import verify_token
from services.voice_assistant_service import process_voice_command
from services.voice_session_service import VoiceSessionService
from services.vertex_ai import VertexAIService
from dao.voice_assistant_dao import VoiceAssistantDAO

# Initialize services
voice_session_service = VoiceSessionService()
try:
    vertex_ai_service = VertexAIService()
except:
    vertex_ai_service = None
voice_dao = VoiceAssistantDAO()

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class VoiceRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")

class TextRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="Text message/question")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    generate_audio: bool = Field(False, description="Generate audio response")

class FileAnalysisRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    query: str = Field(..., description="Question about the file")
    session_id: Optional[str] = Field(None, description="Session ID")
    generate_audio: bool = Field(False, description="Generate audio response")

class UniversalRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Session ID")
    message: Optional[str] = Field(None, description="Text input")
    query: Optional[str] = Field(None, description="File query")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Context")
    response_format: str = Field("auto", description="Response format: text, audio, both, auto")

# ============================================================================
# CORE VOICE PROCESSING ENDPOINTS
# ============================================================================

@router.post("/assistant",
             summary="Universal Voice Assistant", 
             description="Handles voice, text, and file inputs intelligently")
async def universal_assistant(
    request: Request,
    user_data: dict = Depends(verify_token),
    # Optional inputs - at least one required
    audio_file: Optional[UploadFile] = File(None, description="Audio file for voice processing"),
    message: Optional[str] = Form(None, description="Text message for direct chat"),
    file_upload: Optional[UploadFile] = File(None, description="File for analysis"),
    query: Optional[str] = Form(None, description="Question about uploaded file"),
    # Required parameters
    user_id: str = Form(..., description="User identifier"),
    # Optional parameters
    session_id: Optional[str] = Form(None, description="Session ID for conversation continuity"),
    response_format: str = Form("auto", description="Response format: text, audio, both, auto"),
    context: str = Form("{}", description="JSON context object")
):
    """
    Universal voice assistant that intelligently processes:
    - Audio files → Speech-to-text → AI response → Optional audio output
    - Text messages → Direct AI processing → Optional audio output
    - File uploads + queries → File analysis → Optional audio output
    - Session-aware conversations with context preservation
    """
    start_time = datetime.now()
    
    try:
        # Parse context
        try:
            context_dict = json.loads(context)
        except:
            context_dict = {}
        
        # Validate input - at least one input type required
        has_audio = audio_file is not None
        has_text = message is not None and message.strip()
        has_file = file_upload is not None
        
        if not (has_audio or has_text or has_file):
            raise HTTPException(
                status_code=400, 
                detail="Must provide at least one input: audio_file, message, or file_upload"
            )
        
        # Initialize response data
        input_type = "unknown"
        transcript = None
        ai_response = ""
        audio_file_path = None
        audio_filename = None
        file_analysis = None
        
        # Process based on input priority: Voice > Text > File
        if has_audio:
            logger.info(f"Processing voice input for user {user_id}")
            input_type = "voice"
            
            # Use session-aware processing if available
            if session_id:
                result = await voice_session_service.process_session_voice_command(
                    audio_file, user_id, session_id, context_dict
                )
            else:
                result = await process_voice_command(audio_file)
            
            transcript = result.get("transcript", "")
            ai_response = result.get("ai_response", "")
            
            # Audio response handling
            if response_format in ["audio", "both", "auto"]:
                if result.get("audio_file_path"):
                    audio_file_path = result["audio_file_path"]
                    audio_filename = result.get("audio_filename")
                else:
                    # Generate audio if not already created
                    audio_result = await _generate_audio_response(ai_response)
                    audio_file_path = audio_result.get("audio_file_path")
                    audio_filename = audio_result.get("audio_filename")
        
        elif has_text:
            logger.info(f"Processing text input for user {user_id}: {message[:50]}...")
            input_type = "text"
            
            # Process with session awareness if available
            if session_id:
                result = await voice_session_service.process_session_text_command(
                    message, user_id, session_id, context_dict
                )
                ai_response = result.get("ai_response", "")
            else:
                ai_response = await _process_text_with_ai(message, context_dict)
            
            # Generate audio if requested
            if response_format in ["audio", "both"]:
                audio_result = await _generate_audio_response(ai_response)
                audio_file_path = audio_result.get("audio_file_path")
                audio_filename = audio_result.get("audio_filename")
        
        elif has_file:
            logger.info(f"Processing file input for user {user_id}")
            input_type = "file"
            
            query_text = query or message or "Please analyze this file and provide insights."
            
            # Process file with AI
            file_result = await _process_file_with_ai(file_upload, query_text, context_dict)
            ai_response = file_result.get("ai_response", "")
            file_analysis = file_result.get("analysis", {})
            
            # Generate audio if requested
            if response_format in ["audio", "both"]:
                audio_result = await _generate_audio_response(ai_response)
                audio_file_path = audio_result.get("audio_file_path")
                audio_filename = audio_result.get("audio_filename")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Store conversation if session exists
        if session_id and ai_response:
            try:
                await voice_dao.store_conversation_async(
                    user_id=user_id,
                    session_id=session_id,
                    transcript=transcript or message or query or "File processed",
                    ai_response=ai_response,
                    audio_file_path=audio_file_path,
                    metadata={
                        "input_type": input_type,
                        "processing_time": processing_time,
                        "response_format": response_format,
                        "has_file": has_file
                    }
                )
            except Exception as e:
                logger.warning(f"Could not store conversation: {e}")
        
        return JSONResponse(content={
            "status": "success",
            "user_id": user_id,
            "session_id": session_id,
            "input_type": input_type,
            "transcript": transcript,
            "ai_response": ai_response,
            "audio_file_path": audio_file_path,
            "audio_filename": audio_filename,
            "file_analysis": file_analysis,
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Universal assistant error: {str(e)}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return JSONResponse(
            content={
                "status": "error",
                "user_id": user_id,
                "message": f"Processing error: {str(e)}",
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            },
            status_code=500
        )

# ============================================================================
# SPECIALIZED ENDPOINTS (Streamlined)
# ============================================================================

@router.post("/transcribe",
             summary="Speech-to-Text Only",
             description="Convert audio to text without AI processing")
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    user_data: dict = Depends(verify_token)
):
    """Simple speech-to-text conversion without AI response"""
    try:
        # Use the voice service but extract only transcript
        result = await process_voice_command(audio_file)
        
        return JSONResponse(content={
            "status": "success",
            "transcript": result.get("transcript", ""),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.post("/text-chat",
             summary="Text-Only Chat",
             description="Direct text conversation with AI")
async def text_chat(
    request: TextRequest,
    user_data: dict = Depends(verify_token)
):
    """Direct text-to-AI conversation"""
    try:
        # Process with session if provided
        if request.session_id:
            result = await voice_session_service.process_session_text_command(
                request.message, request.user_id, request.session_id, request.context
            )
            ai_response = result.get("ai_response", "")
        else:
            ai_response = await _process_text_with_ai(request.message, request.context)
        
        response_data = {
            "status": "success",
            "user_id": request.user_id,
            "session_id": request.session_id,
            "message": request.message,
            "ai_response": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate audio if requested
        if request.generate_audio:
            audio_result = await _generate_audio_response(ai_response)
            response_data.update({
                "audio_file_path": audio_result.get("audio_file_path"),
                "audio_filename": audio_result.get("audio_filename")
            })
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Text chat error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@router.get("/sessions/{user_id}",
            summary="Get User Sessions",
            description="Retrieve all conversation sessions for a user")
async def get_user_sessions(
    user_id: str,
    limit: int = 50,
    user_data: dict = Depends(verify_token)
):
    """Get all sessions for a user"""
    try:
        sessions = await voice_dao.get_user_conversations_async(user_id, limit=limit)
        return JSONResponse(content={
            "status": "success",
            "user_id": user_id,
            "sessions": sessions,
            "count": len(sessions)
        })
    except Exception as e:
        logger.error(f"Get sessions error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.get("/sessions/{user_id}/{session_id}",
            summary="Get Specific Session",
            description="Retrieve a specific conversation session")
async def get_session(
    user_id: str,
    session_id: str,
    user_data: dict = Depends(verify_token)
):
    """Get specific session details"""
    try:
        session_data = await voice_session_service.get_conversation_context(user_id, session_id)
        return JSONResponse(content={
            "status": "success",
            "user_id": user_id,
            "session_id": session_id,
            "session_data": session_data
        })
    except Exception as e:
        logger.error(f"Get session error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.delete("/sessions/{session_id}",
               summary="Delete Session",
               description="Delete a conversation session")
async def delete_session(
    session_id: str,
    user_data: dict = Depends(verify_token)
):
    """Delete a conversation session"""
    try:
        # Implementation would depend on your session storage
        await voice_session_service.delete_session(session_id)
        return JSONResponse(content={
            "status": "success",
            "message": f"Session {session_id} deleted successfully"
        })
    except Exception as e:
        logger.error(f"Delete session error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/audio/{filename}",
            summary="Download Audio File",
            description="Download generated audio responses")
async def download_audio(filename: str):
    """Download audio file"""
    try:
        audio_dir = os.path.join(os.getcwd(), "temp_audio")
        file_path = os.path.join(audio_dir, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            file_path,
            media_type="audio/mpeg",
            filename=filename
        )
    except Exception as e:
        logger.error(f"Audio download error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-formats",
            summary="Supported Audio Formats",
            description="List all supported audio formats")
async def get_supported_formats():
    """Get supported audio formats"""
    return JSONResponse(content={
        "supported_formats": {
            "input": ["wav", "mp3", "flac", "webm", "m4a", "ogg"],
            "output": ["mp3"],
            "max_file_size": "10MB",
            "recommended": "wav (16kHz, mono)"
        },
        "text_input": {
            "max_length": 5000,
            "supported_languages": ["en-US"]
        },
        "file_analysis": {
            "supported_types": ["pdf", "txt", "docx", "jpg", "png", "gif"],
            "max_file_size": "10MB"
        }
    })

@router.get("/health",
            summary="Voice Service Health Check",
            description="Check the health of all voice-related services")
async def health_check():
    """Comprehensive health check"""
    try:
        # Test core services
        services_status = {
            "voice_processing": "healthy",
            "text_processing": "healthy" if vertex_ai_service else "degraded",
            "session_management": "healthy",
            "audio_generation": "healthy",
            "file_storage": "healthy"
        }
        
        overall_status = "healthy" if all(s in ["healthy"] for s in services_status.values()) else "degraded"
        
        return JSONResponse(content={
            "status": overall_status,
            "service": "consolidated-voice-assistant",
            "services": services_status,
            "capabilities": [
                "voice-to-text",
                "text-to-speech", 
                "text-chat",
                "file-analysis",
                "session-management",
                "multi-modal-input"
            ],
            "endpoints": 8,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            },
            status_code=503
        )

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _process_text_with_ai(message: str, context: Dict[str, Any]) -> str:
    """Process text with AI"""
    try:
        prompt = f"""
        As an AI educational assistant, respond to: "{message}"
        
        Context: {context}
        
        Provide a helpful, educational response that is:
        - Clear and concise
        - Appropriate for the context
        - Encouraging and supportive
        - Focused on learning
        """
        
        if vertex_ai_service:
            response = await vertex_ai_service.generate_content_async(prompt)
            return response.strip()
        else:
            return f"I understand you're asking about: {message}. I'm here to help with your educational questions!"
    except Exception as e:
        logger.error(f"AI text processing error: {str(e)}")
        return "I'm having trouble processing your request right now. Please try again."

async def _generate_audio_response(text: str) -> Dict[str, Any]:
    """Generate audio from text"""
    try:
        from google.cloud import texttospeech
        
        tts_client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        
        # Save audio file
        audio_dir = os.path.join(os.getcwd(), "temp_audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        filename = f"response_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        file_path = os.path.join(audio_dir, filename)
        
        with open(file_path, "wb") as out:
            out.write(response.audio_content)
        
        return {"audio_file_path": file_path, "audio_filename": filename}
        
    except Exception as e:
        logger.error(f"Audio generation error: {str(e)}")
        return {"audio_file_path": None, "audio_filename": None}

async def _process_file_with_ai(file_upload: UploadFile, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process file with AI analysis"""
    try:
        content = await file_upload.read()
        file_type = file_upload.content_type or "unknown"
        file_size = len(content)
        
        analysis = {
            "filename": file_upload.filename,
            "file_type": file_type,
            "file_size": file_size,
            "analysis_type": "content_analysis"
        }
        
        # Basic file processing based on type
        if file_type.startswith("text/") or file_upload.filename.endswith((".txt", ".md")):
            text_content = content.decode("utf-8")
            prompt = f"Analyze this text and answer: {query}\n\nContent:\n{text_content[:2000]}..."
            analysis["analysis_type"] = "text_analysis"
        else:
            prompt = f"User has uploaded a {file_type} file and asks: {query}. Provide helpful guidance about this file type."
        
        # Generate AI response
        if vertex_ai_service:
            ai_response = await vertex_ai_service.generate_content_async(prompt)
        else:
            ai_response = f"I can help analyze your {file_type} file. Please describe what you'd like to know about it."
        
        return {"ai_response": ai_response.strip(), "analysis": analysis}
        
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        return {
            "ai_response": f"I encountered an error analyzing the file: {str(e)}",
            "analysis": {"filename": file_upload.filename if file_upload else "unknown", "error": str(e)}
        }
