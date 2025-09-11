"""
Maintenance tasks for cleanup, backups, and system maintenance.
"""

from celery_app import maintenance_task
from database import get_db_context
from models import ChatSession, Message, AIResponse
import logging
from datetime import datetime, timedelta
import os
import shutil

logger = logging.getLogger(__name__)

@maintenance_task
def cleanup_expired_sessions():
    """Clean up expired and inactive sessions."""
    try:
        with get_db_context() as db:
            # Archive sessions inactive for more than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            expired_sessions = db.query(ChatSession).filter(
                ChatSession.last_activity < cutoff_date,
                ChatSession.is_active == True
            ).all()
            
            archived_count = 0
            for session in expired_sessions:
                session.is_active = False
                session.is_archived = True
                archived_count += 1
            
            db.commit()
            
            logger.info(f"Archived {archived_count} expired sessions")
            return {"success": True, "archived_sessions": archived_count}
            
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {e}")
        return {"error": str(e)}

@maintenance_task
def backup_user_data():
    """Create backup of user data."""
    try:
        with get_db_context() as db:
            # Get all users
            users = db.query(User).all()
            
            # Create backup directory
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # Create backup file
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"user_backup_{timestamp}.json")
            
            # Export user data (simplified)
            user_data = []
            for user in users:
                user_data.append({
                    "id": user.id,
                    "email": user.email,
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                })
            
            # Write backup file
            import json
            with open(backup_file, 'w') as f:
                json.dump(user_data, f, indent=2)
            
            logger.info(f"User data backup created: {backup_file}")
            return {"success": True, "backup_file": backup_file, "users_backed_up": len(users)}
            
    except Exception as e:
        logger.error(f"Error creating user data backup: {e}")
        return {"error": str(e)}

@maintenance_task
def cleanup_old_logs():
    """Clean up old log files."""
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return {"success": True, "message": "No logs directory found"}
        
        # Remove log files older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        removed_files = 0
        
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(log_dir, filename)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_mtime < cutoff_date:
                    os.remove(file_path)
                    removed_files += 1
        
        logger.info(f"Cleaned up {removed_files} old log files")
        return {"success": True, "removed_files": removed_files}
        
    except Exception as e:
        logger.error(f"Error cleaning up old logs: {e}")
        return {"error": str(e)}

@maintenance_task
def optimize_database():
    """Optimize database performance."""
    try:
        with get_db_context() as db:
            # Database-specific optimization commands
            if "sqlite" in str(db.bind.url):
                # SQLite optimization
                db.execute("VACUUM")
                db.execute("ANALYZE")
                logger.info("SQLite database optimized")
            else:
                # PostgreSQL optimization
                db.execute("VACUUM ANALYZE")
                logger.info("PostgreSQL database optimized")
            
            return {"success": True, "message": "Database optimized"}
            
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return {"error": str(e)}
