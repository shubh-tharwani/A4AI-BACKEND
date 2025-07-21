"""
Unified Voice Controller - Combines all voice and text-based AI capabilities
Handles both traditional voice processing and modern text-based interactions
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Union
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
    # Fallback initialization
    vertex_ai_service = None
voice_dao = VoiceAssistantDAO()

router = APIRouter()
logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class TextChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    message: str = Field(..., description="User's text message/question")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    response_format: str = Field("text", description="Response format: 'text' or 'audio' or 'both'")

class VoiceProcessingRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    session_id: Optional[str] = Field(None, description="Session ID for context awareness")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    response_format: str = Field("audio", description="Response format: 'text' or 'audio' or 'both'")

class FileAnalysisRequest(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user")
    query: str = Field(..., description="Question about the uploaded file")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    response_format: str = Field("text", description="Response format: 'text' or 'audio' or 'both'")

class UnifiedResponse(BaseModel):
    status: str
    user_id: str
    session_id: Optional[str] = None
    input_type: str  # "voice", "text", "file"
    transcript: Optional[str] = None
    ai_response: str
    audio_file_path: Optional[str] = None
    audio_filename: Optional[str] = None
    file_analysis: Optional[Dict[str, Any]] = None
    conversation_context: Optional[Dict[str, Any]] = None
    processing_time: float
    timestamp: str

# ============================================================================
# UNIFIED VOICE/TEXT PROCESSING ENDPOINTS
# ============================================================================

@router.post("/unified-assistant",
             response_model=UnifiedResponse,
             summary="Unified Voice/Text Assistant",
             description="Single endpoint that handles both voice and text inputs with flexible response formats")
async def unified_assistant(
    request: Request,
    user_data: dict = Depends(verify_token),
    # Voice input (optional)
    audio_file: Optional[UploadFile] = File(None),
    # Text input (optional)  
    message: Optional[str] = Form(None),
    # File input (optional)
    file_upload: Optional[UploadFile] = File(None),
    # Common parameters
    user_id: str = Form(...),
    session_id: Optional[str] = Form(None),
    response_format: str = Form("auto"),  # "text", "audio", "both", "auto"
    context: str = Form("{}")
):
    """
    Unified endpoint that intelligently processes:
    - Voice input (audio file) → Speech-to-text → AI response
    - Text input (message) → Direct AI response  
    - File input (any file) + query → File analysis + AI response
    - Any combination of the above
    
    Response format automatically determined or explicitly specified.
    """
    start_time = datetime.now()
    
    try:
        # Parse context
        import json
        try:
            context_dict = json.loads(context)
        except:
            context_dict = {}
        
        # Determine input type and processing strategy
        has_audio = audio_file is not None
        has_text = message is not None and message.strip()
        has_file = file_upload is not None
        
        if not (has_audio or has_text or has_file):
            raise HTTPException(status_code=400, detail="Must provide audio, text message, or file input")
        
        # Initialize response data
        transcript = None
        ai_response = ""
        audio_file_path = None
        audio_filename = None
        file_analysis = None
        input_type = "unknown"
        
        # Process based on input type(s)
        if has_audio:
            logger.info(f"Processing voice input for user {user_id}")
            input_type = "voice"
            
            # Use session-aware processing if session_id provided
            if session_id:
                voice_result = await voice_session_service.process_session_voice_command(
                    audio_file, user_id, session_id, context_dict
                )
            else:
                # Use traditional voice processing
                voice_result = await process_voice_command(audio_file)
            
            transcript = voice_result.get("transcript", "")
            ai_response = voice_result.get("ai_response", "")
            
            # If audio response requested and not already generated
            if response_format in ["audio", "both", "auto"] and not voice_result.get("audio_file_path"):
                audio_result = await _generate_audio_response(ai_response)
                audio_file_path = audio_result.get("audio_file_path")
                audio_filename = audio_result.get("audio_filename")
            else:
                audio_file_path = voice_result.get("audio_file_path")
                audio_filename = voice_result.get("audio_filename")
        
        elif has_text:
            logger.info(f"Processing text input for user {user_id}: {message[:50]}...")
            input_type = "text"
            
            # Use session-aware text processing
            if session_id:
                text_result = await voice_session_service.process_session_text_command(
                    message, user_id, session_id, context_dict
                )
                ai_response = text_result.get("ai_response", "")
            else:
                # Direct AI processing
                ai_response = await _process_text_with_ai(message, context_dict)
            
            # Generate audio if requested
            if response_format in ["audio", "both"]:
                audio_result = await _generate_audio_response(ai_response)
                audio_file_path = audio_result.get("audio_file_path")
                audio_filename = audio_result.get("audio_filename")
        
        elif has_file:
            logger.info(f"Processing file input for user {user_id}")
            input_type = "file"
            
            # Determine query text
            query_text = message if has_text else "Analyze this file and provide insights."
            
            # Process file with AI analysis
            file_result = await _process_file_with_ai(file_upload, query_text, context_dict)
            ai_response = file_result.get("ai_response", "")
            file_analysis = file_result.get("analysis", {})
            
            # Generate audio if requested
            if response_format in ["audio", "both"]:
                audio_result = await _generate_audio_response(ai_response)
                audio_file_path = audio_result.get("audio_file_path")
                audio_filename = audio_result.get("audio_filename")
        
        # Get conversation context if session exists
        conversation_context = None
        if session_id:
            try:
                context_result = await voice_session_service.get_conversation_context(user_id, session_id)
                conversation_context = context_result
            except Exception as e:
                logger.warning(f"Could not retrieve conversation context: {e}")
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Store conversation if successful
        if ai_response and session_id:
            try:
                await voice_dao.store_conversation_async(
                    user_id=user_id,
                    session_id=session_id,
                    transcript=transcript or message or "File processed",
                    ai_response=ai_response,
                    audio_file_path=audio_file_path,
                    metadata={
                        "input_type": input_type,
                        "processing_time": processing_time,
                        "response_format": response_format,
                        "has_file_analysis": file_analysis is not None
                    }
                )
            except Exception as e:
                logger.warning(f"Could not store conversation: {e}")
        
        return UnifiedResponse(
            status="success",
            user_id=user_id,
            session_id=session_id,
            input_type=input_type,
            transcript=transcript,
            ai_response=ai_response,
            audio_file_path=audio_file_path,
            audio_filename=audio_filename,
            file_analysis=file_analysis,
            conversation_context=conversation_context,
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in unified assistant: {str(e)}")
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return UnifiedResponse(
            status="error",
            user_id=user_id,
            session_id=session_id,
            input_type="unknown",
            ai_response=f"I encountered an error processing your request: {str(e)}",
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )

# ============================================================================
# TRADITIONAL VOICE ENDPOINTS (Backward Compatibility)
# ============================================================================

@router.post("/assistant", summary="Traditional Voice Assistant (Legacy)")
async def voice_assistant(
    audio_file: UploadFile = File(...),
    user_data: dict = Depends(verify_token)
):
    """Legacy voice assistant endpoint for backward compatibility"""
    result = await process_voice_command(audio_file)
    return JSONResponse(content=result)

@router.post("/session-assistant", summary="Session-Aware Voice Assistant")
async def session_voice_assistant(
    audio_file: UploadFile = File(...),
    request_data: VoiceProcessingRequest = Depends(),
    user_data: dict = Depends(verify_token)
):
    """Session-aware voice processing with conversation context"""
    try:
        result = await voice_session_service.process_session_voice_command(
            audio_file, 
            request_data.user_id, 
            request_data.session_id,
            request_data.context or {}
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Session voice processing error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)}, 
            status_code=500
        )

# ============================================================================
# TEXT-BASED ENDPOINTS
# ============================================================================

@router.post("/text-chat", summary="Text-Based AI Chat")
async def text_chat(
    request: TextChatRequest,
    user_data: dict = Depends(verify_token)
):
    """Direct text-to-AI conversation without audio processing"""
    try:
        if request.session_id:
            result = await voice_session_service.process_session_text_command(
                request.message,
                request.user_id,
                request.session_id,
                request.context
            )
        else:
            ai_response = await _process_text_with_ai(request.message, request.context)
            result = {
                "status": "success",
                "user_id": request.user_id,
                "ai_response": ai_response,
                "timestamp": datetime.now().isoformat()
            }
        
        # Generate audio if requested
        if request.response_format in ["audio", "both"]:
            audio_result = await _generate_audio_response(result["ai_response"])
            result.update(audio_result)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Text chat error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.post("/analyze-file", summary="File Analysis with Text Query")
async def analyze_file(
    file_upload: UploadFile = File(...),
    request: FileAnalysisRequest = Depends(),
    user_data: dict = Depends(verify_token)
):
    """Analyze uploaded files with text-based questions"""
    try:
        result = await _process_file_with_ai(
            file_upload, 
            request.query, 
            {"user_id": request.user_id}
        )
        
        response_data = {
            "status": "success",
            "user_id": request.user_id,
            "session_id": request.session_id,
            "query": request.query,
            "ai_response": result["ai_response"],
            "file_analysis": result["analysis"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Generate audio if requested
        if request.response_format in ["audio", "both"]:
            audio_result = await _generate_audio_response(result["ai_response"])
            response_data.update(audio_result)
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/audio/{filename}", summary="Download Generated Audio")
async def download_audio(filename: str):
    """Download generated audio files"""
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

@router.get("/sessions/{user_id}", summary="Get User Sessions")
async def get_user_sessions(user_id: str, user_data: dict = Depends(verify_token)):
    """Retrieve all sessions for a user"""
    try:
        sessions = await voice_dao.get_user_conversations_async(user_id)
        return JSONResponse(content={"sessions": sessions})
    except Exception as e:
        logger.error(f"Get sessions error: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

@router.get("/health", summary="Voice Service Health Check")
async def health_check():
    """Health check for voice services"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "unified-voice-assistant",
        "capabilities": [
            "voice-processing",
            "text-chat", 
            "file-analysis",
            "session-management",
            "audio-generation"
        ],
        "timestamp": datetime.now().isoformat()
    })

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _process_text_with_ai(message: str, context: Dict[str, Any]) -> str:
    """Process text message with AI and return response"""
    try:
        # Create educational prompt
        prompt = f"""
        As an AI educational assistant, please respond to this message: "{message}"
        
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
            # Fallback response
            return f"I understand you're asking about: {message}. I'm here to help with your educational questions!"
    except Exception as e:
        logger.error(f"AI text processing error: {str(e)}")
        return "I'm having trouble processing your request right now. Please try again."

async def _generate_audio_response(text: str) -> Dict[str, Any]:
    """Generate audio from text response"""
    try:
        from google.cloud import texttospeech
        
        tts_client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )
        
        # Save audio file
        audio_dir = os.path.join(os.getcwd(), "temp_audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        unique_filename = f"response_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_path = os.path.join(audio_dir, unique_filename)
        
        with open(audio_path, "wb") as out:
            out.write(response.audio_content)
        
        return {
            "audio_file_path": audio_path,
            "audio_filename": unique_filename
        }
        
    except Exception as e:
        logger.error(f"Audio generation error: {str(e)}")
        return {
            "audio_file_path": None,
            "audio_filename": None
        }

async def _process_file_with_ai(file_upload: UploadFile, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process uploaded file with AI analysis"""
    try:
        # Read file content
        content = await file_upload.read()
        file_type = file_upload.content_type or "unknown"
        file_size = len(content)
        
        # Basic file analysis
        analysis = {
            "filename": file_upload.filename,
            "file_type": file_type,
            "file_size": file_size,
            "analysis_type": "content_analysis"
        }
        
        # Process based on file type
        if file_type.startswith("text/") or file_upload.filename.endswith((".txt", ".md")):
            # Text file processing
            text_content = content.decode("utf-8")
            prompt = f"""
            Analyze this text file and answer the question: "{query}"
            
            File content:
            {text_content[:2000]}...
            
            Provide a helpful analysis and answer to the question.
            """
            analysis["analysis_type"] = "text_analysis"
            
        elif file_type.startswith("image/"):
            # Image analysis (would need vision API integration)
            prompt = f"""
            I have an image file uploaded. The user asks: "{query}"
            
            Unfortunately, I cannot process images directly in this context, 
            but I can help you understand that this appears to be an image file 
            of type {file_type}. Please describe what you'd like to know about the image.
            """
            analysis["analysis_type"] = "image_analysis"
            
        else:
            # Generic file processing
            prompt = f"""
            I have a file of type {file_type} ({file_size} bytes). 
            The user asks: "{query}"
            
            Based on the file type and size, I can provide general information 
            and guidance about this type of file. How can I help you with this file?
            """
            analysis["analysis_type"] = "generic_analysis"
        
        # Generate AI response
        if vertex_ai_service:
            ai_response = await vertex_ai_service.generate_content_async(prompt)
        else:
            ai_response = f"I can help you analyze this {file_type} file. Please describe what specific information you're looking for."
        
        return {
            "ai_response": ai_response.strip(),
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        return {
            "ai_response": f"I encountered an error analyzing the file: {str(e)}",
            "analysis": {
                "filename": file_upload.filename if file_upload else "unknown",
                "error": str(e)
            }
        }
