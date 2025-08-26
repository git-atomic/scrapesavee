"""
Runs model - Defines scraping run executions
"""
from sqlalchemy import Boolean, DateTime, String, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from uuid import UUID
from typing import Dict, Any, Optional
import uuid

from .base import Base


class Run(Base):
    __tablename__ = "runs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4,
        doc="Unique identifier for this run"
    )
    
    # Foreign key to source
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), 
        nullable=False,
        doc="Source that this run belongs to"
    )
    
    # Run metadata
    kind: Mapped[str] = mapped_column(
        String(50), 
        nullable=True,
        doc="Type of run: 'tail', 'backfill', 'manual'"
    )
    status: Mapped[str] = mapped_column(
        String(50), 
        default="running", 
        nullable=False,
        doc="Run status: 'running', 'success', 'error', 'cancelled'"
    )
    
    # Execution tracking
    started_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        doc="When this run started"
    )
    finished_at: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        doc="When this run completed (null if still running)"
    )
    
    # Results and metrics
    counters: Mapped[Dict[str, Any]] = mapped_column(
        JSON, 
        nullable=True,
        doc="Run metrics: items_discovered, items_processed, errors, etc."
    )
    error: Mapped[str] = mapped_column(
        Text, 
        nullable=True,
        doc="Error message if run failed"
    )

    # Relationship to source
    source = relationship("Source", back_populates="runs")

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, source_id={self.source_id}, status='{self.status}', kind='{self.kind}')>"


# Add the reverse relationship to Source
from .sources import Source
Source.runs = relationship("Run", back_populates="source", cascade="all, delete-orphan")