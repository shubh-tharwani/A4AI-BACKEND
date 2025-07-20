import os
import tempfile
import uuid
import json
from datetime import datetime
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
import vertexai
from vertexai.generative_models import GenerativeModel
from config import GOOGLE_GEMINI_MODEL, PROJECT_ID, LOCATION, GOOGLE_APPLICATION_CREDENTIALS

# Set Google credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Directory for saving generated audio files
AUDIO_FILES_DIR = os.path.join(os.getcwd(), "temp_audio")
os.makedirs(AUDIO_FILES_DIR, exist_ok=True)

# Initialize clients once
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()
model = GenerativeModel(GOOGLE_GEMINI_MODEL)

# Detect encoding based on extension
def get_audio_encoding(file_extension):
    ext = file_extension.lower()
    if ext in ["wav", "linear16"]:
        return speech.RecognitionConfig.AudioEncoding.LINEAR16
    elif ext == "flac":
        return speech.RecognitionConfig.AudioEncoding.FLAC
    elif ext in ["mp3", "mpeg"]:
        return speech.RecognitionConfig.AudioEncoding.MP3
    elif ext in ["webm", "opus"]:
        return speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    else:
        return speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED

def get_sample_rate_for_encoding(file_extension):
    """Get appropriate sample rate based on file extension"""
    ext = file_extension.lower()
    if ext in ["wav", "linear16"]:
        return 16000  # Standard for WAV files
    elif ext in ["webm", "opus"]:
        return 48000  # Standard for OPUS
    else:
        return None  # Let Google auto-detect


async def process_voice_command(audio_file) -> dict:
    """
    Upgraded: Speech-to-Text -> Intent Understanding -> Text-to-Speech
    Returns clean short AI response without reasoning.
    """
    audio_path = None

    try:
        # Save uploaded audio with original filename extension
        file_extension = audio_file.filename.split('.')[-1].lower() if audio_file.filename else 'wav'
        content = await audio_file.read()
        
        # Validate file size (max 10MB)
        if len(content) > 10 * 1024 * 1024:
            return {
                "status": "error",
                "transcript": "File too large",
                "ai_response": "Audio file is too large. Please upload a file smaller than 10MB.",
                "audio_file_path": None,
                "error": "File size exceeds 10MB limit"
            }
        
        # Validate file has content
        if len(content) < 1000:  # Less than 1KB is probably not valid audio
            return {
                "status": "error", 
                "transcript": "File too small",
                "ai_response": "The audio file appears to be too small or corrupted.",
                "audio_file_path": None,
                "error": "File size too small"
            }
        
        print(f"Processing audio file: {audio_file.filename}, Size: {len(content)} bytes, Extension: {file_extension}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_audio:
            temp_audio.write(content)
            audio_path = temp_audio.name

        # --- STEP 1: Convert Speech to Text ---
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        audio = speech.RecognitionAudio(content=audio_data)
        
        # Get appropriate encoding and sample rate based on file extension
        audio_encoding = get_audio_encoding(file_extension)
        sample_rate = get_sample_rate_for_encoding(file_extension)
        print(f"Detected audio encoding: {audio_encoding}, Sample rate: {sample_rate}")
        
        # Try AUTO-DETECTION FIRST (most reliable)
        config = speech.RecognitionConfig(
            language_code="en-US",
            enable_automatic_punctuation=True
        )

        try:
            print("Attempting speech recognition with auto-detection...")
            stt_response = speech_client.recognize(config=config, audio=audio)
        except Exception as e:
            print(f"Auto-detection failed: {e}")
            # Fallback: Try with detected encoding
            config = speech.RecognitionConfig(
                language_code="en-US",
                enable_automatic_punctuation=True,
                encoding=get_audio_encoding(file_extension),
                sample_rate_hertz=16000
            )
            try:
                print("Attempting speech recognition with detected format...")
                stt_response = speech_client.recognize(config=config, audio=audio)
            except Exception as e2:
                print(f"Detected format failed: {e2}")
                # Last fallback: Most basic configuration
                config = speech.RecognitionConfig(
                    language_code="en-US"
                )
                print("Attempting speech recognition with basic config...")
                stt_response = speech_client.recognize(config=config, audio=audio)
        
        # Debug: Check if we got any results
        print(f"Speech recognition results count: {len(stt_response.results) if stt_response.results else 0}")
        
        transcript = ""
        if stt_response.results and len(stt_response.results) > 0:
            # Combine all speech segments found
            transcript_parts = []
            for i, result in enumerate(stt_response.results):
                print(f"Processing result {i}: alternatives count = {len(result.alternatives) if result.alternatives else 0}")
                if result.alternatives and len(result.alternatives) > 0:
                    segment_text = result.alternatives[0].transcript
                    print(f"Raw segment text {i}: '{segment_text}' (length: {len(segment_text)})")
                    if segment_text and segment_text.strip():
                        transcript_parts.append(segment_text.strip())
                        print(f"Added speech segment {i}: '{segment_text.strip()}'")
                    else:
                        print(f"Segment {i} is empty or whitespace only")
                else:
                    print(f"Result {i} has no alternatives")
            
            transcript = " ".join(transcript_parts)
            print(f"Final combined transcript: '{transcript}' (parts: {len(transcript_parts)})")
        else:
            print("No speech results found")
        
        if not transcript.strip():
            print("Setting transcript to 'No speech detected' because final transcript is empty")
            transcript = "No speech detected."

        # --- STEP 2: Intent Analysis with Gemini ---
        structured_prompt = f"""
        Teacher said: "{transcript}".
        Respond in this JSON format:
        {{"answer": "Your short, helpful response for the teacher."}}
        Do NOT include any explanation, reasoning, or additional text.
        """

        ai_response = model.generate_content(structured_prompt)
        raw_text = ai_response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").replace("json", "").strip()
        try:
            parsed_response = json.loads(raw_text)
            response_text = parsed_response.get("answer", "").strip()
        except json.JSONDecodeError:
            # Fallback if model returns plain text
            response_text = ai_response.text.strip().split("\n")[0]

        # If still empty, return default
        if not response_text:
            response_text = "I couldn't understand the command. Please try again."

        # --- STEP 3: Convert AI Response to Speech ---
        synthesis_input = texttospeech.SynthesisInput(text=response_text)
        voice_params = texttospeech.VoiceSelectionParams(language_code="en-US")
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        tts_response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice_params, audio_config=audio_config
        )

        # Save audio file
        unique_filename = f"ai_response_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_output_path = os.path.join(AUDIO_FILES_DIR, unique_filename)
        with open(audio_output_path, "wb") as out:
            out.write(tts_response.audio_content)

        return {
            "status": "success",
            "transcript": transcript,
            "ai_response": response_text,
            "audio_file_path": audio_output_path,
            "audio_filename": unique_filename
        }

    except Exception as e:
        return {
            "status": "error",
            "transcript": "Error processing audio",
            "ai_response": f"Sorry, something went wrong: {str(e)}",
            "audio_file_path": None,
            "error": str(e)
        }

    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass
