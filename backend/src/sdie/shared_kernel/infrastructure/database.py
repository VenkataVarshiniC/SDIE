from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from sdie.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """Binds the Postgres row-level-security session variable. Every
    request-scoped session MUST call this before touching tenant data —
    it's what turns 'tenant_id column' into an actual isolation guarantee
    rather than an application-trust convention."""
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
