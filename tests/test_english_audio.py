"""
Test English audio generation specifically to debug the issue
"""
import asyncio
import os
import sys
import requests

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.activities_service import generate_interactive_story

async def test_english_audio():
    """Test English audio generation specifically"""
    
    print("🔥 TESTING ENGLISH AUDIO GENERATION")
    print("=" * 50)
    
    try:
        # Test English story generation
        print("📝 Generating English story...")
        result = await generate_interactive_story(
            grade=5,
            topic="Solar System",
            language="English",
            user_id="test_user_english"
        )
        
        print(f"✅ Story generated successfully!")
        print(f"📊 Story ID: {result.get('story_id')}")
        print(f"📖 Title: {result.get('title')}")
        print(f"🎵 Audio filename: {result.get('audio_filename')}")
        print(f"📝 Story length: {len(result.get('story_text', ''))} characters")
        
        # Check if audio file exists
        audio_filename = result.get('audio_filename')
        if audio_filename:
            audio_path = os.path.join("temp_audio", audio_filename)
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                print(f"✅ Audio file exists: {audio_path} ({file_size} bytes)")
                
                # Test HTTP access to the audio file
                print(f"🌐 Testing HTTP access to audio file...")
                audio_url = f"http://localhost:8000/api/v1/activities/audio/{audio_filename}"
                print(f"🔗 URL: {audio_url}")
                
                try:
                    response = requests.head(audio_url, timeout=5)
                    if response.status_code == 200:
                        print(f"✅ Audio file accessible via HTTP (Status: {response.status_code})")
                        content_length = response.headers.get('content-length')
                        if content_length:
                            print(f"📏 Content-Length: {content_length} bytes")
                    else:
                        print(f"❌ HTTP access failed (Status: {response.status_code})")
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Cannot test HTTP access (server may not be running): {e}")
                
            else:
                print(f"❌ Audio file does not exist: {audio_path}")
        else:
            print(f"❌ No audio filename returned")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during English audio test: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_multiple_languages():
    """Test audio generation for multiple languages"""
    
    print("\n🌍 TESTING MULTIPLE LANGUAGES")
    print("=" * 50)
    
    languages = ["English", "Spanish", "French", "German", "Hindi"]
    
    for language in languages:
        print(f"\n🔤 Testing {language}...")
        try:
            result = await generate_interactive_story(
                grade=3,
                topic="Animals",
                language=language,
                user_id=f"test_user_{language.lower()}"
            )
            
            audio_filename = result.get('audio_filename')
            if audio_filename:
                audio_path = os.path.join("temp_audio", audio_filename)
                if os.path.exists(audio_path):
                    file_size = os.path.getsize(audio_path)
                    print(f"✅ {language}: {audio_filename} ({file_size} bytes)")
                else:
                    print(f"❌ {language}: File not found - {audio_filename}")
            else:
                print(f"❌ {language}: No audio filename returned")
                
        except Exception as e:
            print(f"❌ {language}: Error - {e}")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_english_audio())
    asyncio.run(test_multiple_languages())
