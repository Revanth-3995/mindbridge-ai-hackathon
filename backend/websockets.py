"""
Socket.IO event handlers for real-time communication.
Handles WebSocket connections, chat events, and real-time updates.
"""

import socketio
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import json

from config import settings
from database import get_db_context
from models import User, ChatSession, Message, AIResponse
from auth import get_current_user_from_token
from celery_app import ai_task

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    cors_allowed_origins=settings.CORS_ORIGINS,
    logger=settings.DEBUG,
    engineio_logger=settings.DEBUG
)

# Socket.IO event handlers
@sio.event
async def connect(sid: str, environ: Dict[str, Any], auth: Optional[Dict[str, str]] = None):
    """Handle client connection."""
    try:
        # Extract token from auth or query parameters
        token = None
        if auth and "token" in auth:
            token = auth["token"]
        elif "HTTP_AUTHORIZATION" in environ:
            auth_header = environ["HTTP_AUTHORIZATION"]
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
        
        if not token:
            logger.warning(f"Connection rejected: No token provided for session {sid}")
            return False
        
        # Verify token and get user
        try:
            user = await get_current_user_from_token(token)
            if not user or not user.is_active:
                logger.warning(f"Connection rejected: Invalid user for session {sid}")
                return False
            
            # Store user info in session
            await sio.save_session(sid, {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "connected_at": datetime.utcnow().isoformat()
            })
            
            # Join user to their personal room
            await sio.enter_room(sid, f"user_{user.id}")
            
            logger.info(f"User {user.username} connected with session {sid}")
            
            # Send connection confirmation
            await sio.emit("connected", {
                "message": "Successfully connected",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                },
                "timestamp": datetime.utcnow().isoformat()
            }, room=sid)
            
            return True
            
        except Exception as e:
            logger.error(f"Token verification failed for session {sid}: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Connection error for session {sid}: {e}")
        return False

@sio.event
async def disconnect(sid: str):
    """Handle client disconnection."""
    try:
        session_data = await sio.get_session(sid)
        if session_data:
            user_id = session_data.get("user_id")
            username = session_data.get("username")
            
            # Leave user room
            await sio.leave_room(sid, f"user_{user_id}")
            
            logger.info(f"User {username} disconnected from session {sid}")
            
            # Notify other clients if needed
            await sio.emit("user_disconnected", {
                "user_id": user_id,
                "username": username,
                "timestamp": datetime.utcnow().isoformat()
            }, room=f"user_{user_id}", skip_sid=sid)
            
    except Exception as e:
        logger.error(f"Disconnection error for session {sid}: {e}")

@sio.event
async def join_session(sid: str, data: Dict[str, Any]):
    """Join a chat session."""
    try:
        session_data = await sio.get_session(sid)
        if not session_data:
            await sio.emit("error", {"message": "Not authenticated"}, room=sid)
            return
        
        user_id = session_data["user_id"]
        session_id = data.get("session_id")
        
        if not session_id:
            await sio.emit("error", {"message": "Session ID required"}, room=sid)
            return
        
        # Verify user has access to session
        with get_db_context() as db:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if not session:
                await sio.emit("error", {"message": "Session not found or access denied"}, room=sid)
                return
            
            # Join session room
            await sio.enter_room(sid, f"session_{session_id}")
            
            # Send session info
            await sio.emit("session_joined", {
                "session": session.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }, room=sid)
            
            logger.info(f"User {user_id} joined session {session_id}")
            
    except Exception as e:
        logger.error(f"Error joining session: {e}")
        await sio.emit("error", {"message": "Failed to join session"}, room=sid)

@sio.event
async def leave_session(sid: str, data: Dict[str, Any]):
    """Leave a chat session."""
    try:
        session_id = data.get("session_id")
        if session_id:
            await sio.leave_room(sid, f"session_{session_id}")
            
            session_data = await sio.get_session(sid)
            user_id = session_data.get("user_id") if session_data else None
            
            await sio.emit("session_left", {
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }, room=sid)
            
            logger.info(f"User {user_id} left session {session_id}")
            
    except Exception as e:
        logger.error(f"Error leaving session: {e}")

@sio.event
async def send_message(sid: str, data: Dict[str, Any]):
    """Send a message in a chat session."""
    try:
        session_data = await sio.get_session(sid)
        if not session_data:
            await sio.emit("error", {"message": "Not authenticated"}, room=sid)
            return
        
        user_id = session_data["user_id"]
        session_id = data.get("session_id")
        content = data.get("content")
        message_type = data.get("message_type", "text")
        
        if not all([session_id, content]):
            await sio.emit("error", {"message": "Session ID and content required"}, room=sid)
            return
        
        # Create message in database
        with get_db_context() as db:
            # Verify session access
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            ).first()
            
            if not session:
                await sio.emit("error", {"message": "Session not found or access denied"}, room=sid)
                return
            
            # Create user message
            message = Message(
                session_id=session_id,
                user_id=user_id,
                content=content,
                message_type=message_type,
                role="user"
            )
            
            db.add(message)
            db.commit()
            db.refresh(message)
            
            # Update session activity
            session.last_activity = datetime.utcnow()
            session.message_count += 1
            db.commit()
            
            # Emit message to session room
            await sio.emit("message_received", {
                "message": message.to_dict(),
                "timestamp": datetime.utcnow().isoformat()
            }, room=f"session_{session_id}")
            
            # Trigger AI response
            await trigger_ai_response.delay(session_id, message.id)
            
            logger.info(f"Message sent in session {session_id} by user {user_id}")
            
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        await sio.emit("error", {"message": "Failed to send message"}, room=sid)

@sio.event
async def typing_start(sid: str, data: Dict[str, Any]):
    """Handle typing start event."""
    try:
        session_data = await sio.get_session(sid)
        if not session_data:
            return
        
        user_id = session_data["user_id"]
        username = session_data["username"]
        session_id = data.get("session_id")
        
        if session_id:
            await sio.emit("user_typing", {
                "user_id": user_id,
                "username": username,
                "session_id": session_id,
                "typing": True,
                "timestamp": datetime.utcnow().isoformat()
            }, room=f"session_{session_id}", skip_sid=sid)
            
    except Exception as e:
        logger.error(f"Error handling typing start: {e}")

@sio.event
async def typing_stop(sid: str, data: Dict[str, Any]):
    """Handle typing stop event."""
    try:
        session_data = await sio.get_session(sid)
        if not session_data:
            return
        
        user_id = session_data["user_id"]
        username = session_data["username"]
        session_id = data.get("session_id")
        
        if session_id:
            await sio.emit("user_typing", {
                "user_id": user_id,
                "username": username,
                "session_id": session_id,
                "typing": False,
                "timestamp": datetime.utcnow().isoformat()
            }, room=f"session_{session_id}", skip_sid=sid)
            
    except Exception as e:
        logger.error(f"Error handling typing stop: {e}")

@sio.event
async def get_online_users(sid: str, data: Dict[str, Any]):
    """Get list of online users in a session."""
    try:
        session_data = await sio.get_session(sid)
        if not session_data:
            await sio.emit("error", {"message": "Not authenticated"}, room=sid)
            return
        
        session_id = data.get("session_id")
        if not session_id:
            await sio.emit("error", {"message": "Session ID required"}, room=sid)
            return
        
        # Get online users in session room
        room_name = f"session_{session_id}"
        online_sessions = await sio.get_session_data_in_room(room_name)
        
        online_users = []
        for session_sid, session_info in online_sessions.items():
            if session_info and session_sid != sid:
                online_users.append({
                    "user_id": session_info.get("user_id"),
                    "username": session_info.get("username"),
                    "connected_at": session_info.get("connected_at")
                })
        
        await sio.emit("online_users", {
            "users": online_users,
            "count": len(online_users),
            "timestamp": datetime.utcnow().isoformat()
        }, room=sid)
        
    except Exception as e:
        logger.error(f"Error getting online users: {e}")
        await sio.emit("error", {"message": "Failed to get online users"}, room=sid)

# AI Response handling
async def broadcast_ai_response(session_id: int, ai_response: AIResponse):
    """Broadcast AI response to session room."""
    try:
        await sio.emit("ai_response", {
            "response": ai_response.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }, room=f"session_{session_id}")
        
        logger.info(f"AI response broadcasted to session {session_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting AI response: {e}")

# Celery task for AI response
@ai_task
def trigger_ai_response(session_id: int, message_id: int):
    """Trigger AI response generation."""
    try:
        with get_db_context() as db:
            # Get session and message
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            message = db.query(Message).filter(Message.id == message_id).first()
            
            if not session or not message:
                logger.error(f"Session {session_id} or message {message_id} not found")
                return
            
            # Generate AI response (placeholder - integrate with actual AI service)
            ai_content = f"AI response to: {message.content[:100]}..."
            
            # Create AI response
            ai_response = AIResponse(
                session_id=session_id,
                message_id=message_id,
                content=ai_content,
                model_name=session.ai_model,
                temperature=0.7,
                tokens_used=len(ai_content.split()),
                processing_time=1.5,
                confidence_score=0.85
            )
            
            db.add(ai_response)
            db.commit()
            db.refresh(ai_response)
            
            # Broadcast response (this would be handled by the main app)
            logger.info(f"AI response generated for session {session_id}")
            
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")

# Utility functions
async def get_current_user_from_token(token: str) -> Optional[User]:
    """Get current user from JWT token."""
    try:
        from auth import verify_token
        from database import get_db_context
        
        token_data = verify_token(token, "access")
        
        with get_db_context() as db:
            user = db.query(User).filter(User.id == token_data.user_id).first()
            return user
            
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        return None

async def send_notification_to_user(user_id: int, notification: Dict[str, Any]):
    """Send notification to specific user."""
    try:
        await sio.emit("notification", {
            "notification": notification,
            "timestamp": datetime.utcnow().isoformat()
        }, room=f"user_{user_id}")
        
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")

# Export Socket.IO app
__all__ = ["sio", "broadcast_ai_response", "send_notification_to_user"]
