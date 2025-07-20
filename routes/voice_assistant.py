from fastapi import APIRouter, UploadFile, Depends, HTTPException, File, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import os
import logging
import mimetypes
from pathlib import Path

from services.voice_assistant_service import process_voice_command
from auth_middleware import firebase_auth, get_current_user_id
import sys
import os

# Add parent directory to path to import config.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice-assistant", tags=["Voice Assistant"])

class VoiceAssistantResponse(BaseModel):
    status: str
    transcript: str
    ai_response: str
    audio_file_path: Optional[str]
    audio_filename: Optional[str]
    download_url: Optional[str]
    metadata: Dict[str, Any]

@router.post("/process",
            summary="Process Voice Command",
            description="Process voice input and return AI-generated response with audio",
            response_model=VoiceAssistantResponse,
            dependencies=[Depends(firebase_auth)])
async def handle_voice_command(
    file: UploadFile = File(..., description="Audio file containing voice command"),
    user_request: Request = None
):
    """
    Process teacher's voice input and respond with AI-generated voice + text
    
    - **file**: Audio file (WAV, MP3, FLAC, WEBM supported)
    
    Returns transcript, AI response text, and downloadable audio response
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        # Validate file
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Check file size
        content = await file.read()
        file_size = len(content)
        
        if file_size > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE} bytes"
            )
        
        if file_size < 1000:
            raise HTTPException(status_code=400, detail="File too small or corrupted")
        
        # Validate file extension
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        logger.info(f"Processing voice command for user {user_id}: {file.filename} ({file_size} bytes)")
        
        # Reset file pointer and process
        await file.seek(0)
        result = await process_voice_command(file)
        
        if result.get("status") == "error":
            logger.error(f"Voice processing error for user {user_id}: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get("error", "Voice processing failed"))
        
        # Generate download URL if audio file was created
        download_url = None
        if result.get("audio_filename"):
            download_url = f"/api/v1/voice-assistant/download-audio/{result['audio_filename']}"
        
        logger.info(f"Successfully processed voice command for user {user_id}")
        
        return VoiceAssistantResponse(
            status="success",
            transcript=result.get("transcript", ""),
            ai_response=result.get("ai_response", ""),
            audio_file_path=result.get("audio_file_path"),
            audio_filename=result.get("audio_filename"),
            download_url=download_url,
            metadata={
                "user_id": user_id,
                "input_filename": file.filename,
                "input_size": file_size,
                "input_format": file_extension,
                "processed_at": datetime.utcnow().isoformat(),
                "transcript_length": len(result.get("transcript", "")),
                "response_length": len(result.get("ai_response", ""))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing voice command for user {user_id if 'user_id' in locals() else 'unknown'}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Voice processing failed: {str(e)}"
        )

@router.get("/download-audio/{filename}",
           summary="Download Audio Response",
           description="Download the AI-generated audio response file",
           dependencies=[Depends(firebase_auth)])
async def download_audio_response(
    filename: str,
    user_request: Request
):
    """
    Download the generated audio response file
    
    - **filename**: Name of the audio file to download
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        # Validate filename (security check)
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Find file in audio directory
        audio_files_dir = Path(config.UPLOAD_DIR)
        file_path = audio_files_dir / filename
        
        if not file_path.exists() or not file_path.is_file():
            logger.warning(f"Audio file not found for user {user_id}: {filename}")
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "audio/mpeg"  # Default for MP3
        
        logger.info(f"Serving audio file for user {user_id}: {filename}")
        
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=filename,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to serve audio file"
        )

@router.get("/conversations",
           summary="Get User Conversation History",
           description="Get conversation history for the authenticated user",
           dependencies=[Depends(firebase_auth)])
async def get_conversation_history(
    user_request: Request,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0
):
    """
    Get conversation history for the user
    
    - **limit**: Maximum number of conversations to return (1-100)
    - **offset**: Number of conversations to skip
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        # Validate parameters
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        if offset < 0:
            raise HTTPException(status_code=400, detail="Offset must be non-negative")
        
        # TODO: Implement conversation history retrieval from database
        # For now, return empty list with proper structure
        
        logger.info(f"Retrieved conversation history for user {user_id} (limit: {limit}, offset: {offset})")
        
        return {
            "status": "success",
            "conversations": [],  # TODO: Implement actual conversation retrieval
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "metadata": {
                "user_id": user_id,
                "retrieved_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation history"
        )


@router.get("/health",
           summary="Voice Assistant Service Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for the voice assistant service"""
    return {
        "status": "healthy",
        "service": "voice_assistant",
        "message": "Voice assistant service is running properly",
        "features": [
            "speech_to_text",
            "ai_response_generation",
            "text_to_speech",
            "audio_file_management"
        ],
        "supported_formats": config.ALLOWED_EXTENSIONS,
        "max_file_size_mb": round(config.MAX_FILE_SIZE / (1024 * 1024), 2)
    }
