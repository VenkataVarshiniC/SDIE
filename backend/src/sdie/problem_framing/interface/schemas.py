from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FrameworkSectionSchema(BaseModel):
    key: str
    label: str
    guiding_question: str


class CreateFrameworkAnalysisRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    framework: str = Field(pattern="^(five_forces|swot)$")
    entries: dict[str, list[str]] = Field(default_factory=dict)


class FrameworkAnalysisResponse(BaseModel):
    analysis_id: UUID
    title: str
    framework: str
    entries: dict[str, list[str]]
    completion_ratio: float
    created_at: datetime


class ClearHistoryResponse(BaseModel):
    deleted_count: int
