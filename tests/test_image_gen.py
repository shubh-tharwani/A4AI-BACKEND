#!/usr/bin/env python3
"""
Test the updated image generation system
"""
import sys
import os
sys.path.append(os.getcwd())

def test_image_generation():
    """Test the image generation functionality"""
    print("🧪 Testing Updated Image Generation System")
    print("=" * 50)
    
    try:
        from services.image_generator import ImageGenerator
        
        print("✅ ImageGenerator imported successfully")
        
        # Initialize generator
        generator = ImageGenerator()
        print("✅ ImageGenerator initialized")
        
        # Test image generation
        print("\n📸 Testing image generation...")
        file_path, filename, metadata = generator.generate_image(
            content="Test educational content about photosynthesis and how plants make energy from sunlight",
            visual_type="diagram",
            topic="Photosynthesis",
            subject="Biology",
            grade="6",
            style="educational",
            color_scheme="green"
        )
        
        print(f"✅ Image generated successfully!")
        print(f"📁 File path: {file_path}")
        print(f"📄 Filename: {filename}")
        print(f"📊 Metadata:")
        for key, value in metadata.items():
            print(f"   {key}: {value}")
        
        # Check if file exists
        if os.path.exists(file_path):
            print(f"✅ File exists on disk")
            file_size = os.path.getsize(file_path)
            print(f"📏 File size: {file_size} bytes")
            
            # Check file extension
            if file_path.endswith('.png'):
                print("✅ Generated PNG image file")
            elif file_path.endswith('.mmd'):
                print("ℹ️ Generated Mermaid diagram file")
            else:
                print(f"⚠️ Unexpected file type: {file_path}")
                
        else:
            print("❌ File does not exist on disk")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_image_generation()
