from __future__ import annotations

from functools import lru_cache

from sdie.recommendation_synthesis.application.ports import OnePagerRendererPort
from sdie.recommendation_synthesis.infrastructure.reportlab_renderer import (
    ReportLabOnePagerRenderer,
)


@lru_cache
def get_one_pager_renderer() -> OnePagerRendererPort:
    return ReportLabOnePagerRenderer()
