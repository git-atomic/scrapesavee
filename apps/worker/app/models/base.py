"""Base SQLAlchemy model."""

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

# Use explicit naming convention for constraints
# This helps with Alembic migrations and database consistency
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s", 
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
