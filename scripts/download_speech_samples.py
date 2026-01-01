#!/usr/bin/env python3
"""
Download Real Speech Test Files
This script attempts to download actual speech samples for testing the Voice Assistant API.
"""

import requests
import os
from urllib.parse import urlparse

def download_speech_samples():
    """Download real speech audio samples for testing"""
    
    # List of URLs with actual speech samples (public domain/free)
    speech_urls = [
        {
            'url': 'https://www2.cs.uic.edu/~i101/SoundFiles/gettysburg10.wav',
            'filename': 'test_speech_gettysburg.wav',
            'description': 'Gettysburg Address sample'
        },
        {
            'url': 'https://www2.cs.uic.edu/~i101/SoundFiles/CantinaBand3.wav', 
            'filename': 'test_speech_cantina.wav',
            'description': 'Star Wars Cantina music'
        }
    ]
    
    print("🔽 Downloading real audio samples for testing...\n")
    
    downloaded_files = []
    
    for sample in speech_urls:
        try:
            print(f"📡 Downloading: {sample['description']}")
            print(f"   URL: {sample['url']}")
            
            response = requests.get(sample['url'], timeout=30)
            
            if response.status_code == 200:
                with open(sample['filename'], 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                print(f"   ✅ Downloaded: {sample['filename']} ({file_size:,} bytes)")
                downloaded_files.append(sample['filename'])
            else:
                print(f"   ❌ Failed: HTTP {response.status_code}")
                
        except requests.RequestException as e:
            print(f"   ❌ Network Error: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    if downloaded_files:
        print("🎉 SUCCESS! Downloaded audio files:")
        for filename in downloaded_files:
            print(f"   📄 {filename}")
        
        print("\n📝 TESTING INSTRUCTIONS:")
        print("1. Start the server: python main.py")
        print("2. Use Postman to test: POST http://localhost:8000/voice-assistant/process")
        print("3. Upload one of the downloaded files")
        print("4. Check terminal logs for 'Raw segment text' debugging info")
        
    else:
        print("❌ No files downloaded. You'll need to record your own speech sample.")
        print("\n📱 MANUAL RECORDING OPTION:")
        print("1. Use your phone's voice recorder")
        print("2. Say: 'Hello, this is a test for the voice assistant'")
        print("3. Save as WAV format and transfer to your computer")
        print("4. Place the file in this directory")

if __name__ == "__main__":
    download_speech_samples()
