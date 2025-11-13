from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---------------------------
# Make sure project root is in path
# ---------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# ---------------------------
# Import Base and all models
# ---------------------------
from core.models.base import Base
import models.models  # make sure all models are loaded

# ---------------------------
# Alembic Config
# ---------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------
# Set target_metadata for autogenerate
# ---------------------------
target_metadata = Base.metadata
print("DEBUG Alembic sees tables in metadata:", list(target_metadata.tables.keys()))
if not target_metadata.tables:
    raise RuntimeError("No tables found in Base.metadata. Check model imports!")

# ---------------------------
# Offline migrations
# ---------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# ---------------------------
# Online migrations
# ---------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,   # detect column type changes
            render_as_batch=True # important for SQLite
        )

        with context.begin_transaction():
            context.run_migrations()

# ---------------------------
# Entrypoint
# ---------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
