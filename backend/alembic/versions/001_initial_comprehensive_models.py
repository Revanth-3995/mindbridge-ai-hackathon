"""Create comprehensive models for Mind Bridge AI

Revision ID: 001_initial
Revises: 
Create Date: 2025-09-10 23:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types with checkfirst=True to avoid duplicates
    mood_level = postgresql.ENUM('very_negative', 'negative', 'neutral', 'positive', 'very_positive', name='moodlevel')
    mood_level.create(op.get_bind(), checkfirst=True)
    
    emotion_type = postgresql.ENUM('happy', 'sad', 'angry', 'fear', 'surprise', 'disgust', 'neutral', name='emotiontype')
    emotion_type.create(op.get_bind(), checkfirst=True)
    
    data_source = postgresql.ENUM('webcam', 'voice', 'text', name='datasource')
    data_source.create(op.get_bind(), checkfirst=True)
    
    connection_status = postgresql.ENUM('pending', 'active', 'completed', 'blocked', name='connectionstatus')
    connection_status.create(op.get_bind(), checkfirst=True)
    
    risk_level = postgresql.ENUM('low', 'medium', 'high', 'critical', name='risklevel')
    risk_level.create(op.get_bind(), checkfirst=True)
    
    message_type = postgresql.ENUM('text', 'system', 'emergency', name='messagetype')
    message_type.create(op.get_bind(), checkfirst=True)

    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('baseline_mood', mood_level, nullable=False),
        sa.Column('emergency_contact_name', sa.String(length=255), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False),
        sa.Column('privacy_settings', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('length(email) > 0', name='email_not_empty'),
        sa.CheckConstraint('length(password_hash) > 0', name='password_hash_not_empty')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index('idx_user_email_active', 'users', ['email', 'is_active'], unique=False)
    op.create_index('idx_user_created_at', 'users', ['created_at'], unique=False)

    # Create emotion_records table
    op.create_table('emotion_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emotion', emotion_type, nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('source', data_source, nullable=False),
        sa.Column('raw_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='confidence_range')
    )
    op.create_index(op.f('ix_emotion_records_id'), 'emotion_records', ['id'], unique=False)
    op.create_index('idx_emotion_user_created', 'emotion_records', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_emotion_type_created', 'emotion_records', ['emotion', 'created_at'], unique=False)
    op.create_index('idx_emotion_source_created', 'emotion_records', ['source', 'created_at'], unique=False)

    # Create peer_connections table
    op.create_table('peer_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', connection_status, nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('requester_id != target_id', name='no_self_connection'),
        sa.CheckConstraint('similarity_score IS NULL OR (similarity_score >= 0.0 AND similarity_score <= 1.0)', name='similarity_score_range'),
        sa.UniqueConstraint('requester_id', 'target_id', name='unique_connection_pair')
    )
    op.create_index(op.f('ix_peer_connections_id'), 'peer_connections', ['id'], unique=False)
    op.create_index('idx_peer_requester_status', 'peer_connections', ['requester_id', 'status'], unique=False)
    op.create_index('idx_peer_target_status', 'peer_connections', ['target_id', 'status'], unique=False)
    op.create_index('idx_peer_created_at', 'peer_connections', ['created_at'], unique=False)

    # Create crisis_alerts table
    op.create_table('crisis_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('risk_level', risk_level, nullable=False),
        sa.Column('prediction_confidence', sa.Float(), nullable=False),
        sa.Column('triggers', sa.JSON(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('prediction_confidence >= 0.0 AND prediction_confidence <= 1.0', name='prediction_confidence_range'),
        sa.CheckConstraint('resolved_at IS NULL OR resolved_at >= created_at', name='resolution_after_creation')
    )
    op.create_index(op.f('ix_crisis_alerts_id'), 'crisis_alerts', ['id'], unique=False)
    op.create_index('idx_crisis_user_created', 'crisis_alerts', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_crisis_risk_level', 'crisis_alerts', ['risk_level'], unique=False)
    op.create_index('idx_crisis_unresolved', 'crisis_alerts', ['user_id', 'resolved_at'], unique=False)

    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('receiver_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', message_type, nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['receiver_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('sender_id != receiver_id', name='no_self_message'),
        sa.CheckConstraint('length(content) > 0', name='content_not_empty'),
        sa.CheckConstraint('read_at IS NULL OR read_at >= created_at', name='read_after_creation')
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)
    op.create_index('idx_message_sender_created', 'chat_messages', ['sender_id', 'created_at'], unique=False)
    op.create_index('idx_message_receiver_created', 'chat_messages', ['receiver_id', 'created_at'], unique=False)
    op.create_index('idx_message_unread', 'chat_messages', ['receiver_id', 'read_at'], unique=False)
    op.create_index('idx_message_type_created', 'chat_messages', ['message_type', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('chat_messages')
    op.drop_table('crisis_alerts')
    op.drop_table('peer_connections')
    op.drop_table('emotion_records')
    op.drop_table('users')
    
    # Drop enum types
    op.execute('DROP TYPE messagetype')
    op.execute('DROP TYPE risklevel')
    op.execute('DROP TYPE connectionstatus')
    op.execute('DROP TYPE datasource')
    op.execute('DROP TYPE emotiontype')
    op.execute('DROP TYPE moodlevel')
