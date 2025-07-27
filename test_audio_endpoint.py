#!/usr/bin/env python3
"""
Test script for audio endpoint
"""
import requests
import os

def test_audio_endpoint():
    """Test the audio file serving endpoint"""
    print("🎵 Testing Audio Endpoint")
    print("=" * 30)
    
    # Check if there are any audio files in the activities_audio directory
    audio_dir = os.path.join(os.getcwd(), "activities_audio")
    if not os.path.exists(audio_dir):
        print("❌ Audio directory doesn't exist")
        return
    
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
    
    if not audio_files:
        print("❌ No audio files found in activities_audio directory")
        return
    
    # Test with the first audio file
    test_file = audio_files[0]
    print(f"🎯 Testing with audio file: {test_file}")
    
    # Test the endpoint
    url = f"http://localhost:8000/api/v1/activities/audio/{test_file}"
    print(f"📡 Requesting: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Audio endpoint working correctly!")
            print(f"📏 Content Length: {len(response.content)} bytes")
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_audio_endpoint()
