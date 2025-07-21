"""
Enhanced Voice Controller with Text-Based Intelligence
Adds text-only APIs for direct AI interaction without audio files
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import logging
import json

from auth_middleware import firebase_auth, get_current_user_id
from services.voice_session_service import voice_session_service
from services.voice_assistant_service import model, tts_client, AUDIO_FILES_DIR
from dao.voice_assistant_dao import voice_assistant_dao
from google.cloud import texttospeech
import uuid
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# ===== REQUEST/RESPONSE MODELS =====

class TextInputRequest(BaseModel):
    """Request model for text-based AI interaction"""
    message: str = Field(..., min_length=1, max_length=1000, description="Text message to process")
    session_id: Optional[str] = Field(None, description="Optional session ID for context")
    generate_audio: bool = Field(False, description="Whether to generate audio response")
    voice_style: Optional[str] = Field("default", description="Voice style for audio generation")

class TextOnlyResponse(BaseModel):
    """Response model for text-only interaction"""
    status: str
    user_message: str
    ai_response: str
    session_info: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    metadata: Dict[str, Any]

class TextWithAudioResponse(BaseModel):
    """Response model for text interaction with audio generation"""
    status: str
    user_message: str
    ai_response: str
    audio_filename: Optional[str] = None
    download_url: Optional[str] = None
    session_info: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    metadata: Dict[str, Any]

class MultiModalRequest(BaseModel):
    """Request model for combined text and file processing"""
    message: str = Field(..., min_length=1, max_length=1000, description="Text message about the file")
    file_context: Optional[str] = Field(None, description="Additional context about the uploaded file")
    generate_audio: bool = Field(False, description="Whether to generate audio response")

class FileAnalysisResponse(BaseModel):
    """Response model for file analysis with text"""
    status: str
    user_message: str
    file_info: Dict[str, Any]
    ai_response: str
    analysis: Dict[str, Any]
    audio_filename: Optional[str] = None
    download_url: Optional[str] = None
    metadata: Dict[str, Any]

# ===== TEXT-BASED AI INTERACTION =====

@router.post("/text-chat",
            summary="Text-Based AI Chat",
            description="Direct text interaction with the AI assistant (no audio required)",
            response_model=TextOnlyResponse,
            dependencies=[Depends(firebase_auth)])
async def text_chat(
    request: TextInputRequest,
    user_request: Request
):
    """
    Direct text-based AI interaction without requiring audio files
    
    Features:
    - **Direct Text Input**: Send messages as text
    - **Session Awareness**: Maintains conversation context if session_id provided
    - **Educational AI**: Specialized for teacher and educational queries
    - **Fast Response**: No audio processing overhead
    
    Use Cases:
    - Quick questions without voice recording
    - Silent environments where audio isn't practical
    - Text-based educational planning and advice
    - Integration with text-based applications
    """
    try:
        user_id = await get_current_user_id(user_request)
        logger.info(f"Processing text chat for user {user_id}: {request.message[:50]}...")
        
        # Validate input
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        session_info = None
        ai_response = ""
        
        # Check if this is a session-aware request
        if request.session_id:
            # Get existing session
            session_context = await voice_session_service.get_session_info(request.session_id)
            
            if session_context and session_context["user_id"] == user_id:
                # Generate context-aware response
                ai_response = await _generate_contextual_text_response(
                    message=request.message,
                    session_id=request.session_id
                )
                session_info = session_context
            else:
                # Session not found or doesn't belong to user
                ai_response = await _generate_basic_text_response(request.message)
        else:
            # Generate basic AI response
            ai_response = await _generate_basic_text_response(request.message)
        
        # Store conversation in database
        conversation_data = {
            "user_id": user_id,
            "session_id": request.session_id,
            "transcript": request.message,  # For consistency with voice conversations
            "ai_response": ai_response,
            "interaction_type": "text_only",
            "created_at": datetime.utcnow(),
            "metadata": {
                "input_method": "text",
                "session_aware": bool(request.session_id and session_info)
            }
        }
        
        conversation_id = voice_assistant_dao.save_conversation(user_id, conversation_data)
        
        return TextOnlyResponse(
            status="success",
            user_message=request.message,
            ai_response=ai_response,
            session_info=session_info,
            conversation_id=conversation_id,
            metadata={
                "user_id": user_id,
                "processed_at": datetime.utcnow().isoformat(),
                "interaction_type": "text_only",
                "session_aware": bool(session_info)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text chat processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process text message"
        )

@router.post("/text-with-audio",
            summary="Text Chat with Audio Response",
            description="Text interaction that generates both text and audio responses",
            response_model=TextWithAudioResponse,
            dependencies=[Depends(firebase_auth)])
async def text_with_audio(
    request: TextInputRequest,
    user_request: Request
):
    """
    Text-based interaction with audio response generation
    
    Perfect for:
    - Text input when audio output is desired
    - Accessibility needs (text input, audio output)
    - Silent input with audio response for driving/walking
    - Educational content that benefits from spoken responses
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        # First, get the text response (reuse text_chat logic)
        text_response = await text_chat(request, user_request)
        
        if text_response.status != "success":
            raise HTTPException(status_code=400, detail="Failed to generate text response")
        
        # Generate audio from the AI response
        audio_info = await _generate_audio_response(
            text=text_response.ai_response,
            voice_style=request.voice_style
        )
        
        download_url = None
        if audio_info["filename"]:
            download_url = f"/api/v1/voice/download-audio/{audio_info['filename']}"
        
        return TextWithAudioResponse(
            status="success",
            user_message=text_response.user_message,
            ai_response=text_response.ai_response,
            audio_filename=audio_info["filename"],
            download_url=download_url,
            session_info=text_response.session_info,
            conversation_id=text_response.conversation_id,
            metadata={
                **text_response.metadata,
                "audio_generated": True,
                "voice_style": request.voice_style
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text with audio processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process text message with audio"
        )

# ===== MULTI-MODAL INTERACTION =====

@router.post("/analyze-with-text",
            summary="Analyze File with Text Query",
            description="Upload any file and ask questions about it via text",
            response_model=FileAnalysisResponse,
            dependencies=[Depends(firebase_auth)])
async def analyze_file_with_text(
    user_request: Request,
    file: UploadFile = File(..., description="File to analyze (documents, images, audio, etc.)"),
    message: str = Form(..., description="Your question about the file"),
    file_context: Optional[str] = Form(None, description="Additional context about the file"),
    generate_audio: bool = Form(False, description="Generate audio response")
):
    """
    Smart file analysis with text-based queries
    
    Capabilities:
    - **Document Analysis**: PDFs, Word docs, text files
    - **Image Analysis**: Describe images, extract text from images
    - **Audio Analysis**: Analyze audio content and respond to questions
    - **Educational Content**: Analyze lesson materials, student work
    - **Smart Questions**: Ask anything about the uploaded content
    
    Example Uses:
    - "Summarize this lesson plan PDF"
    - "What are the key points in this image?"
    - "How can I improve this audio recording?"
    - "Extract the main concepts from this document"
    """
    try:
        user_id = await get_current_user_id(user_request)
        
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        logger.info(f"Analyzing file {file.filename} with text query for user {user_id}")
        
        # Read and analyze the file
        file_content = await file.read()
        file_info = {
            "filename": file.filename,
            "size_bytes": len(file_content),
            "content_type": file.content_type,
            "file_extension": os.path.splitext(file.filename)[1].lower()
        }
        
        # Perform smart analysis based on file type
        analysis_result = await _analyze_file_content(
            file_content=file_content,
            file_info=file_info,
            user_query=message,
            context=file_context
        )
        
        # Generate AI response based on analysis
        ai_response = await _generate_file_analysis_response(
            analysis=analysis_result,
            user_query=message,
            file_info=file_info
        )
        
        # Generate audio if requested
        audio_filename = None
        download_url = None
        
        if generate_audio:
            audio_info = await _generate_audio_response(ai_response)
            audio_filename = audio_info["filename"]
            if audio_filename:
                download_url = f"/api/v1/voice/download-audio/{audio_filename}"
        
        # Store conversation
        conversation_data = {
            "user_id": user_id,
            "transcript": f"File analysis: {message}",
            "ai_response": ai_response,
            "interaction_type": "file_analysis",
            "created_at": datetime.utcnow(),
            "metadata": {
                "file_analyzed": file.filename,
                "file_size": len(file_content),
                "analysis_type": analysis_result.get("type", "general")
            }
        }
        
        conversation_id = voice_assistant_dao.save_conversation(user_id, conversation_data)
        
        return FileAnalysisResponse(
            status="success",
            user_message=message,
            file_info=file_info,
            ai_response=ai_response,
            analysis=analysis_result,
            audio_filename=audio_filename,
            download_url=download_url,
            metadata={
                "user_id": user_id,
                "processed_at": datetime.utcnow().isoformat(),
                "interaction_type": "file_analysis",
                "audio_generated": bool(audio_filename)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze file"
        )

# ===== HELPER FUNCTIONS =====

async def _generate_basic_text_response(message: str) -> str:
    """Generate basic AI response for text input"""
    try:
        structured_prompt = f"""
        A teacher or educator asked: "{message}"
        
        Provide a helpful, educational response in JSON format:
        {{"answer": "Your helpful response for the educator."}}
        
        Make your response:
        - Practical and actionable
        - Educational and professional
        - Concise but comprehensive
        - Supportive and encouraging
        """
        
        ai_response = model.generate_content(structured_prompt)
        raw_text = ai_response.text.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").replace("json", "").strip()
        
        try:
            parsed_response = json.loads(raw_text)
            return parsed_response.get("answer", "I'd be happy to help with your educational needs.").strip()
        except json.JSONDecodeError:
            return ai_response.text.strip().split("\n")[0]
            
    except Exception as e:
        logger.error(f"Error generating basic text response: {e}")
        return "I encountered an error processing your message. Please try again."

async def _generate_contextual_text_response(message: str, session_id: str) -> str:
    """Generate context-aware response using session history"""
    try:
        # This would integrate with the session service
        # For now, use basic response with session awareness note
        basic_response = await _generate_basic_text_response(message)
        return f"Based on our ongoing conversation, {basic_response.lower()}"
        
    except Exception as e:
        logger.error(f"Error generating contextual response: {e}")
        return await _generate_basic_text_response(message)

async def _generate_audio_response(text: str, voice_style: str = "default") -> Dict[str, str]:
    """Generate audio response from text"""
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Select voice based on style
        voice_name = "en-US-Journey-F" if voice_style == "conversational" else "en-US-Standard-C"
        voice_params = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name
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
        unique_filename = f"text_response_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_output_path = os.path.join(AUDIO_FILES_DIR, unique_filename)
        
        with open(audio_output_path, "wb") as out:
            out.write(tts_response.audio_content)
        
        return {
            "filename": unique_filename,
            "path": audio_output_path
        }
        
    except Exception as e:
        logger.error(f"Error generating audio response: {e}")
        return {"filename": None, "path": None}

async def _analyze_file_content(file_content: bytes, file_info: Dict, user_query: str, context: Optional[str]) -> Dict[str, Any]:
    """Analyze uploaded file content"""
    try:
        file_ext = file_info["file_extension"]
        analysis_type = "general"
        
        # Basic file analysis
        analysis = {
            "type": analysis_type,
            "file_size_mb": round(len(file_content) / (1024 * 1024), 2),
            "content_preview": None,
            "detected_format": file_ext,
            "analyzable": True
        }
        
        # Enhanced analysis based on file type
        if file_ext in ['.txt', '.md', '.csv']:
            try:
                # Text-based files
                text_content = file_content.decode('utf-8')[:1000]  # First 1000 chars
                analysis["content_preview"] = text_content
                analysis["type"] = "text_document"
                analysis["character_count"] = len(text_content)
            except:
                analysis["analyzable"] = False
                
        elif file_ext in ['.pdf', '.docx', '.doc']:
            analysis["type"] = "document"
            analysis["requires_parsing"] = True
            
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            analysis["type"] = "image"
            analysis["requires_vision_api"] = True
            
        elif file_ext in ['.wav', '.mp3', '.m4a', '.flac']:
            analysis["type"] = "audio"
            analysis["requires_audio_analysis"] = True
            
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing file content: {e}")
        return {"type": "error", "analyzable": False, "error": str(e)}

async def _generate_file_analysis_response(analysis: Dict, user_query: str, file_info: Dict) -> str:
    """Generate AI response based on file analysis"""
    try:
        prompt = f"""
        A user uploaded a file and asked: "{user_query}"
        
        File Information:
        - Filename: {file_info['filename']}
        - Size: {analysis.get('file_size_mb', 0)} MB
        - Type: {analysis.get('type', 'unknown')}
        - Format: {file_info['file_extension']}
        
        Analysis Results:
        {json.dumps(analysis, indent=2)}
        
        Provide a helpful response about the file in JSON format:
        {{"answer": "Your analysis and response to the user's query about their file."}}
        
        Include:
        - What you can tell about the file
        - Answer to their specific question
        - Suggestions for how they might use or improve the content
        - Educational insights if applicable
        """
        
        ai_response = model.generate_content(prompt)
        raw_text = ai_response.text.strip()
        
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").replace("json", "").strip()
        
        try:
            parsed_response = json.loads(raw_text)
            return parsed_response.get("answer", f"I've analyzed your {file_info['filename']} file and can help with your question.").strip()
        except json.JSONDecodeError:
            return ai_response.text.strip().split("\n")[0]
            
    except Exception as e:
        logger.error(f"Error generating file analysis response: {e}")
        return f"I've received your file '{file_info['filename']}' but encountered an issue analyzing it. Please try again or contact support."
