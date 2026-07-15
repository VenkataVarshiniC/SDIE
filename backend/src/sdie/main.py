from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sdie.config import get_settings
from sdie.decision_analysis.interface.router import router as decision_analysis_router
from sdie.financial_modeling.interface.router import router as financial_modeling_router

settings = get_settings()

app = FastAPI(
    title="Strategic Decision Intelligence Engine",
    description="API for structured strategic decision support: financial modeling, "
    "decision science, evidence-grounded synthesis.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(financial_modeling_router, prefix="/api/v1")
app.include_router(decision_analysis_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
