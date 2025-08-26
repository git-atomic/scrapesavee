"""
ItemSources model - Many-to-many relationship between items and sources
Tracks which sources discovered which items
"""
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from uuid import UUID

from .base import Base


class ItemSource(Base):
    __tablename__ = "item_sources"

    # Composite primary key
    item_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("items.id", ondelete="CASCADE"), 
        primary_key=True,
        doc="Item that was discovered"
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), 
        primary_key=True,
        doc="Source that discovered this item"
    )
    
    # Discovery metadata
    first_seen_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        doc="When this item was first seen from this source"
    )

    # Relationships
    item = relationship("Item", back_populates="sources")
    source = relationship("Source", back_populates="items")

    def __repr__(self) -> str:
        return f"<ItemSource(item_id='{self.item_id}', source_id={self.source_id}, first_seen_at={self.first_seen_at})>"


# Add reverse relationships
from .items import Item
from .sources import Source

Item.sources = relationship("ItemSource", back_populates="item", cascade="all, delete-orphan")
Source.items = relationship("ItemSource", back_populates="source", cascade="all, delete-orphan")



