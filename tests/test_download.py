#!/usr/bin/env python3
"""
Test script to verify download functionality
"""
import os
import requests
import json

def test_download_endpoint():
    """Test the download endpoint"""
    # Test ID that you mentioned
    test_id = "a8c2b120-8e98-4fc7-b063-b3bdd5823a0d"
    download_url = f"http://localhost:8000/api/v1/visual-aids/{test_id}/download"
    
    print(f"🔍 Testing download URL: {download_url}")
    
    try:
        response = requests.get(download_url, timeout=10)
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', 'unknown')
            content_disposition = response.headers.get('content-disposition', 'none')
            
            print(f"✅ Download successful!")
            print(f"📄 Content-Type: {content_type}")
            print(f"📁 Content-Disposition: {content_disposition}")
            print(f"📊 Content Length: {len(response.content)} bytes")
            
            # Check if it's a Mermaid file
            if content_type == 'text/plain' or 'mmd' in content_disposition:
                print(f"🎨 File type: Mermaid diagram (.mmd)")
                print(f"📝 First 200 chars of content:")
                print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
            elif content_type == 'image/png':
                print(f"🖼️ File type: PNG image")
            
        elif response.status_code == 404:
            print(f"❌ File not found (404)")
            print(f"📄 Response: {response.text}")
        else:
            print(f"❌ Error {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server. Make sure it's running on port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Visual Aid Download Endpoint")
    print("=" * 50)
    test_download_endpoint()
