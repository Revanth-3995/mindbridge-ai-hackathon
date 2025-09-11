"""
Simple test script to verify ML service endpoints
"""

import requests
import json
from pathlib import Path
from PIL import Image, ImageDraw
import io

# Service configuration
BASE_URL = "http://localhost:8000"  # Change to 8001 for local development
HEALTH_ENDPOINT = f"{BASE_URL}/health"
EMOTION_ENDPOINT = f"{BASE_URL}/predict/emotion"
BATCH_ENDPOINT = f"{BASE_URL}/predict/batch"

def create_test_image():
    """Create a simple test image with a face"""
    # Create a 200x200 white image
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
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes.getvalue()

def test_health():
    """Test the /health endpoint"""
    print("Testing /health endpoint...")
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_emotion_prediction():
    """Test the /predict/emotion endpoint"""
    print("\nTesting /predict/emotion endpoint...")
    try:
        # Create test image
        image_data = create_test_image()
        
        # Send request
        files = {'file': ('test_face.jpg', image_data, 'image/jpeg')}
        response = requests.post(EMOTION_ENDPOINT, files=files, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_batch_prediction():
    """Test the /predict/batch endpoint"""
    print("\nTesting /predict/batch endpoint...")
    try:
        # Create test images
        image_data1 = create_test_image()
        image_data2 = create_test_image()
        
        # Send request
        files = [
            ('files', ('test_face1.jpg', image_data1, 'image/jpeg')),
            ('files', ('test_face2.jpg', image_data2, 'image/jpeg'))
        ]
        response = requests.post(BATCH_ENDPOINT, files=files, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing ML Service Endpoints")
    print("=" * 50)
    
    # Test health endpoint
    health_ok = test_health()
    
    # Test emotion prediction
    emotion_ok = test_emotion_prediction()
    
    # Test batch prediction
    batch_ok = test_batch_prediction()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    print(f"Emotion Prediction: {'✅ PASS' if emotion_ok else '❌ FAIL'}")
    print(f"Batch Prediction: {'✅ PASS' if batch_ok else '❌ FAIL'}")
    
    if all([health_ok, emotion_ok, batch_ok]):
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed. Check the service logs.")

if __name__ == "__main__":
    main()
