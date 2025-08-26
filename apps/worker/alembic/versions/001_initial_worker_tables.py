"""Initial worker tables

Revision ID: 001_initial_worker_tables
Revises: 
Create Date: 2025-08-25 02:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_worker_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create worker tables in public schema."""
    
    # Create sources table
    op.create_table('sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'active'")),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_sources')
    )
    
    # Create items table
    op.create_table('items',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('page_url', sa.Text(), nullable=False),
        sa.Column('media_type', sa.String(length=50), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('video_url', sa.Text(), nullable=True),
        sa.Column('video_poster_url', sa.Text(), nullable=True),
        sa.Column('source_api_url', sa.Text(), nullable=True),
        sa.Column('source_original_url', sa.Text(), nullable=True),
        sa.Column('og_title', sa.Text(), nullable=True),
        sa.Column('og_description', sa.Text(), nullable=True),
        sa.Column('og_image_url', sa.Text(), nullable=True),
        sa.Column('og_url', sa.Text(), nullable=True),
        sa.Column('sidebar', sa.JSON(), nullable=True),
        sa.Column('media_object_keys', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_items')
    )
    
    # Create runs table
    op.create_table('runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'running'")),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('counters', sa.JSON(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], name='fk_runs_source_id_sources', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_runs')
    )
    
    # Create item_sources junction table
    op.create_table('item_sources',
        sa.Column('item_id', sa.String(length=255), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], name='fk_item_sources_item_id_items', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], name='fk_item_sources_source_id_sources', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('item_id', 'source_id', name='pk_item_sources')
    )
    
    # Create indexes for performance
    op.create_index('ix_sources_enabled', 'sources', ['enabled'])
    op.create_index('ix_sources_status', 'sources', ['status'])
    op.create_index('ix_items_media_type', 'items', ['media_type'])
    op.create_index('ix_items_created_at', 'items', ['created_at'])
    op.create_index('ix_runs_source_id', 'runs', ['source_id'])
    op.create_index('ix_runs_status', 'runs', ['status'])
    op.create_index('ix_runs_started_at', 'runs', ['started_at'])


def downgrade() -> None:
    """Drop worker tables."""
    op.drop_table('item_sources')
    op.drop_table('runs')
    op.drop_table('items')
    op.drop_table('sources')
