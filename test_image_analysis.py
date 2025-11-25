"""
Test script to diagnose image analysis issues.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.db.session import SessionLocal
from app.services.llm import generate_content

def test_image_analysis():
    """Test image analysis with a sample image."""
    print("=" * 60)
    print("IMAGE ANALYSIS DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Check environment variables
    print("\n1. Checking Environment Variables:")
    print(f"   OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    print(f"   OPENAI_VISION_MODEL: {os.getenv('OPENAI_VISION_MODEL', 'gpt-4o (default)')}")
    print(f"   API_BASE_URL: {os.getenv('API_BASE_URL', 'http://localhost:8000 (default)')}")
    
    # Check uploads directory
    print("\n2. Checking Uploads Directory:")
    uploads_dir = Path("uploads/chat_images")
    if uploads_dir.exists():
        files = list(uploads_dir.glob("*"))
        print(f"   Directory exists: YES")
        print(f"   Files found: {len(files)}")
        if files:
            print(f"   Sample files: {[f.name for f in files[:3]]}")
        else:
            print("   WARNING: No image files found in uploads directory")
    else:
        print(f"   Directory exists: NO")
        print(f"   WARNING: Uploads directory does not exist!")
    
    # Test image URL format
    print("\n3. Testing Image URL Handling:")
    test_urls = [
        "/uploads/chat_images/test.jpg",
        "http://localhost:8000/uploads/chat_images/test.jpg",
        "http://192.168.0.120:8000/uploads/chat_images/test.jpg",
    ]
    
    for url in test_urls:
        if url.startswith("/uploads/"):
            filename = url.split("/uploads/chat_images/")[-1]
            local_path = Path("uploads/chat_images") / filename
            exists = local_path.exists()
            print(f"   {url}")
            print(f"      -> Local path: {local_path}")
            print(f"      -> File exists: {exists}")
        else:
            print(f"   {url}")
            print(f"      -> Will try HTTP fetch")
    
    # Test LLM call (if we have a test image)
    print("\n4. Testing LLM Vision Call:")
    if uploads_dir.exists():
        test_files = list(uploads_dir.glob("*.jpg")) + list(uploads_dir.glob("*.png"))
        if test_files:
            test_file = test_files[0]
            test_url = f"/uploads/chat_images/{test_file.name}"
            print(f"   Using test image: {test_file.name}")
            print(f"   Image URL: {test_url}")
            print(f"   File size: {test_file.stat().st_size} bytes")
            
            try:
                print("   Attempting vision API call...")
                result = generate_content(
                    "What do you see in this image?",
                    image_url=test_url,
                    conversation_history=None
                )
                print(f"   SUCCESS: Got response ({len(result.text)} chars)")
                print(f"   Response preview: {result.text[:100]}...")
            except Exception as e:
                print(f"   ERROR: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("   SKIPPED: No test images found")
    else:
        print("   SKIPPED: Uploads directory does not exist")
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_image_analysis()





