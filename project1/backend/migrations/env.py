"""
migrations/env.py — Alembic Environment Configuration
=======================================================
This file is loaded by Alembic every time a migration command runs.
It bridges the gap between Alembic (which is synchronous) and our
async SQLAlchemy setup.

Key decisions:
  1. DB URL comes from settings — never hardcoded here.
  2. We use the SYNC psycopg2 URL for migrations, not asyncpg.
     Alembic does not support async drivers natively.
  3. Base.metadata is passed to Alembic so autogenerate can
     compare the live DB schema against our ORM models.
  4. All models are imported via db/base.py — they must be
     registered before target_metadata is set.

How autogenerate works:
  alembic revision --autogenerate -m "message"
    → Connects to DB with sync URL
    → Reads live schema (existing tables/columns/indexes)
    → Compares with Base.metadata (ORM definitions)
    → Writes a migration script with the diff
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------------------------------------------------------
# Make sure the backend package is importable when running alembic
# from inside the backend/ directory.
# ---------------------------------------------------------------------------
# Project layout:
#   project1/
#     backend/          ← CWD when running alembic
#       migrations/
#         env.py        ← this file
#       main.py
# We add the project root (one level above backend/) to sys.path.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# ---------------------------------------------------------------------------
# Import settings — provides the DB URL
# ---------------------------------------------------------------------------
from backend.core.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# Import Base WITH all models registered
# ---------------------------------------------------------------------------
# db/base.py imports every model module, which causes SQLAlchemy to
# register them all under Base.metadata.  If you add a new model,
# add its import to db/base.py — not here.
from backend.db.base import Base  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to alembic.ini values
# ---------------------------------------------------------------------------
config = context.config

# Override the sqlalchemy.url with our settings-based sync URL.
# This is safer than putting the URL in alembic.ini because:
#   - Secrets stay in .env, not in a tracked ini file
#   - Works consistently across dev / CI / production
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Set up Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that autogenerate compares against the live DB
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration mode
# ---------------------------------------------------------------------------
# Used when you want to generate SQL scripts without a live DB connection.
# Run with: alembic upgrade head --sql
def run_migrations_offline() -> None:
    """
    Generate migration SQL without connecting to the database.
    Useful for reviewing what will be executed before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Include all schema changes Alembic can detect
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration mode (default)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """
    Connect to the database and apply migrations directly.
    This is the standard mode used in all environments.

    Note: We use the SYNC psycopg2 driver here, not asyncpg.
    Alembic's migration runner is synchronous — it doesn't work
    with async connections.  The application uses asyncpg at
    runtime; migrations use psycopg2.  Both drivers talk to the
    same PostgreSQL server.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,      # No pooling — migrations are one-shot
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detect column type changes (e.g. String → Text)
            compare_type=True,
            # Detect server_default changes
            compare_server_default=True,
            # Include indexes in autogenerate
            include_indexes=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point — called by Alembic CLI
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
