from google.cloud import speech

def speech_to_text(audio_file: bytes):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_file)
    config = speech.RecognitionConfig(language_code="en-US")
    response = client.recognize(config=config, audio=audio)
    return response.results[0].alternatives[0].transcript if response.results else ""
