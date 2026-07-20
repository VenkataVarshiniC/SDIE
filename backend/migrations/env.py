from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from sdie.config import get_settings
from sdie.decision_analysis.infrastructure import orm as _decision_analysis_orm  # noqa: F401
from sdie.evidence_research.infrastructure import orm as _evidence_research_orm  # noqa: F401

# Import every context's ORM module here so its tables register on
# Base.metadata before autogenerate/upgrade runs. Add a line per new
# bounded context as it gets a persistence layer.
from sdie.financial_modeling.infrastructure import orm as _financial_modeling_orm  # noqa: F401
from sdie.problem_framing.infrastructure import orm as _problem_framing_orm  # noqa: F401
from sdie.recommendation_synthesis.infrastructure import (
    orm as _recommendation_synthesis_orm,  # noqa: F401
)
from sdie.shared_kernel.infrastructure.database import Base
from sdie.workspace.infrastructure import orm as _workspace_orm  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


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


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
