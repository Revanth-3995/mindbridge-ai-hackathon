"""Add GUID type for cross-database UUID compatibility

Revision ID: d4eaa8b50127
Revises: 106c91df64b4
Create Date: 2025-09-11 01:40:46.080879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4eaa8b50127'
down_revision: Union[str, None] = '106c91df64b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    GUID type implementation for cross-database UUID compatibility.
    
    This migration documents the implementation of a custom GUID type that:
    - Uses PostgreSQL's native UUID type when available
    - Falls back to CHAR(36) for SQLite and other databases
    - Ensures UUID values are properly converted between string and UUID objects
    
    The GUID type is defined in models.py and automatically handles:
    - Database-specific type mapping
    - UUID string conversion for storage
    - UUID object conversion for retrieval
    
    No database schema changes are needed as the GUID type handles
    the compatibility automatically at the SQLAlchemy level.
    """
    pass


def downgrade() -> None:
    """
    No downgrade needed for GUID type implementation.
    
    The GUID type is a SQLAlchemy TypeDecorator that provides
    cross-database compatibility without requiring schema changes.
    """
    pass
