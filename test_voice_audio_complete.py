#!/usr/bin/env python3
"""
Test voice assistant audio generation and serving
"""
import asyncio
import requests
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.voice_assistant_service import process_text_command

async def test_voice_audio_complete_workflow():
    """Test complete voice assistant audio workflow"""
    print("🎤 Testing Voice Assistant Audio Generation and Serving...")
    print("=" * 60)
    
    # Test text command processing
    test_text = "Hello, can you help me create a lesson plan for grade 5 math?"
    
    try:
        print(f"📝 Processing text: '{test_text}'")
        
        # Generate audio response
        result = await process_text_command(test_text)
        
        print(f"✅ Status: {result.get('status')}")
        print(f"💬 AI Response: {result.get('ai_response')}")
        print(f"🎵 Audio filename: {result.get('audio_filename')}")
        
        if result.get('status') == 'success':
            audio_filename = result.get('audio_filename')
            audio_path = result.get('audio_file_path')
            
            # Check if file exists locally
            if os.path.exists(audio_path):
                file_size = os.path.getsize(audio_path)
                print(f"✅ Audio file created locally: {file_size} bytes")
                
                # Test both audio endpoints
                endpoints_to_test = [
                    f"http://localhost:8000/api/v1/voice/audio/{audio_filename}",
                    f"http://localhost:8000/api/v1/voice/download-audio/{audio_filename}"
                ]
                
                for endpoint in endpoints_to_test:
                    print(f"\n🌐 Testing endpoint: {endpoint}")
                    
                    try:
                        # Test HEAD request first
                        head_response = requests.head(endpoint, timeout=10)
                        print(f"📡 HEAD Status: {head_response.status_code}")
                        
                        if head_response.status_code == 200:
                            print(f"📋 Content-Type: {head_response.headers.get('content-type')}")
                            print(f"📏 Content-Length: {head_response.headers.get('content-length')}")
                            print(f"🔒 CORS Headers: {head_response.headers.get('access-control-allow-origin')}")
                            
                            # Test GET request
                            get_response = requests.get(endpoint, timeout=10)
                            if get_response.status_code == 200:
                                print(f"✅ GET successful: {len(get_response.content)} bytes received")
                                
                                # Verify it's valid audio data
                                if get_response.content.startswith(b'\\xFF\\xFB') or get_response.content.startswith(b'ID3'):
                                    print("✅ Valid MP3 audio data detected")
                                else:
                                    print("⚠️ Audio data format may be unusual")
                            else:
                                print(f"❌ GET failed: {get_response.status_code}")
                        else:
                            print(f"❌ HEAD failed: {head_response.status_code}")
                            
                    except requests.exceptions.RequestException as e:
                        print(f"❌ Request failed: {e}")
                
                # Create a simple HTML test file
                create_html_test_file(audio_filename)
                
            else:
                print(f"❌ Audio file not found locally: {audio_path}")
        else:
            print(f"❌ Audio generation failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def create_html_test_file(audio_filename):
    """Create a simple HTML file to test audio playback"""
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Voice Assistant Audio Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .test-section {{ margin: 20px 0; padding: 20px; border: 1px solid #ccc; }}
        audio {{ width: 100%; }}
        .status {{ margin: 10px 0; padding: 10px; background: #f0f0f0; }}
    </style>
</head>
<body>
    <h1>Voice Assistant Audio Test</h1>
    
    <div class="test-section">
        <h2>Audio File: {audio_filename}</h2>
        
        <h3>Direct Audio Endpoint:</h3>
        <audio controls preload="metadata">
            <source src="http://localhost:8000/api/v1/voice/audio/{audio_filename}" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
        
        <h3>Download Audio Endpoint:</h3>
        <audio controls preload="metadata">
            <source src="http://localhost:8000/api/v1/voice/download-audio/{audio_filename}" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
        
        <div class="status" id="status">Loading...</div>
    </div>

    <script>
        // Test audio loading
        const audioElements = document.querySelectorAll('audio');
        const statusDiv = document.getElementById('status');
        let statusMessages = [];
        
        audioElements.forEach((audio, index) => {{
            const endpointName = index === 0 ? 'Direct' : 'Download';
            
            audio.addEventListener('loadstart', function() {{
                statusMessages.push(`${{endpointName}}: Load started...`);
                updateStatus();
            }});
            
            audio.addEventListener('canplaythrough', function() {{
                statusMessages.push(`✅ ${{endpointName}}: Audio loaded successfully!`);
                updateStatus();
            }});
            
            audio.addEventListener('error', function(e) {{
                statusMessages.push(`❌ ${{endpointName}}: Error - ${{e.target.error ? e.target.error.message : 'Unknown error'}}`);
                updateStatus();
                console.error(`${{endpointName}} audio error:`, e);
            }});
        }});
        
        function updateStatus() {{
            statusDiv.innerHTML = statusMessages.join('<br>');
        }}
        
        // Test network requests
        async function testEndpoints() {{
            const endpoints = [
                'http://localhost:8000/api/v1/voice/audio/{audio_filename}',
                'http://localhost:8000/api/v1/voice/download-audio/{audio_filename}'
            ];
            
            for (let i = 0; i < endpoints.length; i++) {{
                const endpointName = i === 0 ? 'Direct' : 'Download';
                try {{
                    const response = await fetch(endpoints[i], {{ method: 'HEAD' }});
                    statusMessages.push(`🌐 ${{endpointName}} HEAD: ${{response.status}} - ${{response.headers.get('content-type')}}`);
                }} catch (error) {{
                    statusMessages.push(`❌ ${{endpointName}} HEAD failed: ${{error.message}}`);
                }}
            }}
            updateStatus();
        }}
        
        // Run tests when page loads
        window.addEventListener('load', function() {{
            testEndpoints();
        }});
    </script>
</body>
</html>'''
    
    with open('voice_audio_test.html', 'w') as f:
        f.write(html_content)
    
    print(f"📄 Created test HTML file: voice_audio_test.html")
    print(f"🌐 Open this file in your browser to test audio playback")

if __name__ == "__main__":
    asyncio.run(test_voice_audio_complete_workflow())
