"""Add production indexes and constraints

Revision ID: 002_production_indexes
Revises: 001_initial_worker_tables
Create Date: 2024-12-30 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_production_indexes'
down_revision: Union[str, None] = '001_initial_worker_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Production indexes for performance
    
    # Sources indexes
    op.create_index('idx_sources_is_active', 'sources', ['is_active'])
    op.create_index('idx_sources_last_run_at', 'sources', ['last_run_at'])
    op.create_index('idx_sources_name', 'sources', ['name'])
    
    # Items indexes
    op.create_index('idx_items_created_at', 'items', ['created_at'])
    op.create_index('idx_items_updated_at', 'items', ['updated_at'])
    op.create_index('idx_items_media_type', 'items', ['media_type'])
    op.create_index('idx_items_created_at_desc', 'items', [sa.text('created_at DESC')])
    
    # Composite index for filtering items by media type and date
    op.create_index('idx_items_media_type_created_at', 'items', ['media_type', 'created_at'])
    
    # GIN index for JSON columns (PostgreSQL specific)
    op.create_index('idx_items_sidebar_gin', 'items', ['sidebar'], postgresql_using='gin')
    op.create_index('idx_items_media_keys_gin', 'items', ['media_object_keys'], postgresql_using='gin')
    
    # Runs indexes
    op.create_index('idx_runs_source_id', 'runs', ['source_id'])
    op.create_index('idx_runs_status', 'runs', ['status'])
    op.create_index('idx_runs_run_type', 'runs', ['run_type'])
    op.create_index('idx_runs_started_at', 'runs', ['started_at'])
    op.create_index('idx_runs_completed_at', 'runs', ['completed_at'])
    op.create_index('idx_runs_started_at_desc', 'runs', [sa.text('started_at DESC')])
    
    # Composite indexes for common queries
    op.create_index('idx_runs_source_status', 'runs', ['source_id', 'status'])
    op.create_index('idx_runs_status_started_at', 'runs', ['status', 'started_at'])
    
    # Item sources indexes
    op.create_index('idx_item_sources_source_id', 'item_sources', ['source_id'])
    op.create_index('idx_item_sources_discovered_at', 'item_sources', ['discovered_at'])
    op.create_index('idx_item_sources_source_discovered', 'item_sources', ['source_id', 'discovered_at'])
    
    # Add triggers for updated_at timestamps
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_sources_updated_at 
        BEFORE UPDATE ON sources 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_items_updated_at 
        BEFORE UPDATE ON items 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Add constraints for data integrity
    op.create_check_constraint(
        'ck_sources_base_url_not_empty',
        'sources',
        sa.text("base_url <> ''")
    )
    
    op.create_check_constraint(
        'ck_items_page_url_not_empty',
        'items',
        sa.text("page_url <> ''")
    )
    
    op.create_check_constraint(
        'ck_runs_status_valid',
        'runs',
        sa.text("status IN ('pending', 'running', 'completed', 'failed', 'cancelled')")
    )
    
    op.create_check_constraint(
        'ck_runs_run_type_valid',
        'runs',
        sa.text("run_type IN ('tail', 'backfill', 'manual')")
    )
    
    op.create_check_constraint(
        'ck_runs_completed_after_started',
        'runs',
        sa.text("completed_at IS NULL OR completed_at >= started_at")
    )
    
    op.create_check_constraint(
        'ck_runs_items_counts_non_negative',
        'runs',
        sa.text("""
            (items_discovered IS NULL OR items_discovered >= 0) AND
            (items_processed IS NULL OR items_processed >= 0) AND 
            (items_failed IS NULL OR items_failed >= 0)
        """)
    )


def downgrade() -> None:
    # Drop constraints
    op.drop_constraint('ck_runs_items_counts_non_negative', 'runs')
    op.drop_constraint('ck_runs_completed_after_started', 'runs')
    op.drop_constraint('ck_runs_run_type_valid', 'runs')
    op.drop_constraint('ck_runs_status_valid', 'runs')
    op.drop_constraint('ck_items_page_url_not_empty', 'items')
    op.drop_constraint('ck_sources_base_url_not_empty', 'sources')
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_items_updated_at ON items;")
    op.execute("DROP TRIGGER IF EXISTS update_sources_updated_at ON sources;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop indexes
    op.drop_index('idx_item_sources_source_discovered', table_name='item_sources')
    op.drop_index('idx_item_sources_discovered_at', table_name='item_sources')
    op.drop_index('idx_item_sources_source_id', table_name='item_sources')
    
    op.drop_index('idx_runs_status_started_at', table_name='runs')
    op.drop_index('idx_runs_source_status', table_name='runs')
    op.drop_index('idx_runs_started_at_desc', table_name='runs')
    op.drop_index('idx_runs_completed_at', table_name='runs')
    op.drop_index('idx_runs_started_at', table_name='runs')
    op.drop_index('idx_runs_run_type', table_name='runs')
    op.drop_index('idx_runs_status', table_name='runs')
    op.drop_index('idx_runs_source_id', table_name='runs')
    
    op.drop_index('idx_items_media_keys_gin', table_name='items')
    op.drop_index('idx_items_sidebar_gin', table_name='items')
    op.drop_index('idx_items_media_type_created_at', table_name='items')
    op.drop_index('idx_items_created_at_desc', table_name='items')
    op.drop_index('idx_items_media_type', table_name='items')
    op.drop_index('idx_items_updated_at', table_name='items')
    op.drop_index('idx_items_created_at', table_name='items')
    
    op.drop_index('idx_sources_name', table_name='sources')
    op.drop_index('idx_sources_last_run_at', table_name='sources')
    op.drop_index('idx_sources_is_active', table_name='sources')
