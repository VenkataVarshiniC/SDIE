from __future__ import annotations

from functools import lru_cache

from sdie.workspace.application.ports import EngagementDeckRendererPort
from sdie.workspace.infrastructure.reportlab_deck_renderer import ReportLabEngagementDeckRenderer


@lru_cache
def get_engagement_deck_renderer() -> EngagementDeckRendererPort:
    return ReportLabEngagementDeckRenderer()
