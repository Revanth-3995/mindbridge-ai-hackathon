"""
SQLAlchemy models for the Mind Bridge AI application.
Defines database schema for users, chat sessions, messages, and AI responses.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

class User(Base):
    """User model for authentication and profile management."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    
    # Profile information
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    preferences = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for API responses."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_premium": self.is_premium,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

class ChatSession(Base):
    """Chat session model for organizing conversations."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Session metadata
    session_type = Column(String(50), default="general")  # general, therapy, coaching, etc.
    mood = Column(String(50), nullable=True)  # happy, sad, anxious, etc.
    tags = Column(JSON, default=list)
    
    # AI Configuration
    ai_model = Column(String(100), default="gpt-3.5-turbo")
    ai_personality = Column(String(100), default="helpful")
    ai_settings = Column(JSON, default=dict)
    
    # Session statistics
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    session_duration = Column(Integer, default=0)  # in seconds
    
    # Status
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    ai_responses = relationship("AIResponse", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, title='{self.title}', user_id={self.user_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for API responses."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "session_type": self.session_type,
            "mood": self.mood,
            "tags": self.tags,
            "ai_model": self.ai_model,
            "ai_personality": self.ai_personality,
            "ai_settings": self.ai_settings,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "session_duration": self.session_duration,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }

class Message(Base):
    """Message model for storing chat messages."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Message content
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text, image, audio, file
    role = Column(String(20), nullable=False)  # user, assistant, system
    
    # Message metadata
    tokens_used = Column(Integer, default=0)
    processing_time = Column(Float, nullable=True)  # in seconds
    sentiment = Column(String(50), nullable=True)  # positive, negative, neutral
    emotions = Column(JSON, default=list)
    
    # Attachments
    attachments = Column(JSON, default=list)
    file_urls = Column(JSON, default=list)
    
    # Status
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")
    ai_response = relationship("AIResponse", back_populates="message", uselist=False)
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', session_id={self.session_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for API responses."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "content": self.content,
            "message_type": self.message_type,
            "role": self.role,
            "tokens_used": self.tokens_used,
            "processing_time": self.processing_time,
            "sentiment": self.sentiment,
            "emotions": self.emotions,
            "attachments": self.attachments,
            "file_urls": self.file_urls,
            "is_edited": self.is_edited,
            "is_deleted": self.is_deleted,
            "is_flagged": self.is_flagged,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class AIResponse(Base):
    """AI response model for storing AI-generated responses and metadata."""
    __tablename__ = "ai_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    
    # Response content
    content = Column(Text, nullable=False)
    response_type = Column(String(50), default="text")  # text, suggestion, action
    
    # AI Model information
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=True)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1000)
    
    # Response metadata
    tokens_used = Column(Integer, default=0)
    processing_time = Column(Float, nullable=True)  # in seconds
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Response analysis
    sentiment = Column(String(50), nullable=True)
    emotions = Column(JSON, default=list)
    topics = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    
    # Quality metrics
    is_helpful = Column(Boolean, nullable=True)
    user_rating = Column(Integer, nullable=True)  # 1-5 scale
    feedback = Column(Text, nullable=True)
    
    # Status
    is_generated = Column(Boolean, default=True)
    is_reviewed = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="ai_responses")
    message = relationship("Message", back_populates="ai_response")
    
    def __repr__(self):
        return f"<AIResponse(id={self.id}, model='{self.model_name}', session_id={self.session_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AI response to dictionary for API responses."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "content": self.content,
            "response_type": self.response_type,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tokens_used": self.tokens_used,
            "processing_time": self.processing_time,
            "confidence_score": self.confidence_score,
            "sentiment": self.sentiment,
            "emotions": self.emotions,
            "topics": self.topics,
            "suggestions": self.suggestions,
            "is_helpful": self.is_helpful,
            "user_rating": self.user_rating,
            "feedback": self.feedback,
            "is_generated": self.is_generated,
            "is_reviewed": self.is_reviewed,
            "is_approved": self.is_approved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
