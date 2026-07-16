"""Integration tests hit a real Postgres — they exercise the ORM mapping,
generated columns, and full-text search that unit tests deliberately can't
touch. No testcontainers here: this platform's own constraint is "no
Docker," so these tests point at whatever SDIE_DATABASE_URL already
resolves to (the same hosted-or-native database used for local dev) and
skip cleanly if it isn't reachable — CI supplies one via a service
container (see .github/workflows/ci.yml), which is a different thing from
requiring Docker on a contributor's machine.

Every test runs inside a transaction that's rolled back at teardown, so
nothing written here persists and tests never depend on each other's state
or a special separate test database.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sdie.config import get_settings
from sdie.shared_kernel.domain.value_objects import TenantId
from sdie.shared_kernel.infrastructure.database import set_tenant_context


def _database_available() -> bool:
    import asyncio

    async def _check() -> bool:
        try:
            engine = create_async_engine(get_settings().database_url)
            async with engine.connect():
                pass
            await engine.dispose()
            return True
        except Exception:
            return False

    return asyncio.run(_check())


requires_db = pytest.mark.skipif(
    not _database_available(),
    reason="No reachable Postgres at SDIE_DATABASE_URL — set it to run integration tests "
    "(see README: hosted free tier or native install, no Docker required).",
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(get_settings().database_url)
    connection = await engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
def tenant_id() -> TenantId:
    return TenantId(uuid.uuid4())


@pytest_asyncio.fixture
async def tenant_scoped_session(db_session: AsyncSession, tenant_id: TenantId) -> AsyncSession:
    await set_tenant_context(db_session, tenant_id.value)
    return db_session
