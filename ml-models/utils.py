"""
Utility functions for the ML inference service
Image processing, validation, and response formatting
"""

import logging
import numpy as np
import cv2
from PIL import Image
import io
from typing import Optional, Dict, Any, List
import json
import os
import re
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

def validate_image(image_data: bytes) -> bool:
    """
    Validate if the uploaded data is a valid image
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        True if valid image, False otherwise
    """
    try:
        # Try to open with PIL
        image = Image.open(io.BytesIO(image_data))
        image.verify()
        
        # Enforce supported formats and size limits (max 5MB)
        supported_formats = ['JPEG', 'PNG', 'WEBP']
        if image.format not in supported_formats:
            logger.warning(f"Unsupported image format: {image.format}")
            return False
        # Check file size
        max_bytes = 5 * 1024 * 1024
        if len(image_data) > max_bytes:
            logger.warning(f"Image exceeds max size: {len(image_data)} bytes")
            return False
        
        # Check image size (reasonable limits)
        width, height = image.size
        if width < 10 or height < 10:
            logger.warning(f"Image too small: {width}x{height}")
            return False
        
        if width > 10000 or height > 10000:
            logger.warning(f"Image too large: {width}x{height}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Image validation failed: {str(e)}")
        return False

def preprocess_image(image_data: bytes) -> Optional[np.ndarray]:
    """
    Preprocess image data for emotion detection
    
    Args:
        image_data: Raw image bytes
        
    Returns:
        Preprocessed image array or None if failed
    """
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        image_array = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        image_bgr = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        
        # Resize if too large (maintain aspect ratio)
        max_size = 1024
        height, width = image_bgr.shape[:2]
        
        if max(height, width) > max_size:
            if height > width:
                new_height = max_size
                new_width = int(width * max_size / height)
            else:
                new_width = max_size
                new_height = int(height * max_size / width)
            
            image_bgr = cv2.resize(image_bgr, (new_width, new_height))
        
        return image_bgr
        
    except Exception as e:
        logger.error(f"Image preprocessing failed: {str(e)}")
        return None

def is_allowed_mime(content_type: Optional[str]) -> bool:
    """
    Validate MIME type is allowed image type.
    """
    try:
        if content_type is None:
            return False
        allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
        return content_type.lower() in allowed
    except Exception:
        return False

def detect_faces_opencv(image: np.ndarray) -> List[tuple]:
    """
    Detect faces in image using OpenCV Haar cascades
    
    Args:
        image: Input image array
        
    Returns:
        List of face bounding boxes (x, y, w, h)
    """
    try:
        # Load face cascade
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        if face_cascade.empty():
            logger.error("Failed to load face cascade")
            return []
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        return faces.tolist() if len(faces) > 0 else []
        
    except Exception as e:
        logger.error(f"Face detection failed: {str(e)}")
        return []

def b64_encode_image(image_bytes: bytes) -> str:
    """
    Base64-encode image bytes for transport/storage.
    """
    import base64
    try:
        return base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        logger.error(f"Base64 encode failed: {str(e)}")
        return ""

def b64_decode_image(b64_string: str) -> Optional[bytes]:
    """
    Decode base64 string to raw image bytes.
    """
    import base64
    try:
        return base64.b64decode(b64_string)
    except Exception as e:
        logger.error(f"Base64 decode failed: {str(e)}")
        return None

def _clean_filename(filename: Optional[str]) -> str:
    """Return a sanitized filename for logging/saving."""
    if not filename:
        return "upload.bin"
    name = os.path.basename(filename)
    # allow alphanum, dot, dash, underscore
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "upload.bin"

def validate_upload(file: UploadFile) -> str:
    """
    Validate uploaded file: correct MIME/extension and max size 5MB.
    Returns cleaned filename or raises HTTPException 400.
    """
    try:
        if file is None:
            raise HTTPException(status_code=400, detail={"error": "No file uploaded"})
        # MIME type
        if not is_allowed_mime(file.content_type):
            logger.warning(f"Invalid content type: {file.content_type}")
            raise HTTPException(status_code=400, detail={"error": "Unsupported file type. Allowed: jpg, jpeg, png, webp"})

        # Extension check
        cleaned = _clean_filename(file.filename)
        ext = cleaned.split(".")[-1].lower() if "." in cleaned else ""
        if ext not in {"jpg", "jpeg", "png", "webp"}:
            logger.warning(f"Invalid file extension: {ext}")
            raise HTTPException(status_code=400, detail={"error": "Unsupported file type. Allowed: jpg, jpeg, png, webp"})

        # Size check (seek to end, then restore)
        try:
            current = file.file.tell()
        except Exception:
            current = 0
        try:
            file.file.seek(0, 2)
            size = file.file.tell()
            file.file.seek(current, 0)
        except Exception:
            size = None

        if size is not None and size > 5 * 1024 * 1024:
            logger.warning(f"File too large: {size} bytes")
            raise HTTPException(status_code=400, detail={"error": "File too large. Max 5MB"})

        return cleaned
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"validate_upload failed: {str(e)}")
        raise HTTPException(status_code=400, detail={"error": "Invalid upload"})

def calculate_confidence_score(probabilities: np.ndarray) -> float:
    """
    Calculate confidence score from prediction probabilities
    
    Args:
        probabilities: Array of class probabilities
        
    Returns:
        Confidence score between 0 and 1
    """
    try:
        # Use the maximum probability as confidence
        max_prob = np.max(probabilities)
        
        # Apply softmax normalization if needed
        if max_prob > 1.0:
            exp_probs = np.exp(probabilities - np.max(probabilities))
            probabilities = exp_probs / np.sum(exp_probs)
            max_prob = np.max(probabilities)
        
        return float(max_prob)
        
    except Exception as e:
        logger.error(f"Confidence calculation failed: {str(e)}")
        return 0.0

def format_response(
    success: bool,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format API response in consistent structure
    
    Args:
        success: Whether the operation was successful
        data: Response data
        error: Error message if failed
        metadata: Additional metadata
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "success": success,
        "timestamp": get_timestamp()
    }
    
    if success and data is not None:
        response["data"] = data
    elif not success and error is not None:
        response["error"] = error
    
    if metadata is not None:
        response["metadata"] = metadata
    
    return response

def get_timestamp() -> str:
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

def resize_image(image: np.ndarray, target_size: tuple = (48, 48)) -> np.ndarray:
    """
    Resize image to target size
    
    Args:
        image: Input image array
        target_size: Target size (width, height)
        
    Returns:
        Resized image array
    """
    try:
        return cv2.resize(image, target_size)
    except Exception as e:
        logger.error(f"Image resize failed: {str(e)}")
        return image

def normalize_image(image: np.ndarray) -> np.ndarray:
    """
    Normalize image to [0, 1] range
    
    Args:
        image: Input image array
        
    Returns:
        Normalized image array
    """
    try:
        # Convert to float and normalize
        normalized = image.astype(np.float32) / 255.0
        return normalized
    except Exception as e:
        logger.error(f"Image normalization failed: {str(e)}")
        return image

def crop_face_region(image: np.ndarray, face_box: tuple) -> np.ndarray:
    """
    Crop face region from image
    
    Args:
        image: Input image array
        face_box: Face bounding box (x, y, w, h)
        
    Returns:
        Cropped face region
    """
    try:
        x, y, w, h = face_box
        
        # Ensure coordinates are within image bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, image.shape[1] - x)
        h = min(h, image.shape[0] - y)
        
        return image[y:y+h, x:x+w]
        
    except Exception as e:
        logger.error(f"Face cropping failed: {str(e)}")
        return image

def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Convert image to grayscale
    
    Args:
        image: Input image array
        
    Returns:
        Grayscale image array
    """
    try:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
    except Exception as e:
        logger.error(f"Grayscale conversion failed: {str(e)}")
        return image

def enhance_image_contrast(image: np.ndarray) -> np.ndarray:
    """
    Enhance image contrast using CLAHE
    
    Args:
        image: Input grayscale image array
        
    Returns:
        Enhanced image array
    """
    try:
        # Create CLAHE object
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # Apply CLAHE
        enhanced = clahe.apply(image)
        
        return enhanced
    except Exception as e:
        logger.error(f"Contrast enhancement failed: {str(e)}")
        return image

def validate_bounding_box(box: tuple, image_shape: tuple) -> bool:
    """
    Validate if bounding box is within image bounds
    
    Args:
        box: Bounding box (x, y, w, h)
        image_shape: Image shape (height, width, channels)
        
    Returns:
        True if valid, False otherwise
    """
    try:
        x, y, w, h = box
        height, width = image_shape[:2]
        
        # Check if box is within image bounds
        if x < 0 or y < 0 or x + w > width or y + h > height:
            return False
        
        # Check if box has positive dimensions
        if w <= 0 or h <= 0:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Bounding box validation failed: {str(e)}")
        return False

def create_error_response(error_message: str, error_code: str = "PROCESSING_ERROR") -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        error_message: Error message
        error_code: Error code
        
    Returns:
        Formatted error response
    """
    return {
        "success": False,
        "error": {
            "message": error_message,
            "code": error_code
        },
        "timestamp": get_timestamp()
    }
