"""
Test script for the ML inference service
"""

import requests
import json
import time
from pathlib import Path

# Service configuration
BASE_URL = "http://localhost:8001"  # Change to 8000 for Docker
HEALTH_ENDPOINT = f"{BASE_URL}/health"
EMOTION_ENDPOINT = f"{BASE_URL}/predict/emotion"
BATCH_ENDPOINT = f"{BASE_URL}/predict/batch"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")
        return False

def create_test_image():
    """Create a simple test image for testing"""
    try:
        from PIL import Image, ImageDraw
        import numpy as np
        
        # Create a simple test image with a face-like shape
        img = Image.new('RGB', (200, 200), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw a simple face
        # Face outline
        draw.ellipse([50, 50, 150, 150], outline='black', width=2)
        
        # Eyes
        draw.ellipse([70, 80, 85, 95], fill='black')
        draw.ellipse([115, 80, 130, 95], fill='black')
        
        # Nose
        draw.polygon([(100, 100), (95, 110), (105, 110)], outline='black')
        
        # Mouth (smile)
        draw.arc([80, 120, 120, 140], 0, 180, fill='black', width=2)
        
        # Save test image
        test_image_path = Path("test_face.jpg")
        img.save(test_image_path)
        print(f"✅ Created test image: {test_image_path}")
        return test_image_path
        
    except Exception as e:
        print(f"❌ Failed to create test image: {str(e)}")
        return None

def test_emotion_prediction(image_path):
    """Test single image emotion prediction"""
    print("Testing emotion prediction...")
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(EMOTION_ENDPOINT, files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Emotion prediction successful: {data}")
            return True
        else:
            print(f"❌ Emotion prediction failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Emotion prediction error: {str(e)}")
        return False

def test_batch_prediction(image_path):
    """Test batch image prediction"""
    print("Testing batch prediction...")
    try:
        with open(image_path, 'rb') as f:
            files = [('files', f), ('files', f)]  # Send same image twice
            response = requests.post(BATCH_ENDPOINT, files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Batch prediction successful: {data}")
            return True
        else:
            print(f"❌ Batch prediction failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Batch prediction error: {str(e)}")
        return False

def cleanup_test_files():
    """Clean up test files"""
    try:
        test_image = Path("test_face.jpg")
        if test_image.exists():
            test_image.unlink()
            print("✅ Cleaned up test files")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {str(e)}")

def main():
    """Run all tests"""
    print("🚀 Starting ML Service Tests")
    print("=" * 50)
    
    # Test health endpoint
    if not test_health():
        print("❌ Health check failed. Make sure the service is running.")
        return
    
    # Create test image
    test_image = create_test_image()
    if not test_image:
        print("❌ Failed to create test image. Exiting.")
        return
    
    try:
        # Test single emotion prediction
        test_emotion_prediction(test_image)
        
        # Test batch prediction
        test_batch_prediction(test_image)
        
        print("=" * 50)
        print("✅ All tests completed!")
        
    finally:
        # Cleanup
        cleanup_test_files()

if __name__ == "__main__":
    main()
