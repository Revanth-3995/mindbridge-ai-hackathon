"""
Main FastAPI application with Socket.IO integration.
Entry point for the Mind Bridge AI backend service.
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import uvicorn
from datetime import datetime
import os

from config import settings
from database import init_db, check_db_connection, get_db_info
from websockets import sio
from auth import get_current_active_user, User
from celery_app import celery_app, health_check

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE) if settings.LOG_FILE else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Mind Bridge AI application...")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Check database connection
    if not check_db_connection():
        logger.error("Database connection check failed")
        raise Exception("Database connection failed")
    
    # Log database info
    db_info = get_db_info()
    logger.info(f"Database info: {db_info}")
    
    # Test Celery connection
    try:
        result = health_check.delay()
        logger.info("Celery connection test initiated")
    except Exception as e:
        logger.warning(f"Celery connection test failed: {e}")
    
    logger.info("Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mind Bridge AI application...")
    logger.info("Application shutdown completed")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered mental health and wellness platform",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1"]
)

# Mount static files
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Socket.IO integration
from socketio import ASGIApp
socketio_app = ASGIApp(sio, app)

# Health check endpoints
@app.get("/health")
async def health_check_endpoint():
    """Health check endpoint."""
    db_connected = check_db_connection()
    db_info = get_db_info()
    
    return {
        "status": "healthy" if db_connected else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "database": db_info,
        "services": {
            "database": "connected" if db_connected else "disconnected",
            "redis": "unknown",  # Could add Redis health check
            "celery": "unknown"  # Could add Celery health check
        }
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with service status."""
    db_connected = check_db_connection()
    db_info = get_db_info()
    
    # Test Celery
    celery_status = "unknown"
    try:
        result = health_check.delay()
        celery_status = "connected"
    except Exception as e:
        celery_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_connected else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "environment": {
            "debug": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
            "database_url": db_info.get("url", "unknown")
        },
        "services": {
            "database": {
                "status": "connected" if db_connected else "disconnected",
                "info": db_info
            },
            "celery": {
                "status": celery_status,
                "broker": settings.CELERY_BROKER_URL,
                "backend": settings.CELERY_RESULT_BACKEND
            },
            "redis": {
                "status": "unknown",
                "url": settings.REDIS_URL
            }
        }
    }

# API Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Documentation not available in production",
        "health": "/health"
    }

@app.get("/api/v1/status")
async def api_status(current_user: User = Depends(get_current_active_user)):
    """API status endpoint requiring authentication."""
    return {
        "status": "active",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# User endpoints
@app.get("/api/v1/users/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return {
        "user": current_user.to_dict(),
        "timestamp": datetime.utcnow().isoformat()
    }

# Chat session endpoints
@app.get("/api/v1/sessions")
async def get_user_sessions(current_user: User = Depends(get_current_active_user)):
    """Get user's chat sessions."""
    from database import get_db_context
    from models import ChatSession
    
    with get_db_context() as db:
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id,
            ChatSession.is_active == True
        ).order_by(ChatSession.last_activity.desc()).all()
        
        return {
            "sessions": [session.to_dict() for session in sessions],
            "count": len(sessions),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/api/v1/sessions")
async def create_session(
    title: str,
    description: str = None,
    session_type: str = "general",
    current_user: User = Depends(get_current_active_user)
):
    """Create a new chat session."""
    from database import get_db_context
    from models import ChatSession
    
    with get_db_context() as db:
        session = ChatSession(
            user_id=current_user.id,
            title=title,
            description=description,
            session_type=session_type
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return {
            "session": session.to_dict(),
            "message": "Session created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# WebSocket endpoint
@app.get("/socket.io/")
async def socketio_info():
    """Socket.IO information endpoint."""
    return {
        "message": "Socket.IO endpoint",
        "url": "/socket.io/",
        "transports": ["websocket", "polling"],
        "timestamp": datetime.utcnow().isoformat()
    }

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:socketio_app",  # Use socketio_app for Socket.IO support
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG
    )
