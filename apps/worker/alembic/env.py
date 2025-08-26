"""Alembic environment configuration for ScrapeSavee worker."""

import os
import sys
from logging.config import fileConfig
from dotenv import load_dotenv

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from alembic import context

# Load environment variables
load_dotenv()

# Add the parent directory to sys.path to import our models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our models for autogenerate support
from app.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override the sqlalchemy.url with the environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    # Convert to sync psycopg (psycopg[binary]) for Alembic
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    elif DATABASE_URL.startswith("postgresql+asyncpg://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    # Ensure it's using the synchronous psycopg driver for Alembic
    if "postgresql://" in DATABASE_URL and "+psycopg" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    # Fix SSL parameter for psycopg
    if "ssl=require" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("ssl=require", "sslmode=require")
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with established connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy import engine_from_config
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()