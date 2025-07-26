#!/usr/bin/env python3
"""
Test script for audio generation functionality
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.activities_service import _generate_story_audio, _create_fallback_audio_file

async def test_audio_generation():
    """Test audio generation with multiple languages"""
    print("🧪 Testing Audio Generation")
    print("=" * 50)
    
    # Test story text
    test_story = "Hello! This is a test story about mathematics. Math is all around us in our daily lives."
    
    # Test languages
    test_languages = ["English", "Spanish", "French", "German", "Hindi"]
    
    for language in test_languages:
        print(f"\n🌍 Testing {language}...")
        try:
            # Test audio generation
            audio_filename = await _generate_story_audio(test_story, language)
            print(f"✅ Generated audio: {audio_filename}")
            
            # Check if file exists
            audio_path = os.path.join("temp_audio", audio_filename)
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                print(f"📁 File exists: {file_size} bytes")
            else:
                print(f"❌ File not found: {audio_path}")
                
        except Exception as e:
            print(f"❌ Error with {language}: {e}")
            
            # Test fallback
            print(f"🔄 Testing fallback for {language}...")
            try:
                fallback_filename = _create_fallback_audio_file(test_story, language)
                print(f"✅ Fallback generated: {fallback_filename}")
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
    
    print("\n🏁 Audio generation test completed!")

if __name__ == "__main__":
    asyncio.run(test_audio_generation())
