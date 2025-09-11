# Mind Bridge AI ML Inference Service

GPU-optimized FastAPI service for emotion detection, designed for RunPod deployment.

## Features

- **Single Image Emotion Detection**: `/predict/emotion` endpoint
- **Batch Image Processing**: `/predict/batch` endpoint  
- **Health Monitoring**: `/health` endpoint
- **GPU Acceleration**: CUDA 11.8 support with PyTorch
- **Face Detection**: OpenCV Haar cascades
- **Multiple Model Support**: Hugging Face transformers + custom CNN
- **Production Ready**: Docker containerization, logging, error handling

## Quick Start

### Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the service**:
   ```bash
   uvicorn main:app --reload --port 8001
   ```

3. **Test health endpoint**:
   ```bash
   curl http://localhost:8001/health
   ```

### Docker Deployment

1. **Build the image**:
   ```bash
   docker build -t mindbridge-ml .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8000:8000 mindbridge-ml
   ```

3. **Test the service**:
   ```bash
   curl http://localhost:8000/health
   ```

## API Endpoints

### Health Check
```bash
GET /health
```
Returns service status and GPU availability.

### Single Image Prediction
```bash
POST /predict/emotion
Content-Type: multipart/form-data

file: [image file]
```

**Response**:
```json
{
  "success": true,
  "prediction": {
    "emotion": "happy",
    "confidence": 0.95,
    "bounding_box": [100, 150, 200, 200]
  }
}
```

Correct usage examples:

- curl (Linux/macOS):
```bash
curl -X POST "http://localhost:9000/predict/emotion" -F "file=@testimage.jpeg"
```

- PowerShell (Windows):
```powershell
Invoke-WebRequest -Uri "http://localhost:9000/predict/emotion" -Method Post -Form @{ file = Get-Item "testimage.jpeg" }
```

### Batch Image Prediction
```bash
POST /predict/batch
Content-Type: multipart/form-data

files: [image1, image2, image3, ...]
```

**Response**:
```json
{
  "success": true,
  "predictions": [
    {
      "emotion": "happy",
      "confidence": 0.95,
      "bounding_box": [100, 150, 200, 200]
    },
    {
      "emotion": "sad",
      "confidence": 0.87,
      "bounding_box": [50, 80, 180, 180]
    }
  ],
  "total_processed": 2,
  "errors": []
}
```

## Supported Image Formats

- JPEG
- PNG
- BMP
- TIFF
- WEBP

## Emotion Labels

The service detects the following emotions:
- `angry`
- `disgust`
- `fear`
- `happy`
- `sad`
- `surprise`
- `neutral`

## GPU Requirements

- CUDA 11.8 compatible GPU
- Minimum 4GB VRAM recommended
- PyTorch with CUDA support

## RunPod Deployment

1. **Upload to RunPod**:
   - Upload the entire `ml-models` folder
   - Set the working directory to `/workspace/ml-models`

2. **Configure RunPod**:
   - Select a GPU-enabled template
   - Set port 8000 as public
   - Use the provided Dockerfile

3. **Environment Variables** (optional):
   ```bash
   CUDA_VISIBLE_DEVICES=0
   MODEL_CACHE_DIR=/workspace/models
   LOG_LEVEL=INFO
   ```

## Performance Optimization

- **Model Caching**: Models are loaded once and cached in memory
- **Batch Processing**: Efficient batch inference for multiple images
- **GPU Acceleration**: Automatic GPU detection and utilization
- **Image Preprocessing**: Optimized image resizing and normalization

## Error Handling

The service includes comprehensive error handling:
- Invalid image format detection
- Face detection failures
- Model loading errors
- GPU memory management
- Graceful degradation when models fail to load

## Monitoring

- Health check endpoint for service monitoring
- Structured logging with timestamps
- Error tracking and reporting
- Performance metrics

## Development

### Project Structure
```
ml-models/
├── main.py              # FastAPI application
├── emotion_model.py     # Emotion detection models
├── utils.py            # Utility functions
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container configuration
└── README.md          # This file
```

### Adding New Models

1. Extend the `EmotionModel` class in `emotion_model.py`
2. Implement the prediction logic
3. Update the model loading in `load_model()`
4. Test with the existing endpoints

### Testing

```bash
# Test with curl
curl -X POST "http://localhost:8001/predict/emotion" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@test_image.jpg"

# Test batch processing
curl -X POST "http://localhost:8001/predict/batch" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "files=@image1.jpg" \
     -F "files=@image2.jpg"
```

## Troubleshooting

### Common Issues

1. **CUDA out of memory**: Reduce batch size or use CPU
2. **Model loading fails**: Check internet connection for Hugging Face models
3. **No faces detected**: Ensure images contain clear, front-facing faces
4. **Slow inference**: Enable GPU acceleration and check CUDA installation

### Logs

Check the application logs for detailed error information:
```bash
docker logs <container_id>
```

## License

This project is part of the Mind Bridge AI platform.
