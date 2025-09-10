"""
Celery configuration for background tasks.
Handles asynchronous processing, AI model inference, and scheduled tasks.
"""

from celery import Celery
from celery.schedules import crontab
from config import settings
import logging

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "mindbridge_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.ai_processing",
        "tasks.notifications",
        "tasks.analytics",
        "tasks.maintenance"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "tasks.ai_processing.*": {"queue": "ai_queue"},
        "tasks.notifications.*": {"queue": "notification_queue"},
        "tasks.analytics.*": {"queue": "analytics_queue"},
        "tasks.maintenance.*": {"queue": "maintenance_queue"},
    },
    
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    worker_prefetch_multiplier=1,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Worker settings
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-sessions": {
            "task": "tasks.maintenance.cleanup_expired_sessions",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        },
        "generate-analytics-report": {
            "task": "tasks.analytics.generate_daily_report",
            "schedule": crontab(hour=0, minute=30),  # Daily at 12:30 AM
        },
        "backup-user-data": {
            "task": "tasks.maintenance.backup_user_data",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Weekly on Sunday at 3 AM
        },
        "update-ai-models": {
            "task": "tasks.ai_processing.update_model_cache",
            "schedule": crontab(hour=4, minute=0),  # Daily at 4 AM
        },
        "send-weekly-digest": {
            "task": "tasks.notifications.send_weekly_digest",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Monday at 9 AM
        },
    },
    
    # Error handling
    task_acks_late=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Monitoring
    worker_hijack_root_logger=False,
    worker_log_color=False,
)

# Task decorators for different queues
def ai_task(func):
    """Decorator for AI processing tasks."""
    return celery_app.task(
        bind=True,
        queue="ai_queue",
        name=f"ai_processing.{func.__name__}"
    )(func)

def notification_task(func):
    """Decorator for notification tasks."""
    return celery_app.task(
        bind=True,
        queue="notification_queue",
        name=f"notifications.{func.__name__}"
    )(func)

def analytics_task(func):
    """Decorator for analytics tasks."""
    return celery_app.task(
        bind=True,
        queue="analytics_queue",
        name=f"analytics.{func.__name__}"
    )(func)

def maintenance_task(func):
    """Decorator for maintenance tasks."""
    return celery_app.task(
        bind=True,
        queue="maintenance_queue",
        name=f"maintenance.{func.__name__}"
    )(func)

# Health check task
@celery_app.task(bind=True)
def health_check(self):
    """Health check task for monitoring."""
    return {
        "status": "healthy",
        "worker": self.request.hostname,
        "task_id": self.request.id,
        "timestamp": self.request.eta
    }

# Utility functions
def get_task_status(task_id: str) -> dict:
    """Get task status by ID."""
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.successful() else None,
            "error": str(result.result) if result.failed() else None,
            "traceback": result.traceback if result.failed() else None,
        }
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return {
            "task_id": task_id,
            "status": "UNKNOWN",
            "error": str(e)
        }

def cancel_task(task_id: str) -> bool:
    """Cancel a running task."""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception as e:
        logger.error(f"Error canceling task: {e}")
        return False

def get_active_tasks() -> list:
    """Get list of active tasks."""
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        return active_tasks
    except Exception as e:
        logger.error(f"Error getting active tasks: {e}")
        return []

def get_worker_stats() -> dict:
    """Get worker statistics."""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting worker stats: {e}")
        return {}

# Task monitoring
class TaskMonitor:
    """Task monitoring utility."""
    
    def __init__(self):
        self.celery_app = celery_app
    
    def get_queue_lengths(self) -> dict:
        """Get queue lengths."""
        try:
            inspect = self.celery_app.control.inspect()
            reserved = inspect.reserved()
            active = inspect.active()
            
            queue_lengths = {}
            for worker, tasks in reserved.items():
                queue_lengths[worker] = {
                    "reserved": len(tasks),
                    "active": len(active.get(worker, []))
                }
            return queue_lengths
        except Exception as e:
            logger.error(f"Error getting queue lengths: {e}")
            return {}
    
    def get_failed_tasks(self) -> list:
        """Get list of failed tasks."""
        try:
            inspect = self.celery_app.control.inspect()
            failed = inspect.failed()
            return failed
        except Exception as e:
            logger.error(f"Error getting failed tasks: {e}")
            return []
    
    def retry_failed_task(self, task_id: str) -> bool:
        """Retry a failed task."""
        try:
            result = self.celery_app.AsyncResult(task_id)
            result.retry()
            return True
        except Exception as e:
            logger.error(f"Error retrying task: {e}")
            return False

# Initialize task monitor
task_monitor = TaskMonitor()

# Export celery app for use in other modules
__all__ = [
    "celery_app",
    "ai_task",
    "notification_task", 
    "analytics_task",
    "maintenance_task",
    "get_task_status",
    "cancel_task",
    "get_active_tasks",
    "get_worker_stats",
    "TaskMonitor",
    "task_monitor"
]
