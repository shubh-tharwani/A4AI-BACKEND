import os
import tempfile
import uuid
from datetime import datetime
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
import vertexai
from vertexai.generative_models import GenerativeModel
from config import GOOGLE_GEMINI_MODEL, PROJECT_ID, LOCATION, GOOGLE_APPLICATION_CREDENTIALS

# Set credentials before initializing Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Create audio files directory
AUDIO_FILES_DIR = os.path.join(os.getcwd(), "temp_audio")
os.makedirs(AUDIO_FILES_DIR, exist_ok=True)

# Initialize clients once for better performance
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()
model = GenerativeModel(GOOGLE_GEMINI_MODEL)

async def process_voice_command(audio_file) -> dict:
    """
    Process teacher's voice command: Speech-to-Text -> Intent Analysis -> Text-to-Speech
    """
    audio_path = None
    
    try:
        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(await audio_file.read())
            audio_path = temp_audio.name

        # --- STEP 1: Speech-to-Text ---
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
    language_code="en-US",
    enable_automatic_punctuation=True,
    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
    sample_rate_hertz=16000
)


        response = speech_client.recognize(config=config, audio=audio)
        
        # Handle case where no speech is detected
        if not response.results:
            transcript = "No speech detected."
        else:
            transcript = response.results[0].alternatives[0].transcript

        # --- STEP 2: Intent Understanding using Gemini ---
        prompt = f"Teacher said: '{transcript}'. Identify intent and respond as a helpful teaching assistant. Give ONLY a short helpful response for the teacher in plain text. Do NOT explain your reasoning or give multiple scenarios."

        # Use the new Vertex AI Generative Models API
        ai_response = model.generate_content(prompt)
        response_text = ai_response.text

        # --- STEP 3: Convert AI Response to Speech ---
        synthesis_input = texttospeech.SynthesisInput(text=response_text)
        voice_params = texttospeech.VoiceSelectionParams(language_code="en-US")
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice_params, audio_config=audio_config
        )

        # Save TTS output with unique filename
        unique_filename = f"ai_response_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_output_path = os.path.join(AUDIO_FILES_DIR, unique_filename)
        with open(audio_output_path, "wb") as out:
            out.write(tts_response.audio_content)

        return {
            "transcript": transcript,
            "ai_response": response_text,
            "audio_file_path": audio_output_path,
            "audio_filename": unique_filename  # Add filename for download endpoint
        }
    
    except Exception as e:
        return {
            "transcript": "Error processing audio",
            "ai_response": f"Sorry, I encountered an error: {str(e)}",
            "audio_file_path": None,
            "error": str(e)
        }
    
    finally:
        # Clean up temporary file
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass  # Ignore cleanup errors
