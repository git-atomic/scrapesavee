"""
Sources model - Defines scraping sources (Savee profiles, collections, etc.)
"""
from sqlalchemy import Boolean, DateTime, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from uuid import UUID
import uuid

from .base import Base


class Source(Base):
    __tablename__ = "sources"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        doc="Unique identifier for the source"
    )
    
    # Core source information
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        doc="Human-readable name for the source"
    )
    type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        doc="Source type: 'home', 'pop', 'user', 'collection'"
    )
    url: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        doc="Base URL for scraping this source"
    )
    
    # Status and configuration
    enabled: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False,
        doc="Whether this source is active for scraping"
    )
    status: Mapped[str] = mapped_column(
        String(50), 
        default="active", 
        nullable=False,
        doc="Current status: 'active', 'paused', 'error'"
    )
    
    # Scheduling
    next_run_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When this source should next be scraped"
    )
    
    # Metadata
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        doc="When this source was created"
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(), 
        onupdate=func.now(),
        doc="When this source was last updated"
    )

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name='{self.name}', type='{self.type}', enabled={self.enabled})>"