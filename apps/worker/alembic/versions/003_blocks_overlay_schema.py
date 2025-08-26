"""Add blocks overlay schema for ingestion-CMS separation

Revision ID: 003_blocks_overlay_schema
Revises: 002_production_indexes
Create Date: 2025-08-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_blocks_overlay_schema'
down_revision: Union[str, None] = '002_production_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create overlay schema for blocks and CMS overrides"""
    
    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS cms")
    
    # Create core.blocks table (ingestion truth)
    op.create_table('blocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=False),  # savee item ID
        sa.Column('title_raw', sa.Text(), nullable=True),
        sa.Column('description_raw', sa.Text(), nullable=True),
        sa.Column('tags_raw', postgresql.ARRAY(sa.String(length=100)), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column('media_key', sa.String(length=500), nullable=False),  # R2 object key
        sa.Column('media_type', sa.String(length=20), nullable=False),  # 'image' or 'video'
        sa.Column('video_poster_key', sa.String(length=500), nullable=True),  # R2 key for video poster
        sa.Column('url', sa.Text(), nullable=False),  # page URL
        sa.Column('source_api_url', sa.Text(), nullable=True),
        sa.Column('source_original_url', sa.Text(), nullable=True),
        sa.Column('sidebar_info', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('og_title', sa.Text(), nullable=True),
        sa.Column('og_description', sa.Text(), nullable=True),
        sa.Column('og_image_url', sa.Text(), nullable=True),
        sa.Column('og_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_core_blocks'),
        sa.UniqueConstraint('source_id', 'external_id', name='uq_core_blocks_source_external'),
        schema='core'
    )
    
    # Add foreign key to sources table
    op.create_foreign_key('fk_core_blocks_source_id', 'blocks', 'sources', ['source_id'], ['id'], 
                         source_schema='core', referent_schema='public', ondelete='CASCADE')
    
    # Create CMS blocks overrides table (editorial layer)
    op.create_table('blocks_overrides',
        sa.Column('block_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title_override', sa.Text(), nullable=True),
        sa.Column('description_override', sa.Text(), nullable=True),
        sa.Column('tags_override', postgresql.ARRAY(sa.String(length=100)), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column('locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('block_id', name='pk_cms_blocks_overrides'),
        sa.CheckConstraint("status IN ('draft', 'published', 'hidden', 'archived')", name='ck_cms_blocks_status'),
        schema='cms'
    )
    
    # Add foreign key to core.blocks
    op.create_foreign_key('fk_cms_blocks_overrides_block_id', 'blocks_overrides', 'blocks', 
                         ['block_id'], ['id'], source_schema='cms', referent_schema='core', ondelete='CASCADE')
    
    # Create the merged view for reading
    op.execute("""
        CREATE OR REPLACE VIEW cms.v_blocks AS
        SELECT
            b.id,
            b.source_id,
            b.external_id,
            COALESCE(o.title_override, b.title_raw) as title,
            COALESCE(o.description_override, b.description_raw) as description,
            COALESCE(o.tags_override, b.tags_raw) as tags,
            b.media_key,
            b.media_type,
            b.video_poster_key,
            b.url,
            b.source_api_url,
            b.source_original_url,
            b.sidebar_info,
            b.og_title,
            b.og_description,
            b.og_image_url,
            b.og_url,
            COALESCE(o.status, 'draft') as status,
            COALESCE(o.locked, false) as locked,
            COALESCE(o.priority, 0) as priority,
            o.notes,
            b.created_at,
            GREATEST(b.updated_at, COALESCE(o.updated_at, b.updated_at)) as updated_at,
            -- Include override info for admin
            CASE WHEN o.block_id IS NOT NULL THEN true ELSE false END as has_overrides,
            o.updated_at as override_updated_at
        FROM core.blocks b
        LEFT JOIN cms.blocks_overrides o ON o.block_id = b.id
    """)
    
    # Create production indexes for core.blocks
    op.create_index('idx_core_blocks_source_id', 'blocks', ['source_id'], schema='core')
    op.create_index('idx_core_blocks_external_id', 'blocks', ['external_id'], schema='core')
    op.create_index('idx_core_blocks_media_type', 'blocks', ['media_type'], schema='core')
    op.create_index('idx_core_blocks_created_at', 'blocks', ['created_at'], schema='core')
    op.create_index('idx_core_blocks_updated_at', 'blocks', ['updated_at'], schema='core')
    op.create_index('idx_core_blocks_created_desc', 'blocks', [sa.text('created_at DESC')], schema='core')
    
    # GIN indexes for array and JSON columns
    op.create_index('idx_core_blocks_tags_gin', 'blocks', ['tags_raw'], 
                   postgresql_using='gin', schema='core')
    # JSONB GIN index - must be created after table exists
    op.execute("CREATE INDEX idx_core_blocks_sidebar_gin ON core.blocks USING gin (sidebar_info)")
    
    # Composite indexes for common queries
    op.create_index('idx_core_blocks_source_created', 'blocks', ['source_id', 'created_at'], schema='core')
    op.create_index('idx_core_blocks_media_created', 'blocks', ['media_type', 'created_at'], schema='core')
    
    # CMS overrides indexes
    op.create_index('idx_cms_blocks_overrides_status', 'blocks_overrides', ['status'], schema='cms')
    op.create_index('idx_cms_blocks_overrides_priority', 'blocks_overrides', ['priority'], schema='cms')
    op.create_index('idx_cms_blocks_overrides_updated', 'blocks_overrides', ['updated_at'], schema='cms')
    
    # Create updated_at trigger function (if not exists from migration 002)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Add updated_at triggers for new tables
    op.execute("""
        CREATE TRIGGER update_core_blocks_updated_at 
        BEFORE UPDATE ON core.blocks 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_cms_blocks_overrides_updated_at 
        BEFORE UPDATE ON cms.blocks_overrides 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop overlay schema"""
    op.execute("DROP VIEW IF EXISTS cms.v_blocks")
    op.drop_table('blocks_overrides', schema='cms')
    op.drop_table('blocks', schema='core')
    op.execute("DROP SCHEMA IF EXISTS cms CASCADE")
    op.execute("DROP SCHEMA IF EXISTS core CASCADE")
