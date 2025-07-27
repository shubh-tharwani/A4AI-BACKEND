#!/usr/bin/env python3
"""
Test TTS with timeout handling
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.voice_assistant_service import generate_tts_audio_with_retry, create_fallback_audio, process_text_command

def test_tts_timeout_handling():
    """Test TTS generation with timeout handling"""
    print("🎙️ Testing TTS with Timeout Handling...")
    print("=" * 50)
    
    test_text = "Hello, this is a test of the timeout handling system."
    
    try:
        print(f"📝 Testing text: '{test_text}'")
        
        # Test direct TTS function
        print("\n🔧 Testing direct TTS function...")
        audio_content = generate_tts_audio_with_retry(test_text, max_retries=2)
        
        if audio_content:
            print(f"✅ TTS successful: {len(audio_content)} bytes")
        else:
            print("❌ TTS returned empty content")
            
    except Exception as e:
        print(f"❌ TTS failed: {e}")
        
        # Test fallback audio
        print("\n🔇 Testing fallback audio...")
        try:
            fallback_audio = create_fallback_audio(test_text)
            print(f"✅ Fallback audio created: {len(fallback_audio)} bytes")
        except Exception as fallback_error:
            print(f"❌ Fallback audio failed: {fallback_error}")

async def test_complete_workflow():
    """Test complete voice assistant workflow with timeout handling"""
    print("\n🔄 Testing Complete Workflow...")
    print("=" * 50)
    
    test_text = "Can you help me create a lesson plan?"
    
    try:
        result = await process_text_command(test_text)
        
        print(f"✅ Status: {result.get('status')}")
        print(f"💬 AI Response: {result.get('ai_response')}")
        print(f"🎵 Audio filename: {result.get('audio_filename')}")
        
        if result.get('status') == 'success':
            audio_path = result.get('audio_file_path')
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                print(f"✅ Audio file created: {file_size} bytes")
            else:
                print(f"❌ Audio file not found: {audio_path}")
        else:
            print(f"❌ Workflow failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Complete workflow test failed: {e}")

if __name__ == "__main__":
    # Test direct TTS function
    test_tts_timeout_handling()
    
    # Test complete workflow
    asyncio.run(test_complete_workflow())
