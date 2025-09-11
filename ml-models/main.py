"""
FastAPI ML Inference Service for Mind Bridge AI
GPU-optimized emotion detection service for RunPod deployment
"""

import logging
import asyncio
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from emotion_model import EmotionModel
from utils import validate_image, preprocess_image, format_response, is_allowed_mime, validate_upload

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Mind Bridge AI ML Service",
    description="GPU-optimized emotion detection service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
emotion_model: Optional[EmotionModel] = None

# Pydantic models
class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    gpu_available: bool = Field(..., description="Whether GPU is available")
    model_loaded: bool = Field(..., description="Whether emotion model is loaded")

class EmotionPrediction(BaseModel):
    emotion: str = Field(..., description="Detected emotion")
    confidence: float = Field(..., description="Confidence score (0-1)")
    bounding_box: Optional[List[int]] = Field(None, description="Face bounding box [x, y, w, h]")
    faces_detected: Optional[int] = Field(None, description="Number of faces detected in the image")

class SinglePredictionResponse(BaseModel):
    success: bool = Field(..., description="Whether prediction was successful")
    prediction: Optional[EmotionPrediction] = Field(None, description="Emotion prediction result")
    error: Optional[str] = Field(None, description="Error message if prediction failed")

class BatchPredictionResponse(BaseModel):
    success: bool = Field(..., description="Whether batch prediction was successful")
    predictions: List[EmotionPrediction] = Field(..., description="List of emotion predictions")
    total_processed: int = Field(..., description="Total number of images processed")
    errors: List[str] = Field(default_factory=list, description="List of errors encountered")

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the emotion model on startup"""
    global emotion_model
    try:
        logger.info("Initializing emotion detection model...")
        emotion_model = EmotionModel()
        await emotion_model.load_model()
        logger.info("Emotion model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load emotion model: {str(e)}")
        emotion_model = None

# Dependency to get the emotion model
def get_emotion_model() -> EmotionModel:
    if emotion_model is None:
        raise HTTPException(
            status_code=503,
            detail="Emotion model not loaded. Please try again later."
        )
    return emotion_model

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for service monitoring"""
    try:
        import torch
        gpu_available = torch.cuda.is_available()
    except ImportError:
        gpu_available = False
    
    return HealthResponse(
        status="ok",
        gpu_available=gpu_available,
        model_loaded=emotion_model is not None
    )

# Single image emotion prediction endpoint
@app.post("/predict/emotion", response_model=SinglePredictionResponse)
async def predict_emotion(
    file: UploadFile = File(..., description="Image file to analyze"),
    model: EmotionModel = Depends(get_emotion_model)
):
    """
    Predict emotion from a single image upload
    
    Args:
        file: Image file (JPEG, PNG, etc.)
        model: Loaded emotion detection model
        
    Returns:
        Emotion prediction with confidence score
    """
    try:
        # Validate presence/type/size
        cleaned_name = validate_upload(file)
        
        # Read and validate image
        image_data = await file.read()
        if not validate_image(image_data):
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid image. Ensure jpg/png/webp and <= 5MB"}
            )
        
        # Preprocess image
        processed_image = preprocess_image(image_data)
        if processed_image is None:
            raise HTTPException(
                status_code=400,
                detail="Failed to preprocess image"
            )
        
        # Make prediction
        prediction = await model.predict_single(processed_image)
        
        if prediction is None:
            return SinglePredictionResponse(
                success=False,
                error="No face detected in image"
            )
        
        return SinglePredictionResponse(
            success=True,
            prediction=EmotionPrediction(
                emotion=prediction['emotion'],
                confidence=prediction['confidence'],
                bounding_box=prediction.get('bounding_box'),
                faces_detected=prediction.get('faces_detected')
            )
        )
        
    except HTTPException as e:
        # Ensure JSON error shape per spec
        if isinstance(e.detail, dict):
            raise e
        raise HTTPException(status_code=e.status_code, detail={"error": str(e.detail)})
    except Exception as e:
        logger.error(f"Error in emotion prediction: {str(e)}")
        return SinglePredictionResponse(
            success=False,
            error=f"Internal server error: {str(e)}"
        )

# Batch image emotion prediction endpoint
@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(
    files: List[UploadFile] = File(..., description="List of image files to analyze"),
    model: EmotionModel = Depends(get_emotion_model)
):
    """
    Predict emotions from multiple images
    
    Args:
        files: List of image files
        model: Loaded emotion detection model
        
    Returns:
        List of emotion predictions
    """
    predictions = []
    errors = []
    
    # Limit batch size for performance
    max_batch_size = 10
    if files is None or len(files) == 0:
        logger.warning("Batch request missing files")
        raise HTTPException(status_code=400, detail={"error": "No file uploaded"})

    if len(files) > max_batch_size:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Batch size too large. Maximum {max_batch_size} images allowed."}
        )
    
    try:
        # Process each image
        for i, file in enumerate(files):
            try:
                # Validate file
                try:
                    validate_upload(file)
                except HTTPException as e:
                    logger.warning(f"Batch invalid file {i+1}: {e.detail}")
                    errors.append(f"File {i+1}: {getattr(e, 'detail', {'error':'Invalid file'})}")
                    continue
                
                # Read and validate image
                image_data = await file.read()
                if not validate_image(image_data):
                    errors.append(f"File {i+1}: Invalid image file")
                    continue
                
                # Preprocess image
                processed_image = preprocess_image(image_data)
                if processed_image is None:
                    errors.append(f"File {i+1}: Failed to preprocess image")
                    continue
                
                # Make prediction
                prediction = await model.predict_single(processed_image)
                
                if prediction is None:
                    errors.append(f"File {i+1}: No face detected")
                    continue
                
                predictions.append(EmotionPrediction(
                    emotion=prediction['emotion'],
                    confidence=prediction['confidence'],
                    bounding_box=prediction.get('bounding_box'),
                    faces_detected=prediction.get('faces_detected')
                ))
                
            except Exception as e:
                logger.error(f"Error processing file {i+1}: {str(e)}")
                errors.append(f"File {i+1}: {str(e)}")
        
        return BatchPredictionResponse(
            success=len(predictions) > 0,
            predictions=predictions,
            total_processed=len(predictions),
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Error in batch prediction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": f"Internal server error: {str(e)}"}
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Mind Bridge AI ML Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "predict_single": "/predict/emotion",
            "predict_batch": "/predict/batch",
            "docs": "/docs"
        }
    }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
