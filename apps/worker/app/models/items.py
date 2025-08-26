"""
Items model - Defines scraped items from Savee.com
"""
from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Dict, Any

from .base import Base


class Item(Base):
    __tablename__ = "items"

    # Primary key - using Savee ID as natural primary key
    id: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True,
        doc="Savee item ID (natural key from savee.com)"
    )
    
    # Core item information
    page_url: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        doc="Original Savee page URL for this item"
    )
    media_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=True,
        doc="Type of media: 'image', 'video', 'gif', etc."
    )
    
    # Media URLs (original sources)
    image_url: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Original image URL from Savee"
    )
    video_url: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Original video URL from Savee"
    )
    video_poster_url: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Video poster/thumbnail URL"
    )
    
    # Source and API data
    source_api_url: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="API endpoint URL for this item"
    )
    source_original_url: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Original source URL before Savee"
    )
    
    # Open Graph metadata
    og_title: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Open Graph title"
    )
    og_description: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Open Graph description"
    )
    og_image_url: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Open Graph image URL"
    )
    og_url: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Open Graph canonical URL"
    )
    
    # Structured data
    sidebar: Mapped[Dict[str, Any]] = mapped_column(
        JSON, 
        nullable=True,
        doc="Sidebar metadata extracted from Savee page (tags, stats, etc.)"
    )
    media_object_keys: Mapped[Dict[str, Any]] = mapped_column(
        JSON, 
        nullable=True,
        doc="R2 object keys for downloaded media files"
    )
    
    # Timestamps
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        doc="When this item was first discovered"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(), 
        onupdate=func.now(),
        doc="When this item was last updated"
    )

    def __repr__(self) -> str:
        return f"<Item(id='{self.id}', media_type='{self.media_type}', created_at={self.created_at})>"