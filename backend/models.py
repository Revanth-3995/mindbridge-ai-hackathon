"""
SQLAlchemy models for the Mind Bridge AI application.
Defines comprehensive database schema for mental health and wellness platform.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, ForeignKey, 
    JSON, Float, Enum as SQLEnum, Index, CheckConstraint, UniqueConstraint,
    TypeDecorator, CHAR
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# Custom GUID type for cross-database compatibility
class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            try:
                return str(uuid.UUID(value))
            except (ValueError, TypeError):
                return str(value)
        return str(value) if dialect.name != 'postgresql' else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == 'postgresql':
            return value  # Already a UUID object
        else:
            return uuid.UUID(value)

# Enums
class MoodLevel(str, Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"

class EmotionType(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"

class DataSource(str, Enum):
    WEBCAM = "webcam"
    VOICE = "voice"
    TEXT = "text"

class ConnectionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MessageType(str, Enum):
    TEXT = "text"
    SYSTEM = "system"
    EMERGENCY = "emergency"

class AIResponse(Base):
    """AI response model linked to chat messages."""
    __tablename__ = "ai_responses"

    # Primary key as UUID
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to ChatMessage (required)
    message_id = Column(GUID(), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)

    # Response content
    content = Column(Text, nullable=False)
    response_type = Column(String(50))
    
    # AI model information
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50))
    temperature = Column(Float)
    max_tokens = Column(Integer)
    tokens_used = Column(Integer)
    processing_time = Column(Float)
    confidence_score = Column(Float)

    # Analysis results
    sentiment = Column(String(50))
    emotions = Column(JSON)
    topics = Column(JSON)
    suggestions = Column(JSON)

    # User feedback
    is_helpful = Column(Boolean, default=False)
    user_rating = Column(Integer)
    feedback = Column(Text)

    # Status flags
    is_generated = Column(Boolean, default=True)
    is_reviewed = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    message = relationship("ChatMessage", back_populates="ai_responses")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)', name='confidence_score_range'),
        CheckConstraint('user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 5)', name='user_rating_range'),
        CheckConstraint('length(content) > 0', name='content_not_empty'),
        Index('idx_ai_response_message_created', 'message_id', 'created_at'),
        Index('idx_ai_response_model_created', 'model_name', 'created_at'),
        Index('idx_ai_response_helpful', 'is_helpful'),
    )
    
    def __repr__(self):
        return f"<AIResponse(id={self.id}, message_id={self.message_id}, model='{self.model_name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AI response to dictionary for API responses."""
        return {
            "id": str(self.id),
            "message_id": str(self.message_id),
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


class User(Base):
    """User model for authentication and profile management."""
    __tablename__ = "users"
    
    # Primary key as UUID
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    
    # Authentication fields
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hashed password
    full_name = Column(String(255), nullable=True)
    
    # Profile information
    baseline_mood = Column(SQLEnum(MoodLevel), default=MoodLevel.NEUTRAL, nullable=False)
    
    # Emergency contact information
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    # Status flags
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    
    # Privacy and settings
    privacy_settings = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    emotion_records = relationship("EmotionRecord", back_populates="user", cascade="all, delete-orphan")
    crisis_alerts = relationship("CrisisAlert", back_populates="user", cascade="all, delete-orphan")
    
    # Peer connections (as requester)
    requested_connections = relationship(
        "PeerConnection", 
        foreign_keys="PeerConnection.requester_id",
        back_populates="requester",
        cascade="all, delete-orphan"
    )
    
    # Peer connections (as target)
    received_connections = relationship(
        "PeerConnection", 
        foreign_keys="PeerConnection.target_id",
        back_populates="target",
        cascade="all, delete-orphan"
    )
    
    # Messages sent
    sent_messages = relationship(
        "ChatMessage", 
        foreign_keys="ChatMessage.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    
    # Messages received
    received_messages = relationship(
        "ChatMessage", 
        foreign_keys="ChatMessage.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint('length(email) > 0', name='email_not_empty'),
        CheckConstraint('length(password_hash) > 0', name='password_hash_not_empty'),
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', mood='{self.baseline_mood}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for API responses."""
        return {
            "id": str(self.id),
            "email": self.email,
            "baseline_mood": self.baseline_mood.value if self.baseline_mood else None,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "privacy_settings": self.privacy_settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class EmotionRecord(Base):
    """Emotion detection record model."""
    __tablename__ = "emotion_records"
    
    # Primary key as UUID
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to User
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Emotion detection data
    emotion = Column(SQLEnum(EmotionType), nullable=False)
    confidence = Column(Float, nullable=False)
    source = Column(SQLEnum(DataSource), nullable=False)
    
    # Raw ML output data
    raw_data = Column(JSON, default=dict, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="emotion_records")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='confidence_range'),
        Index('idx_emotion_user_created', 'user_id', 'created_at'),
        Index('idx_emotion_type_created', 'emotion', 'created_at'),
        Index('idx_emotion_source_created', 'source', 'created_at'),
    )
    
    def __repr__(self):
        return f"<EmotionRecord(id={self.id}, user_id={self.user_id}, emotion='{self.emotion}', confidence={self.confidence})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert emotion record to dictionary for API responses."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "emotion": self.emotion.value if self.emotion else None,
            "confidence": self.confidence,
            "source": self.source.value if self.source else None,
            "raw_data": self.raw_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class PeerConnection(Base):
    """Peer-to-peer connection model for matching users."""
    __tablename__ = "peer_connections"
    
    # Primary key as UUID
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys to User
    requester_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Connection data
    status = Column(SQLEnum(ConnectionStatus), default=ConnectionStatus.PENDING, nullable=False)
    similarity_score = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    requester = relationship("User", foreign_keys=[requester_id], back_populates="requested_connections")
    target = relationship("User", foreign_keys=[target_id], back_populates="received_connections")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('requester_id != target_id', name='no_self_connection'),
        CheckConstraint('similarity_score IS NULL OR (similarity_score >= 0.0 AND similarity_score <= 1.0)', name='similarity_score_range'),
        UniqueConstraint('requester_id', 'target_id', name='unique_connection_pair'),
        Index('idx_peer_requester_status', 'requester_id', 'status'),
        Index('idx_peer_target_status', 'target_id', 'status'),
        Index('idx_peer_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<PeerConnection(id={self.id}, requester={self.requester_id}, target={self.target_id}, status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert peer connection to dictionary for API responses."""
        return {
            "id": str(self.id),
            "requester_id": str(self.requester_id),
            "target_id": str(self.target_id),
            "status": self.status.value if self.status else None,
            "similarity_score": self.similarity_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class CrisisAlert(Base):
    """Crisis detection and alert model."""
    __tablename__ = "crisis_alerts"
    
    # Primary key as UUID
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to User
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Crisis assessment data
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    prediction_confidence = Column(Float, nullable=False)
    triggers = Column(JSON, default=list, nullable=False)  # Array of trigger factors
    
    # Resolution tracking
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="crisis_alerts")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('prediction_confidence >= 0.0 AND prediction_confidence <= 1.0', name='prediction_confidence_range'),
        CheckConstraint('resolved_at IS NULL OR resolved_at >= created_at', name='resolution_after_creation'),
        Index('idx_crisis_user_created', 'user_id', 'created_at'),
        Index('idx_crisis_risk_level', 'risk_level'),
        Index('idx_crisis_unresolved', 'user_id', 'resolved_at'),
    )
    
    def __repr__(self):
        return f"<CrisisAlert(id={self.id}, user_id={self.user_id}, risk_level='{self.risk_level}', confidence={self.prediction_confidence})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert crisis alert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "risk_level": self.risk_level.value if self.risk_level else None,
            "prediction_confidence": self.prediction_confidence,
            "triggers": self.triggers,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class ChatMessage(Base):
    """Encrypted chat message model."""
    __tablename__ = "chat_messages"
    
    # Primary key as UUID
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys to User
    sender_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Message content (encrypted)
    content = Column(Text, nullable=False)  # Encrypted text content
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT, nullable=False)
    
    # Read status
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")
    ai_responses = relationship("AIResponse", back_populates="message", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('sender_id != receiver_id', name='no_self_message'),
        CheckConstraint('length(content) > 0', name='content_not_empty'),
        CheckConstraint('read_at IS NULL OR read_at >= created_at', name='read_after_creation'),
        Index('idx_message_sender_created', 'sender_id', 'created_at'),
        Index('idx_message_receiver_created', 'receiver_id', 'created_at'),
        Index('idx_message_unread', 'receiver_id', 'read_at'),
        Index('idx_message_type_created', 'message_type', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, sender={self.sender_id}, receiver={self.receiver_id}, type='{self.message_type}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chat message to dictionary for API responses."""
        return {
            "id": str(self.id),
            "sender_id": str(self.sender_id),
            "receiver_id": str(self.receiver_id),
            "content": self.content,  # Note: This should be decrypted before sending
            "message_type": self.message_type.value if self.message_type else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

# Additional utility functions
def get_user_by_email(session, email: str) -> Optional[User]:
    """Get user by email address."""
    return session.query(User).filter(User.email == email).first()

def get_active_crisis_alerts(session, user_id: uuid.UUID) -> List[CrisisAlert]:
    """Get unresolved crisis alerts for a user."""
    return session.query(CrisisAlert).filter(
        CrisisAlert.user_id == user_id,
        CrisisAlert.resolved_at.is_(None)
    ).order_by(CrisisAlert.created_at.desc()).all()

def get_unread_messages(session, user_id: uuid.UUID) -> List[ChatMessage]:
    """Get unread messages for a user."""
    return session.query(ChatMessage).filter(
        ChatMessage.receiver_id == user_id,
        ChatMessage.read_at.is_(None)
    ).order_by(ChatMessage.created_at.desc()).all()

def get_pending_connections(session, user_id: uuid.UUID) -> List[PeerConnection]:
    """Get pending peer connections for a user."""
    return session.query(PeerConnection).filter(
        (PeerConnection.requester_id == user_id) | (PeerConnection.target_id == user_id),
        PeerConnection.status == ConnectionStatus.PENDING
    ).order_by(PeerConnection.created_at.desc()).all()