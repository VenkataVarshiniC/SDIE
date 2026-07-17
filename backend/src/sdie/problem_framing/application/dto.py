from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateFrameworkAnalysisCommand:
    tenant_id: UUID
    title: str
    framework: str
    entries: dict[str, list[str]]


@dataclass(frozen=True, slots=True)
class FrameworkAnalysisResult:
    analysis_id: UUID
    title: str
    framework: str
    entries: dict[str, list[str]]
    completion_ratio: float
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FrameworkSectionResult:
    key: str
    label: str
    guiding_question: str
