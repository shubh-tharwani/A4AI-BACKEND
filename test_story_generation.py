#!/usr/bin/env python3
"""
Test script for interactive story generation
Tests the improved prompt and story generation functionality
"""
import asyncio
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.activities_service import generate_interactive_story

async def test_story_generation():
    """Test the improved story generation"""
    print("🧪 Testing Interactive Story Generation")
    print("=" * 50)
    
    # Test parameters
    test_cases = [
        {"grade": 5, "topic": "Solar System", "language": "English"},
        {"grade": 3, "topic": "Water Cycle", "language": "English"},
        {"grade": 8, "topic": "Photosynthesis", "language": "Spanish"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📚 Test Case {i}: {test_case}")
        print("-" * 30)
        
        try:
            # Generate story
            result = await generate_interactive_story(
                grade=test_case["grade"],
                topic=test_case["topic"],
                language=test_case["language"]
            )
            
            # Display results
            print(f"✅ Story generated successfully!")
            print(f"🏷️  Title: {result['title']}")
            print(f"📝 Story length: {len(result['story_text'])} characters")
            print(f"📝 Word count: {len(result['story_text'].split())} words")
            print(f"🎯 Learning objectives: {len(result.get('learning_objectives', []))}")
            print(f"📚 Vocabulary words: {len(result.get('vocabulary_words', []))}")
            print(f"🤔 Think about it: {len(result.get('think_about_it', ''))} characters")
            print(f"📖 What you learn: {len(result.get('what_you_learn', ''))} characters")
            
            # Show first 200 characters of story
            story_preview = result['story_text'][:200] + "..." if len(result['story_text']) > 200 else result['story_text']
            print(f"📄 Story preview: {story_preview}")
            
        except Exception as e:
            print(f"❌ Error generating story: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_story_generation())
