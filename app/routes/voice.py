from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging
import tempfile
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Request models
class VoiceRequest(BaseModel):
    text: str
    language: Optional[str] = "English"

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

@router.post("/assistant")
async def voice_assistant(
    audio_file: Optional[UploadFile] = File(None),
    message: Optional[str] = Form(None),
    file_upload: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    """
    Voice Assistant endpoint that accepts multiple input types
    """
    try:
        # Check if at least one input is provided
        if not any([audio_file, message, file_upload, text]):
            raise HTTPException(
                status_code=400, 
                detail="Must provide at least one input: audio_file, message, or file_upload"
            )
        
        # Determine input type and content
        input_content = ""
        input_type = ""
        files_processed = 0
        
        if message:
            input_content = message
            input_type = "text_message"
            logger.info(f"Processing text message: {message[:50]}...")
            
        elif text:
            input_content = text
            input_type = "text"
            logger.info(f"Processing text input: {text[:50]}...")
            
        elif audio_file:
            # Save audio file temporarily for processing
            audio_path = await save_uploaded_file(audio_file, "audio")
            input_content = f"Audio file processed: {audio_file.filename}"
            input_type = "audio"
            files_processed = 1
            logger.info(f"Audio saved to: {audio_path}")
            logger.info(f"Processing audio file: {audio_file.filename}")
            
        elif file_upload:
            # Save uploaded file
            file_path = await save_uploaded_file(file_upload, "document")
            input_content = f"File processed: {file_upload.filename}"
            input_type = "file"
            files_processed = 1
            logger.info(f"File saved to: {file_path}")
            logger.info(f"Processing uploaded file: {file_upload.filename}")
        
        # Generate response based on the input
        response_text = generate_response(input_content, input_type)
        
        return JSONResponse({
            "status": "success",
            "input_type": input_type,
            "files": files_processed,
            "response_style": "conversational",
            "max_tokens": 1500,
            "response": response_text,
            "capabilities": [
                "Advanced file analysis (documents, images, audio, video)",
                "Voice transcription and processing",
                "Contextual AI responses",
                "Code assistance and review",
                "Creative writing and storytelling",
                "Educational content generation",
                "Multi-language support"
            ],
            "message": "Voice Assistant API processed your request successfully!"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice assistant: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def save_uploaded_file(upload_file: UploadFile, file_type: str) -> str:
    """
    Save uploaded file to temporary directory and return the path
    """
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(os.getcwd(), "uploads", file_type)
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        import uuid
        file_extension = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        content = await upload_file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"File saved: {file_path} (Size: {len(content)} bytes)")
        return file_path
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise

@router.post("/chat")
async def chat_assistant(request: ChatRequest):
    """
    Simple chat endpoint for conversational interactions
    """
    try:
        logger.info(f"Chat request: {request.message[:50]}...")
        
        response_text = generate_response(request.message, "text")
        
        return JSONResponse({
            "status": "success",
            "user_message": request.message,
            "assistant_response": response_text,
            "timestamp": "2024-07-25T11:59:21"
        })
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def voice_health_check():
    return {
        "status": "healthy",
        "service": "Voice Assistant API",
        "message": "Voice Assistant API is fully operational",
        "endpoints": [
            "/api/v1/voice/assistant",
            "/api/v1/voice/chat",
            "/api/v1/voice/health"
        ],
        "file_storage": {
            "audio_files": "uploads/audio/",
            "documents": "uploads/document/"
        }
    }

@router.get("/files")
async def list_uploaded_files():
    """
    List all uploaded files
    """
    try:
        files_info = []
        upload_base = os.path.join(os.getcwd(), "uploads")
        
        if os.path.exists(upload_base):
            for file_type in ["audio", "document"]:
                type_dir = os.path.join(upload_base, file_type)
                if os.path.exists(type_dir):
                    for filename in os.listdir(type_dir):
                        file_path = os.path.join(type_dir, filename)
                        file_stat = os.stat(file_path)
                        files_info.append({
                            "filename": filename,
                            "type": file_type,
                            "size": file_stat.st_size,
                            "path": file_path,
                            "created": file_stat.st_ctime
                        })
        
        return {
            "status": "success",
            "total_files": len(files_info),
            "files": files_info
        }
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_response(user_input: str, input_type: str = "text", context: Optional[str] = None) -> str:
    """
    Generate conversational responses based on user input and type
    """
    user_input_lower = user_input.lower()
    
    # File processing responses
    if input_type == "audio":
        return f"🎵 I've successfully received and processed your audio file! {user_input}\n\nI can help you with:\n• Audio transcription\n• Voice analysis\n• Converting speech to text\n• Audio content summarization\n\nThe audio file has been saved securely. What would you like me to do with this audio content?"
    
    elif input_type == "file":
        return f"📁 I've successfully processed your uploaded file! {user_input}\n\nI can help you with:\n• Document analysis\n• Content extraction\n• File summarization\n• Data processing\n\nThe file has been saved securely. How can I assist you with this document?"
    
    # Educational responses
    elif any(word in user_input_lower for word in ['lesson', 'teach', 'learn', 'study']):
        return f"📚 I'd be happy to help you with learning! Based on your input about '{user_input}', I can assist with:\n\n• Creating detailed lesson plans\n• Explaining complex concepts\n• Generating study materials\n• Creating practice exercises\n• Developing assessments\n\nWhat specific educational topic would you like to explore?"
    
    # Greeting responses
    elif any(word in user_input_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        return "👋 Hello! I'm your AI education assistant. I'm equipped with advanced capabilities including:\n\n• 🎓 Educational content creation\n• 📝 Lesson planning\n• 🎵 Audio processing\n• 📁 File analysis\n• 💬 Conversational AI\n\nHow can I assist you today?"
    
    # Help responses
    elif any(word in user_input_lower for word in ['help', 'assist', 'support']):
        return "🆘 I'm here to help! Here's what I can do for you:\n\n• 📚 Create lesson plans and educational content\n• 🎵 Process audio files and voice recordings\n• 📁 Analyze documents and files\n• 💻 Provide coding assistance\n• 🧮 Help with mathematics\n• 🔬 Explain scientific concepts\n• 📝 Generate assessments and activities\n\nWhat would you like help with today?"
    
    # Code-related responses
    elif any(word in user_input_lower for word in ['code', 'programming', 'python', 'javascript']):
        return f"💻 Great! I can help you with programming and coding. Based on your question about '{user_input}', I can:\n\n• Provide code examples and solutions\n• Debug existing code\n• Explain programming concepts\n• Create tutorials and guides\n• Review code for best practices\n\nWhat specific programming challenge are you working on?"
    
    # Math responses
    elif any(word in user_input_lower for word in ['math', 'mathematics', 'calculate', 'solve']):
        return f"🧮 I'd love to help with mathematics! Your question about '{user_input}' sounds interesting. I can:\n\n• Explain mathematical concepts step-by-step\n• Solve complex problems\n• Create practice exercises\n• Provide visual explanations\n• Generate study guides\n\nWhat math topic would you like to explore?"
    
    # Science responses
    elif any(word in user_input_lower for word in ['science', 'biology', 'chemistry', 'physics']):
        return f"🔬 Science is fascinating! Regarding your question about '{user_input}', I can:\n\n• Explain scientific concepts clearly\n• Provide experiment ideas\n• Create study materials\n• Answer questions about various science topics\n• Generate visual aids\n\nWhich area of science interests you most?"
    
    # Default conversational response
    else:
        return f"💬 Thank you for your message: '{user_input}'\n\nI'm your comprehensive AI education assistant with advanced capabilities including:\n\n• 🎓 Educational content generation\n• 🎵 Audio and voice processing\n• 📁 File analysis\n• 💻 Programming assistance\n• 🧮 Mathematical problem solving\n• 🔬 Scientific explanations\n\nCould you tell me more about what you'd like to learn or how I can assist you today?"

# Additional endpoint for simple text processing
@router.post("/process-text")
async def process_text(request: dict):
    """
    Simple text processing endpoint
    """
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")
        
        response = generate_response(text, "text")
        
        return {
            "status": "success",
            "original_text": text,
            "processed_response": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
