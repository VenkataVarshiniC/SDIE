"""Global exception handling. Without this, an unhandled exception in any
route gives the browser a bare 500 with no detail and the server logs
whatever uvicorn's default handler feels like — which is exactly what made
the earlier timezone bug hard to diagnose from the frontend. Every
unhandled error now gets a trace_id the user can quote back, and a full
traceback logged server-side keyed to that same id.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("sdie.errors")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        trace_id = str(uuid.uuid4())
        logger.exception(
            "Unhandled exception (trace_id=%s) on %s %s",
            trace_id,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred.",
                "trace_id": trace_id,
            },
        )
