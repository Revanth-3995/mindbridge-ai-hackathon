# Mind Bridge AI ML Service - Deployment Guide

## 🚀 Quick Start

### Local Testing (Recommended First)

1. **Navigate to the ml-models directory**:
   ```bash
   cd ml-models
   ```

2. **Run the service** (Windows):
   ```bash
   start.bat
   ```
   
   Or manually:
   ```bash
   # Activate virtual environment
   venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Start service
   uvicorn main:app --reload --port 8001
   ```

3. **Test the service**:
   ```bash
   # Health check
   curl http://localhost:8001/health
   
   # Run test script
   python test_service.py
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

### RunPod Deployment

1. **Upload files to RunPod**:
   - Upload the entire `ml-models` folder to your RunPod workspace
   - Set working directory to `/workspace/ml-models`

2. **Configure RunPod**:
   - Select a GPU-enabled template (RTX 3080, 4090, etc.)
   - Set port 8000 as public
   - Use the provided Dockerfile

3. **Environment Variables** (optional):
   ```bash
   CUDA_VISIBLE_DEVICES=0
   LOG_LEVEL=INFO
   ```

## 📋 Service Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service information |
| `/health` | GET | Health check and status |
| `/predict/emotion` | POST | Single image emotion detection |
| `/predict/batch` | POST | Batch image emotion detection |
| `/docs` | GET | Interactive API documentation |

## 🧪 Testing

### Manual Testing

1. **Health Check**:
   ```bash
   curl http://localhost:8001/health
   ```

2. **Single Image Prediction**:
   ```bash
   curl -X POST "http://localhost:8001/predict/emotion" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@your_image.jpg"
   ```

3. **Batch Prediction**:
   ```bash
   curl -X POST "http://localhost:8001/predict/batch" \
        -H "Content-Type: multipart/form-data" \
        -F "files=@image1.jpg" \
        -F "files=@image2.jpg"
   ```

### Automated Testing

Run the test script:
```bash
python test_service.py
```

## 🔧 Configuration

### Environment Variables

- `CUDA_VISIBLE_DEVICES`: GPU device ID (default: 0)
- `LOG_LEVEL`: Logging level (default: INFO)
- `MODEL_CACHE_DIR`: Model cache directory (default: /app/models)

### Model Configuration

The service automatically loads:
- **Text Model**: `j-hartmann/emotion-english-distilroberta-base`
- **Image Model**: Custom CNN for emotion detection
- **Face Detection**: OpenCV Haar cascades

## 📊 Performance

### Expected Performance

- **Single Image**: ~200-500ms (GPU), ~1-2s (CPU)
- **Batch Processing**: ~100-300ms per image (GPU)
- **Memory Usage**: ~2-4GB RAM, ~1-2GB VRAM
- **Concurrent Requests**: Up to 10 simultaneous

### Optimization Tips

1. **GPU Acceleration**: Ensure CUDA is properly installed
2. **Batch Processing**: Use batch endpoint for multiple images
3. **Image Size**: Resize large images before sending
4. **Model Caching**: Models are cached in memory after first load

## 🐛 Troubleshooting

### Common Issues

1. **CUDA out of memory**:
   - Reduce batch size
   - Use CPU mode
   - Check GPU memory usage

2. **Model loading fails**:
   - Check internet connection
   - Verify Hugging Face access
   - Check disk space

3. **No faces detected**:
   - Ensure images contain clear faces
   - Check image quality and lighting
   - Try different image formats

4. **Slow inference**:
   - Enable GPU acceleration
   - Check CUDA installation
   - Monitor system resources

### Logs

Check application logs for detailed error information:
```bash
# Docker logs
docker logs <container_id>

# Local logs
# Check console output when running uvicorn
```

## 🔒 Security

### Production Considerations

1. **Authentication**: Add API key authentication
2. **Rate Limiting**: Implement request rate limiting
3. **Input Validation**: Validate all input files
4. **CORS**: Configure appropriate CORS settings
5. **HTTPS**: Use HTTPS in production

### Docker Security

- Non-root user in container
- Minimal base image
- No unnecessary packages
- Health checks enabled

## 📈 Monitoring

### Health Checks

The service provides comprehensive health monitoring:
- Service status
- GPU availability
- Model loading status
- Memory usage

### Metrics

Monitor these key metrics:
- Request latency
- Success/failure rates
- GPU utilization
- Memory usage
- Model inference time

## 🚀 Scaling

### Horizontal Scaling

- Use load balancer (nginx, HAProxy)
- Deploy multiple container instances
- Use Redis for session management
- Implement health checks

### Vertical Scaling

- Increase GPU memory
- Add more CPU cores
- Increase container resources
- Optimize model size

## 📝 API Documentation

Visit `/docs` endpoint for interactive API documentation:
- http://localhost:8001/docs (local)
- http://your-runpod-url:8000/docs (RunPod)

## 🆘 Support

For issues and questions:
1. Check the logs for error details
2. Verify all dependencies are installed
3. Test with the provided test script
4. Check GPU/CUDA installation
5. Review the README.md for detailed information
