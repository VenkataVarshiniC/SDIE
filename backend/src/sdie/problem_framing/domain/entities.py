"""Problem Framing domain. The core idea: a partner doesn't start from a
blank page, they reach for a framework (Five Forces, SWOT) that itself
tells them what to consider. Encoding the framework's *structure* — its
sections and guiding questions — as data, not prose, is what lets this
context scaffold an analysis rather than just hold freeform notes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sdie.shared_kernel.domain.events import AggregateRoot, DomainEvent
from sdie.shared_kernel.domain.value_objects import TenantId


class ProblemFramingError(ValueError):
    pass


class Framework(str, Enum):
    FIVE_FORCES = "five_forces"
    SWOT = "swot"


@dataclass(frozen=True, slots=True)
class FrameworkSection:
    key: str
    label: str
    guiding_question: str


FRAMEWORK_TEMPLATES: dict[Framework, list[FrameworkSection]] = {
    Framework.FIVE_FORCES: [
        FrameworkSection(
            "threat_of_new_entrants",
            "Threat of new entrants",
            "How easily could a new competitor enter this market?",
        ),
        FrameworkSection(
            "supplier_power",
            "Bargaining power of suppliers",
            "How much leverage do suppliers have over price and terms?",
        ),
        FrameworkSection(
            "buyer_power",
            "Bargaining power of buyers",
            "How much leverage do customers have to demand lower prices or better terms?",
        ),
        FrameworkSection(
            "threat_of_substitutes",
            "Threat of substitutes",
            "What alternatives could customers switch to instead of this offering?",
        ),
        FrameworkSection(
            "competitive_rivalry",
            "Competitive rivalry",
            "How intense is competition among existing players in this market?",
        ),
    ],
    Framework.SWOT: [
        FrameworkSection(
            "strengths", "Strengths", "What internal advantages does the organization have?"
        ),
        FrameworkSection(
            "weaknesses", "Weaknesses", "What internal limitations could hold the strategy back?"
        ),
        FrameworkSection(
            "opportunities",
            "Opportunities",
            "What external trends or gaps could be exploited?",
        ),
        FrameworkSection(
            "threats", "Threats", "What external forces could threaten this strategy?"
        ),
    ],
}


def get_template(framework: Framework) -> list[FrameworkSection]:
    return FRAMEWORK_TEMPLATES[framework]


@dataclass(frozen=True, kw_only=True)
class FrameworkAnalysisCreated(DomainEvent):
    analysis_id: UUID
    framework: str


@dataclass(slots=True)
class FrameworkAnalysis(AggregateRoot):
    """A filled-in instance of a framework template. `entries` is keyed by
    section key (validated against that framework's template) with a list
    of freeform observations per section — deliberately not further
    structured, since forcing every observation into a quant field here
    would just push the same problem down a level; this context's job is
    to make sure nothing gets skipped, not to quantify it."""

    id: UUID
    tenant_id: TenantId
    title: str
    framework: Framework
    entries: dict[str, list[str]]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)

    @classmethod
    def create(
        cls,
        *,
        tenant_id: TenantId,
        title: str,
        framework: Framework,
        entries: dict[str, list[str]],
    ) -> FrameworkAnalysis:
        if not title.strip():
            raise ProblemFramingError("title must not be empty")

        valid_keys = {s.key for s in get_template(framework)}
        unknown_keys = set(entries.keys()) - valid_keys
        if unknown_keys:
            raise ProblemFramingError(
                f"Unknown section(s) for {framework.value}: {unknown_keys}. "
                f"Valid sections: {sorted(valid_keys)}"
            )
        if not any(entries.get(k) for k in valid_keys):
            raise ProblemFramingError("At least one section must have at least one entry")

        analysis = cls(
            id=uuid4(), tenant_id=tenant_id, title=title, framework=framework, entries=entries
        )
        analysis.raise_event(
            FrameworkAnalysisCreated(
                tenant_id=tenant_id.value, analysis_id=analysis.id, framework=framework.value
            )
        )
        return analysis

    @property
    def completion_ratio(self) -> float:
        """What fraction of this framework's sections have at least one
        entry — a simple, honest signal of how thorough the framing is,
        surfaced back to the user rather than silently accepted."""
        template = get_template(self.framework)
        filled = sum(1 for s in template if self.entries.get(s.key))
        return filled / len(template)
