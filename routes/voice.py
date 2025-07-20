from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import os

from auth_middleware import firebase_auth, get_current_user_id
from services.voice_agent import speech_to_text
import sys
import os

# Add parent directory to path to import config.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Processing"])

class TranscriptionResponse(BaseModel):
    status: str
    transcript: str
    confidence: Optional[float] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    metadata: dict

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
    Transcribe audio file to text
    
    - **file**: Audio file (WAV, MP3, FLAC, WEBM supported)
    - **language**: Language code for transcription (default: en-US)
    
    Supported formats: WAV, MP3, FLAC, WEBM
    Maximum file size: 10MB
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        # Validate file
        if not file:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Check file size
        content = await file.read()
        file_size = len(content)
        
        if file_size > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE} bytes"
            )
        
        if file_size < 1024:  # Less than 1KB
            raise HTTPException(
                status_code=400,
                detail="File too small or corrupted"
            )
        
        # Check file extension
        file_extension = file.filename.split('.')[-1].lower() if file.filename else ''
        if file_extension not in config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        logger.info(f"Transcribing audio for user {user_id}: {file.filename} ({file_size} bytes)")
        
        # Reset file pointer
        await file.seek(0)
        audio_bytes = await file.read()
        
        # Transcribe audio
        result = speech_to_text(
            audio_bytes=audio_bytes,
            language=language,
            file_extension=file_extension
        )
        
        logger.info(f"Successfully transcribed audio for user {user_id}")
        
        return TranscriptionResponse(
            status="success",
            transcript=result.get("transcript", ""),
            confidence=result.get("confidence"),
            language=result.get("language", language),
            duration=result.get("duration"),
            metadata={
                "user_id": user_id,
                "filename": file.filename,
                "file_size": file_size,
                "file_extension": file_extension,
                "language_requested": language,
                "processed_at": datetime.utcnow().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio for user {user_id if 'user_id' in locals() else 'unknown'}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio: {str(e)}"
        )

@router.get("/supported-formats",
           summary="Get Supported Audio Formats",
           description="Get list of supported audio formats and limits")
async def get_supported_formats():
    """Get supported audio formats and file limits"""
    return {
        "status": "success",
        "supported_formats": config.ALLOWED_EXTENSIONS,
        "max_file_size": config.MAX_FILE_SIZE,
        "max_file_size_mb": round(config.MAX_FILE_SIZE / (1024 * 1024), 2),
        "supported_languages": [
            "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", 
            "pt-BR", "ru-RU", "ja-JP", "ko-KR", "zh-CN"
        ],
        "recommendations": {
            "preferred_format": "WAV",
            "sample_rate": "16kHz or 48kHz",
            "bit_depth": "16-bit",
            "channels": "Mono preferred, Stereo supported"
        }
    }

@router.get("/health",
           summary="Voice Service Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for the voice service"""
    return {
        "status": "healthy",
        "service": "voice",
        "message": "Voice processing service is running properly",
        "features": ["speech_to_text"],
        "supported_formats": config.ALLOWED_EXTENSIONS,
        "max_file_size_mb": round(config.MAX_FILE_SIZE / (1024 * 1024), 2)
    }
