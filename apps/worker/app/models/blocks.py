"""
Blocks model for core ingestion data
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import String, Text, DateTime, Boolean, Integer, ARRAY, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from .base import Base


class Block(Base):
    """Core blocks table - raw ingestion data"""
    __tablename__ = "blocks"
    __table_args__ = {'schema': 'core'}
    
    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text('gen_random_uuid()')
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        nullable=False,
        index=True
    )
    external_id: Mapped[str] = mapped_column(
        String(100), 
        nullable=False,
        index=True
    )
    
    # Raw content from scraper
    title_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags_raw: Mapped[List[str]] = mapped_column(
        ARRAY(String(100)), 
        nullable=False,
        server_default=text("'{}'::text[]")
    )
    
    # Media information
    media_key: Mapped[str] = mapped_column(String(500), nullable=False)  # R2 object key
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'image' or 'video'
    video_poster_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # URLs
    url: Mapped[str] = mapped_column(Text, nullable=False)  # page URL
    source_api_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_original_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    sidebar_info: Mapped[dict] = mapped_column(
        JSONB, 
        nullable=False, 
        server_default=text("'{}'::jsonb")
    )
    
    # Open Graph data
    og_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    og_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    og_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    og_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp()
    )
    
    # Unique constraint on source + external_id
    __table_args__ = (
        {'schema': 'core'},
    )

    def __repr__(self) -> str:
        return f"<Block(id={self.id}, external_id='{self.external_id}', media_type='{self.media_type}')>"


class BlockOverride(Base):
    """CMS overrides for blocks - editorial layer"""
    __tablename__ = "blocks_overrides"
    __table_args__ = {'schema': 'cms'}
    
    block_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True
    )
    
    # Editorial overrides
    title_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_override: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags_override: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(100)), 
        nullable=True
    )
    
    # Editorial metadata
    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        server_default=text("'draft'"),
        index=True
    )
    locked: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        server_default=text('false')
    )
    priority: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        server_default=text('0'),
        index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        index=True
    )

    def __repr__(self) -> str:
        return f"<BlockOverride(block_id={self.block_id}, status='{self.status}')>"
