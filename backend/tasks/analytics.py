"""
Analytics tasks for data processing, reporting, and insights generation.
"""

from celery_app import analytics_task
from database import get_db_context
from models import User, ChatSession, Message, AIResponse
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@analytics_task
def generate_daily_report():
    """Generate daily analytics report."""
    try:
        with get_db_context() as db:
            today = datetime.utcnow().date()
            
            # User statistics
            total_users = db.query(User).count()
            active_users_today = db.query(User).filter(
                User.last_login >= today
            ).count()
            
            # Session statistics
            total_sessions = db.query(ChatSession).count()
            sessions_today = db.query(ChatSession).filter(
                ChatSession.created_at >= today
            ).count()
            
            # Message statistics
            total_messages = db.query(Message).count()
            messages_today = db.query(Message).filter(
                Message.created_at >= today
            ).count()
            
            # AI response statistics
            total_ai_responses = db.query(AIResponse).count()
            ai_responses_today = db.query(AIResponse).filter(
                AIResponse.created_at >= today
            ).count()
            
            report = {
                "date": today.isoformat(),
                "users": {
                    "total": total_users,
                    "active_today": active_users_today
                },
                "sessions": {
                    "total": total_sessions,
                    "created_today": sessions_today
                },
                "messages": {
                    "total": total_messages,
                    "sent_today": messages_today
                },
                "ai_responses": {
                    "total": total_ai_responses,
                    "generated_today": ai_responses_today
                }
            }
            
            logger.info(f"Daily report generated: {report}")
            return {"success": True, "report": report}
            
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        return {"error": str(e)}

@analytics_task
def analyze_user_engagement(user_id: int):
    """Analyze user engagement metrics."""
    try:
        with get_db_context() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            # Get user's sessions and messages
            sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).all()
            messages = db.query(Message).filter(Message.user_id == user_id).all()
            
            # Calculate engagement metrics
            total_sessions = len(sessions)
            total_messages = len(messages)
            avg_messages_per_session = total_messages / total_sessions if total_sessions > 0 else 0
            
            # Calculate session duration
            total_duration = sum(session.session_duration for session in sessions)
            avg_session_duration = total_duration / total_sessions if total_sessions > 0 else 0
            
            engagement_data = {
                "user_id": user_id,
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "avg_messages_per_session": avg_messages_per_session,
                "total_session_duration": total_duration,
                "avg_session_duration": avg_session_duration,
                "last_activity": user.last_login.isoformat() if user.last_login else None
            }
            
            logger.info(f"User engagement analyzed for user {user_id}")
            return {"success": True, "engagement": engagement_data}
            
    except Exception as e:
        logger.error(f"Error analyzing user engagement: {e}")
        return {"error": str(e)}
