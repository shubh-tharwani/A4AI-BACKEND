from fastapi import APIRouter, UploadFile, Depends, HTTPException, File, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import os
import logging
import mimetypes
from pathlib import Path

from services.voice_assistant_service import process_voice_command
from services.voice_agent import speech_to_text
from dao.voice_assistant_dao import voice_assistant_dao
from auth_middleware import firebase_auth, get_current_user_id
import sys
import os

# Add parent directory to path to import config.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])

# Response Models
class TranscriptionResponse(BaseModel):
    status: str
    transcript: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    metadata: dict

class VoiceAssistantResponse(BaseModel):
    status: str
    transcript: str
    ai_response: str
    audio_file_path: Optional[str]
    audio_filename: Optional[str]
    download_url: Optional[str]
    metadata: Dict[str, Any]

class ConversationHistoryResponse(BaseModel):
    status: str
    conversations: List[Dict[str, Any]]
    total_count: int

# ===== TRANSCRIPTION ENDPOINTS =====

@router.post("/transcribe",
            summary="Transcribe Audio to Text",
            description="Convert uploaded audio file to text using advanced speech recognition",
            response_model=TranscriptionResponse,
            dependencies=[Depends(firebase_auth)])
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = "en-US",
    user_request: Request = None
):
    """
    Basic speech-to-text transcription
    
    - **file**: Audio file (WAV, MP3, FLAC, WEBM supported)
    - **language**: Language code for transcription (default: en-US)
    
    Supported formats: WAV, MP3, FLAC, WEBM
    Maximum file size: 10MB
    """
    try:
        user_id = get_current_user_id(user_request)
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file extension
        allowed_extensions = {'.wav', '.mp3', '.flac', '.webm', '.m4a'}
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        audio_content = await file.read()
        
        # Validate file size (10MB limit)
        if len(audio_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
        
        # Perform transcription
        transcript = speech_to_text(audio_content)
        
        if not transcript:
            transcript = "No speech detected in the audio file"
            
        return TranscriptionResponse(
            status="success",
            transcript=transcript,
            confidence=0.95,  # Placeholder - could be enhanced with actual confidence
            language=language,
            metadata={
                "filename": file.filename,
                "file_size": len(audio_content),
                "transcribed_at": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# ===== VOICE ASSISTANT ENDPOINTS =====

@router.post("/assistant",
            summary="Voice Assistant - Full Processing",
            description="Process voice input and return AI-generated response with audio",
            response_model=VoiceAssistantResponse,
            dependencies=[Depends(firebase_auth)])
async def voice_assistant(
    file: UploadFile = File(..., description="Audio file containing voice command"),
    user_request: Request = None
):
    """
    Full voice assistant processing: Speech-to-Text → AI Response → Text-to-Speech
    
    - **file**: Audio file (WAV, MP3, FLAC, WEBM supported)
    
    Returns transcript, AI response text, and downloadable audio response
    """
    try:
        user_id = get_current_user_id(user_request)
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file extension
        allowed_extensions = {'.wav', '.mp3', '.flac', '.webm', '.m4a'}
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Process voice command using the existing service
        result = await process_voice_command(file)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Store conversation in database
        try:
            conversation_data = {
                "user_id": user_id,
                "transcript": result["transcript"],
                "ai_response": result["ai_response"],
                "audio_filename": result.get("audio_filename"),
                "created_at": datetime.utcnow(),
                "metadata": {
                    "original_filename": file.filename,
                    "processing_status": "completed"
                }
            }
            
            await voice_assistant_dao.store_conversation(conversation_data)
            logger.info(f"Conversation stored for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to store conversation: {e}")
            # Don't fail the request if conversation storage fails
        
        # Generate download URL
        download_url = None
        if result.get("audio_filename"):
            download_url = f"/voice/download-audio/{result['audio_filename']}"
        
        return VoiceAssistantResponse(
            status="success",
            transcript=result["transcript"],
            ai_response=result["ai_response"],
            audio_file_path=result.get("audio_file_path"),
            audio_filename=result.get("audio_filename"),
            download_url=download_url,
            metadata={
                "user_id": user_id,
                "processed_at": datetime.utcnow().isoformat(),
                "original_filename": file.filename
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice assistant error: {e}")
        raise HTTPException(status_code=500, detail=f"Voice assistant processing failed: {str(e)}")

# ===== AUDIO DOWNLOAD ENDPOINT =====

@router.get("/download-audio/{filename}",
           summary="Download Generated Audio",
           description="Download AI-generated audio response file")
async def download_audio_file(
    filename: str,
    user_request: Request = None,
    current_user: str = Depends(firebase_auth)
):
    """
    Download AI-generated audio response
    
    - **filename**: The audio filename to download
    """
    try:
        # Construct file path
        audio_path = os.path.join(os.getcwd(), "temp_audio", filename)
        
        # Verify file exists and is safe
        if not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Security check: ensure filename doesn't contain path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Determine media type
        media_type = mimetypes.guess_type(audio_path)[0] or "audio/mpeg"
        
        # Return file
        return FileResponse(
            path=audio_path,
            media_type=media_type,
            filename=filename,
            headers={"Cache-Control": "no-cache"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio download error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download audio: {str(e)}")

# ===== CONVERSATION HISTORY ENDPOINT =====

@router.get("/conversations",
           summary="Get Voice Conversation History", 
           description="Retrieve user's voice assistant conversation history",
           response_model=ConversationHistoryResponse,
           dependencies=[Depends(firebase_auth)])
async def get_conversation_history(
    user_request: Request = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get user's conversation history with the voice assistant
    
    - **limit**: Maximum number of conversations to return (default: 50, max: 100)
    - **offset**: Number of conversations to skip (for pagination)
    """
    try:
        user_id = get_current_user_id(user_request)
        
        # Validate parameters
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 50
        if offset < 0:
            offset = 0
        
        # Retrieve conversations from DAO
        conversations = await voice_assistant_dao.get_user_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        total_count = await voice_assistant_dao.get_user_conversations_count(user_id)
        
        return ConversationHistoryResponse(
            status="success",
            conversations=conversations,
            total_count=total_count
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve conversation history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history"
        )

# ===== UTILITY ENDPOINTS =====

@router.get("/supported-formats",
           summary="Get Supported Audio Formats",
           description="List all supported audio formats and their specifications")
async def get_supported_formats():
    """
    Get information about supported audio formats
    """
    return {
        "status": "success",
        "supported_formats": {
            "wav": {
                "description": "Waveform Audio Format",
                "mime_types": ["audio/wav", "audio/wave"],
                "extensions": [".wav"],
                "recommended_sample_rate": "16kHz",
                "max_file_size": "10MB"
            },
            "mp3": {
                "description": "MPEG Audio Layer 3",
                "mime_types": ["audio/mpeg", "audio/mp3"],
                "extensions": [".mp3"],
                "recommended_bitrate": "128kbps or higher",
                "max_file_size": "10MB"
            },
            "flac": {
                "description": "Free Lossless Audio Codec",
                "mime_types": ["audio/flac"],
                "extensions": [".flac"],
                "quality": "Lossless compression",
                "max_file_size": "10MB"
            },
            "webm": {
                "description": "WebM Audio (Opus codec)",
                "mime_types": ["audio/webm"],
                "extensions": [".webm"],
                "recommended_sample_rate": "48kHz",
                "max_file_size": "10MB"
            },
            "m4a": {
                "description": "MPEG-4 Audio",
                "mime_types": ["audio/mp4", "audio/m4a"],
                "extensions": [".m4a"],
                "codec": "AAC",
                "max_file_size": "10MB"
            }
        },
        "general_requirements": {
            "max_file_size": "10MB",
            "max_duration": "5 minutes recommended",
            "language_support": ["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"],
            "quality_tips": [
                "Clear speech with minimal background noise",
                "Consistent volume level",
                "Avoid echo or reverb",
                "16kHz sample rate or higher for best results"
            ]
        }
    }

@router.get("/health",
           summary="Voice Service Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for the voice service"""
    return {
        "status": "healthy",
        "service": "voice_unified",
        "message": "Voice service is running properly",
        "features": [
            "speech_to_text_transcription",
            "voice_assistant_full_processing",
            "ai_response_generation", 
            "text_to_speech",
            "audio_file_management",
            "conversation_history"
        ],
        "supported_formats": ["WAV", "MP3", "FLAC", "WEBM", "M4A"],
        "max_file_size_mb": round(config.MAX_FILE_SIZE / (1024 * 1024), 2),
        "endpoints": {
            "transcription": "/voice/transcribe",
            "voice_assistant": "/voice/assistant", 
            "audio_download": "/voice/download-audio/{filename}",
            "conversation_history": "/voice/conversations",
            "supported_formats": "/voice/supported-formats"
        }
    }
