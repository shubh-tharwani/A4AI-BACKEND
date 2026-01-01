#!/usr/bin/env python3
"""
Test interactive story generation with regional languages
"""
import asyncio
import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.activities_service import generate_interactive_story

async def test_regional_story_generation():
    """Test story generation with regional languages"""
    print("🧪 Testing Regional Language Story Generation")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        {"grade": 5, "topic": "Mathematics", "language": "Hindi"},
        {"grade": 3, "topic": "Science", "language": "Spanish"},
        {"grade": 7, "topic": "History", "language": "French"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📚 Test {i}: Grade {test_case['grade']} - {test_case['topic']} in {test_case['language']}")
        print("-" * 50)
        
        try:
            # Generate story
            result = await generate_interactive_story(
                grade=test_case['grade'],
                topic=test_case['topic'],
                language=test_case['language']
            )
            
            print(f"✅ Story generated successfully!")
            print(f"📖 Title: {result.get('title', 'N/A')[:100]}...")
            print(f"📝 Story length: {len(result.get('story_text', ''))} characters")
            print(f"🎵 Audio file: {result.get('audio_filename', 'N/A')}")
            print(f"🎯 Learning objectives: {len(result.get('learning_objectives', []))}")
            print(f"📚 Vocabulary words: {len(result.get('vocabulary_words', []))}")
            
            # Check if audio file exists
            audio_filename = result.get('audio_filename', '')
            if audio_filename:
                audio_path = os.path.join("temp_audio", audio_filename)
                if os.path.exists(audio_path):
                    file_size = os.path.getsize(audio_path)
                    print(f"🎧 Audio file exists: {file_size} bytes")
                else:
                    print(f"❌ Audio file not found: {audio_path}")
            
        except Exception as e:
            print(f"❌ Error generating story: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n🏁 Regional language story generation test completed!")

if __name__ == "__main__":
    asyncio.run(test_regional_story_generation())
