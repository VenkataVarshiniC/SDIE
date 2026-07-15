"""Auth dependency for FastAPI routes.

STUB IMPLEMENTATION: reads tenant/user identity from headers so the rest of
the stack (routers, use cases, RLS wiring) can be built and tested against
a stable interface. Swap the body of `get_current_principal` for real
OIDC/JWT verification (e.g. via python-jose against your IdP's JWKS) before
any non-local deployment — nothing else in the codebase needs to change,
since callers only depend on the `Principal` shape.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException, status


@dataclass(frozen=True, slots=True)
class Principal:
    tenant_id: UUID
    user_id: UUID
    roles: tuple[str, ...]


async def get_current_principal(
    x_tenant_id: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> Principal:
    if not x_tenant_id or not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Tenant-Id / X-User-Id (stub auth — replace with OIDC before deployment)",
        )
    try:
        return Principal(
            tenant_id=UUID(x_tenant_id),
            user_id=UUID(x_user_id),
            roles=("analyst",),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed tenant/user id"
        ) from exc
