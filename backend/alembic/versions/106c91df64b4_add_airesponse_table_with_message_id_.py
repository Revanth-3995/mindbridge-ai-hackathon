"""Add AIResponse table with message_id foreign key

Revision ID: 106c91df64b4
Revises: 001_initial
Create Date: 2025-09-11 00:54:53.987676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '106c91df64b4'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ai_responses table
    op.create_table('ai_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('response_type', sa.String(length=50), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('sentiment', sa.String(length=50), nullable=True),
        sa.Column('emotions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('topics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('suggestions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_helpful', sa.Boolean(), nullable=True),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('is_generated', sa.Boolean(), nullable=True),
        sa.Column('is_reviewed', sa.Boolean(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('confidence_score IS NULL OR (confidence_score >= 0.0 AND confidence_score <= 1.0)', name='confidence_score_range'),
        sa.CheckConstraint('user_rating IS NULL OR (user_rating >= 1 AND user_rating <= 5)', name='user_rating_range'),
        sa.CheckConstraint('length(content) > 0', name='content_not_empty')
    )
    
    # Create indexes
    op.create_index('idx_ai_response_message_created', 'ai_responses', ['message_id', 'created_at'], unique=False)
    op.create_index('idx_ai_response_model_created', 'ai_responses', ['model_name', 'created_at'], unique=False)
    op.create_index('idx_ai_response_helpful', 'ai_responses', ['is_helpful'], unique=False)
    op.create_index(op.f('ix_ai_responses_id'), 'ai_responses', ['id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_ai_responses_id'), table_name='ai_responses')
    op.drop_index('idx_ai_response_helpful', table_name='ai_responses')
    op.drop_index('idx_ai_response_model_created', table_name='ai_responses')
    op.drop_index('idx_ai_response_message_created', table_name='ai_responses')
    
    # Drop table
    op.drop_table('ai_responses')
