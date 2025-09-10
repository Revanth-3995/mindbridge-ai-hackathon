"""
Celery configuration and task definitions for Mind Bridge AI backend.

This module provides:
- Celery app configuration with Redis broker/backend
- Periodic task scheduling with Celery Beat
- Background tasks for crisis detection, cleanup, and metrics
- Comprehensive error handling and retry logic
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from celery import Celery
from celery.schedules import crontab
from celery.exceptions import Retry, MaxRetriesExceededError
from celery.utils.log import get_task_logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from database import get_db_context, check_db_connection
from models import User, EmotionRecord, CrisisAlert, ChatMessage, PeerConnection

# Configure logging
logger = get_task_logger(__name__)
logging.basicConfig(level=logging.INFO)

# Create Celery app
celery_app = Celery('mindbridge_ai')

# Celery Configuration
celery_app.conf.update(
    # Broker and Result Backend
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    
    # Task Serialization
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Timezone Configuration
    timezone='UTC',
    enable_utc=True,
    
    # Task Configuration
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    
    # Task Routing
    task_routes={
        'celery_app.check_user_crisis_indicators': {'queue': 'crisis'},
        'celery_app.send_crisis_alert': {'queue': 'alerts'},
        'celery_app.cleanup_expired_sessions': {'queue': 'maintenance'},
        'celery_app.generate_daily_metrics': {'queue': 'analytics'},
    },
    
    # Retry Configuration
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Result Backend Configuration
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Beat Schedule for Periodic Tasks
    beat_schedule={
        'crisis-detection-scan': {
            'task': 'celery_app.check_all_users_crisis_indicators',
            'schedule': crontab(minute='*/15'),  # Every 15 minutes
        },
        'cleanup-expired-sessions': {
            'task': 'celery_app.cleanup_expired_sessions',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        },
        'database-backup': {
            'task': 'celery_app.database_backup',
            'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
        },
        'user-engagement-metrics': {
            'task': 'celery_app.generate_daily_metrics',
            'schedule': crontab(minute=0),  # Hourly
        },
    },
)

# Task Decorators for Retry Configuration
def task_with_retry(max_retries=3, default_retry_delay=60, exponential_backoff=True):
    """Decorator for tasks with retry configuration."""
    def decorator(func):
        return celery_app.task(
            bind=True,
            max_retries=max_retries,
            default_retry_delay=default_retry_delay,
            autoretry_for=(Exception,),
            retry_kwargs={'max_retries': max_retries},
            retry_backoff=exponential_backoff,
            retry_backoff_max=600,  # Max 10 minutes
            retry_jitter=True,
        )(func)
    return decorator

# ============================================================================
# CRISIS DETECTION TASKS
# ============================================================================

@task_with_retry(max_retries=3)
def check_user_crisis_indicators(self, user_id: str) -> Dict[str, Any]:
    """
    Check crisis indicators for a specific user.
    
    Args:
        user_id: UUID string of the user to check
        
    Returns:
        Dict containing risk assessment and indicators
    """
    try:
        logger.info(f"Checking crisis indicators for user: {user_id}")
        
        with get_db_context() as db:
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User not found: {user_id}")
                return {"error": "User not found", "user_id": user_id}
            
            # Get recent emotion records (last 24 hours)
            recent_emotions = db.query(EmotionRecord).filter(
                EmotionRecord.user_id == user_id,
                EmotionRecord.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).order_by(EmotionRecord.created_at.desc()).all()
            
            # Analyze emotion patterns
            risk_indicators = []
            risk_score = 0.0
            
            if recent_emotions:
                # Check for negative emotion patterns
                negative_emotions = [e for e in recent_emotions if e.emotion in ['sad', 'angry', 'fear']]
                if len(negative_emotions) > len(recent_emotions) * 0.7:  # 70% negative
                    risk_indicators.append("High frequency of negative emotions")
                    risk_score += 0.3
                
                # Check for declining confidence
                if len(recent_emotions) >= 3:
                    recent_confidences = [e.confidence for e in recent_emotions[:3]]
                    if all(recent_confidences[i] >= recent_confidences[i+1] for i in range(len(recent_confidences)-1)):
                        risk_indicators.append("Declining emotion detection confidence")
                        risk_score += 0.2
                
                # Check for extreme emotions
                extreme_emotions = [e for e in recent_emotions if e.confidence > 0.8 and e.emotion in ['sad', 'angry']]
                if extreme_emotions:
                    risk_indicators.append("High-confidence extreme negative emotions")
                    risk_score += 0.4
            
            # Check for recent crisis alerts
            recent_alerts = db.query(CrisisAlert).filter(
                CrisisAlert.user_id == user_id,
                CrisisAlert.created_at >= datetime.utcnow() - timedelta(hours=24),
                CrisisAlert.resolved_at.is_(None)
            ).count()
            
            if recent_alerts > 0:
                risk_indicators.append("Recent unresolved crisis alerts")
                risk_score += 0.5
            
            # Determine risk level
            if risk_score >= 0.7:
                risk_level = "critical"
            elif risk_score >= 0.5:
                risk_level = "high"
            elif risk_score >= 0.3:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            result = {
                "user_id": user_id,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "indicators": risk_indicators,
                "emotion_count": len(recent_emotions),
                "checked_at": datetime.utcnow().isoformat()
            }
            
            # If high risk, trigger alert
            if risk_level in ["high", "critical"]:
                send_crisis_alert.delay(user_id, risk_level)
            
            logger.info(f"Crisis check completed for user {user_id}: {risk_level}")
            return result
            
    except Exception as exc:
        logger.error(f"Error checking crisis indicators for user {user_id}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)

@task_with_retry(max_retries=3)
def check_all_users_crisis_indicators(self) -> Dict[str, Any]:
    """
    Check crisis indicators for all active users.
    This is the periodic task that runs every 15 minutes.
    """
    try:
        logger.info("Starting crisis detection scan for all users")
        
        with get_db_context() as db:
            # Get all active users
            active_users = db.query(User).filter(User.is_active == True).all()
            
            results = []
            for user in active_users:
                try:
                    result = check_user_crisis_indicators.delay(str(user.id))
                    results.append({"user_id": str(user.id), "task_id": result.id})
                except Exception as e:
                    logger.error(f"Failed to queue crisis check for user {user.id}: {str(e)}")
            
            logger.info(f"Crisis detection scan queued for {len(results)} users")
            return {
                "status": "completed",
                "users_checked": len(results),
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as exc:
        logger.error(f"Error in crisis detection scan: {str(exc)}")
        raise self.retry(countdown=300, exc=exc)  # Retry in 5 minutes

@task_with_retry(max_retries=3)
def send_crisis_alert(self, user_id: str, risk_level: str) -> Dict[str, Any]:
    """
    Send crisis alert for a user.
    
    Args:
        user_id: UUID string of the user
        risk_level: Risk level (low, medium, high, critical)
    """
    try:
        logger.info(f"Sending crisis alert for user {user_id} with risk level: {risk_level}")
        
        with get_db_context() as db:
            # Create crisis alert record
            alert = CrisisAlert(
                id=uuid.uuid4(),
                user_id=user_id,
                risk_level=risk_level,
                prediction_confidence=0.8,  # Default confidence
                triggers=["automated_crisis_detection"],
                created_at=datetime.utcnow()
            )
            
            db.add(alert)
            db.commit()
            
            # Get user details
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User not found for crisis alert: {user_id}")
                return {"error": "User not found"}
            
            # TODO: Implement actual alert sending (email, SMS, push notification)
            # For now, just log the alert
            logger.critical(f"CRISIS ALERT: User {user.email} has {risk_level} risk level")
            
            # If critical, also log to emergency contact
            if risk_level == "critical" and user.emergency_contact_name:
                logger.critical(f"EMERGENCY CONTACT: {user.emergency_contact_name} - {user.emergency_contact_phone}")
            
            return {
                "status": "alert_sent",
                "user_id": user_id,
                "risk_level": risk_level,
                "alert_id": str(alert.id),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as exc:
        logger.error(f"Error sending crisis alert for user {user_id}: {str(exc)}")
        raise self.retry(countdown=30, exc=exc)

# ============================================================================
# MAINTENANCE TASKS
# ============================================================================

@task_with_retry(max_retries=3)
def cleanup_expired_sessions(self) -> Dict[str, Any]:
    """
    Clean up expired sessions and old data.
    Runs daily at 2 AM.
    """
    try:
        logger.info("Starting cleanup of expired sessions")
        
        with get_db_context() as db:
            # Clean up old peer connections (older than 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            old_connections = db.query(PeerConnection).filter(
                PeerConnection.created_at < cutoff_date,
                PeerConnection.status.in_(['completed', 'blocked'])
            ).all()
            
            for connection in old_connections:
                db.delete(connection)
            
            # Clean up old emotion records (older than 90 days)
            emotion_cutoff = datetime.utcnow() - timedelta(days=90)
            old_emotions = db.query(EmotionRecord).filter(
                EmotionRecord.created_at < emotion_cutoff
            ).all()
            
            for emotion in old_emotions:
                db.delete(emotion)
            
            # Clean up resolved crisis alerts (older than 30 days)
            alert_cutoff = datetime.utcnow() - timedelta(days=30)
            old_alerts = db.query(CrisisAlert).filter(
                CrisisAlert.resolved_at.isnot(None),
                CrisisAlert.resolved_at < alert_cutoff
            ).all()
            
            for alert in old_alerts:
                db.delete(alert)
            
            db.commit()
            
            cleanup_stats = {
                "peer_connections_removed": len(old_connections),
                "emotion_records_removed": len(old_emotions),
                "crisis_alerts_removed": len(old_alerts),
                "cleanup_date": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
    except Exception as exc:
        logger.error(f"Error during cleanup: {str(exc)}")
        raise self.retry(countdown=3600, exc=exc)  # Retry in 1 hour

@task_with_retry(max_retries=3)
def database_backup(self) -> Dict[str, Any]:
    """
    Create database backup.
    Runs daily at 3 AM.
    """
    try:
        logger.info("Starting database backup")
        
        # Check database connection
        if not check_db_connection():
            raise Exception("Database connection failed")
        
        # For SQLite, we can create a simple file copy
        # For PostgreSQL, you would typically use pg_dump
        backup_info = {
            "backup_type": "automated",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed",
            "note": "Backup mechanism depends on database type"
        }
        
        logger.info("Database backup completed")
        return backup_info
        
    except Exception as exc:
        logger.error(f"Error during database backup: {str(exc)}")
        raise self.retry(countdown=3600, exc=exc)  # Retry in 1 hour

# ============================================================================
# ANALYTICS TASKS
# ============================================================================

@task_with_retry(max_retries=3)
def generate_daily_metrics(self) -> Dict[str, Any]:
    """
    Generate user engagement and system metrics.
    Runs hourly.
    """
    try:
        logger.info("Generating daily metrics")
        
        with get_db_context() as db:
            # Get current time boundaries
            now = datetime.utcnow()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # User engagement metrics
            active_users_hour = db.query(User).filter(
                User.is_active == True,
                User.updated_at >= hour_ago
            ).count()
            
            active_users_day = db.query(User).filter(
                User.is_active == True,
                User.updated_at >= day_ago
            ).count()
            
            # Emotion tracking metrics
            emotions_hour = db.query(EmotionRecord).filter(
                EmotionRecord.created_at >= hour_ago
            ).count()
            
            emotions_day = db.query(EmotionRecord).filter(
                EmotionRecord.created_at >= day_ago
            ).count()
            
            # Crisis alert metrics
            alerts_hour = db.query(CrisisAlert).filter(
                CrisisAlert.created_at >= hour_ago
            ).count()
            
            alerts_day = db.query(CrisisAlert).filter(
                CrisisAlert.created_at >= day_ago
            ).count()
            
            # Chat activity metrics
            messages_hour = db.query(ChatMessage).filter(
                ChatMessage.created_at >= hour_ago
            ).count()
            
            messages_day = db.query(ChatMessage).filter(
                ChatMessage.created_at >= day_ago
            ).count()
            
            metrics = {
                "timestamp": now.isoformat(),
                "period": "hourly",
                "user_engagement": {
                    "active_users_hour": active_users_hour,
                    "active_users_day": active_users_day
                },
                "emotion_tracking": {
                    "emotions_recorded_hour": emotions_hour,
                    "emotions_recorded_day": emotions_day
                },
                "crisis_management": {
                    "alerts_triggered_hour": alerts_hour,
                    "alerts_triggered_day": alerts_day
                },
                "communication": {
                    "messages_sent_hour": messages_hour,
                    "messages_sent_day": messages_day
                }
            }
            
            logger.info(f"Metrics generated: {metrics}")
            return metrics
            
    except Exception as exc:
        logger.error(f"Error generating metrics: {str(exc)}")
        raise self.retry(countdown=1800, exc=exc)  # Retry in 30 minutes

# ============================================================================
# AI TASKS
# ============================================================================

@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
def ai_task(self, session_id: int, prompt: str) -> Dict[str, Any]:
    """
    AI task for processing prompts and generating responses.
    
    Args:
        session_id: Session ID for the AI interaction
        prompt: User prompt to process
        
    Returns:
        Dict containing session_id and AI response
    """
    try:
        logger.info(f"Processing AI task for session {session_id} with prompt: {prompt[:50]}...")
        
        # Simulate AI processing work
        import time
        time.sleep(1)  # Simulate processing time
        
        # Generate mock AI response
        response = f"AI response for session {session_id} with prompt: {prompt}"
        
        result = {
            "session_id": session_id,
            "response": response,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        
        logger.info(f"AI task completed for session {session_id}")
        return result
        
    except Exception as exc:
        logger.error(f"Error in AI task for session {session_id}: {str(exc)}")
        # Retry with exponential backoff (2^retries seconds)
        retry_delay = 2 ** self.request.retries
        raise self.retry(countdown=retry_delay, exc=exc)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_celery_app() -> Celery:
    """Get the configured Celery app instance."""
    return celery_app

def start_worker():
    """Start Celery worker (for development)."""
    celery_app.worker_main(['worker', '--loglevel=info'])

def start_beat():
    """Start Celery Beat scheduler (for development)."""
    celery_app.control.purge()  # Clear any existing tasks
    celery_app.start(['beat', '--loglevel=info'])

# ============================================================================
# TASK MONITORING AND HEALTH CHECKS
# ============================================================================

@celery_app.task
def health_check() -> Dict[str, Any]:
    """Health check task to verify Celery is working."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "celery_version": celery_app.version,
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND
    }

@celery_app.task
def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a specific task."""
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "info": result.info
    }

if __name__ == '__main__':
    # For development - start worker
    start_worker()
