from fastapi import APIRouter, UploadFile, Depends, HTTPException, File, Header
from services.voice_assistant_service import process_voice_command
from firebase_config import verify_token
import os

router = APIRouter(prefix="/voice-assistant", tags=["Voice Assistant"])

async def get_current_user(authorization: str = Header(None)):
    """Dependency to verify Firebase token from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return user

@router.post("/speech-to-text-and-speech")
async def handle_voice_command(file: UploadFile = File(...), user=Depends(get_current_user)):
    """
    Accepts teacher's voice input and responds with AI-generated voice + text.
    """
    try:
        result = await process_voice_command(file)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "status": "success",
            "data": {
                "transcript": result["transcript"],
                "ai_response": result["ai_response"],
                "audio_file_path": result["audio_file_path"],
                "audio_filename": result.get("audio_filename", None),
                "download_url": f"/voice-assistant/download-audio/{result.get('audio_filename', '')}" if result.get('audio_filename') else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")

@router.get("/download-audio/{filename}")
async def download_audio_response(filename: str, user=Depends(get_current_user)):
    """
    Download the generated audio response file.
    """
    from fastapi.responses import FileResponse
    
    # Look for file in the audio files directory
    audio_files_dir = os.path.join(os.getcwd(), "temp_audio")
    file_path = os.path.join(audio_files_dir, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename=filename
    )
