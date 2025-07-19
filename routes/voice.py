from fastapi import APIRouter, UploadFile, File, Depends
from auth_middleware import firebase_auth
from services.voice_agent import speech_to_text

router = APIRouter(prefix="/voice", tags=["Voice Agent"])

@router.post("/transcribe", dependencies=[Depends(firebase_auth)])
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    transcript = speech_to_text(audio_bytes)
    return {"transcript": transcript}
