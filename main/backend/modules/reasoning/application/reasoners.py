from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from backend.modules.reasoning.domain.entities import Stance


@dataclass(frozen=True, slots=True)
class ReasoningInputs:
    """Everything a reasoner needs, already gathered by the service.

    Keeping this a plain data bag means a reasoner never does I/O — it only
    turns structured evidence into an explanation, which makes both the
    deterministic and LLM adapters trivial to test.
    """

    symbol: str
    company_name: str | None = None

    fused_action: str | None = None       # buy / hold / sell
    fused_score: float | None = None
    fused_confidence: float | None = None

    company_overall: float | None = None
    company_rating: str | None = None

    signal_drivers: tuple[str, ...] = field(default_factory=tuple)
    event_summaries: tuple[str, ...] = field(default_factory=tuple)
    research_snippets: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ReasonedResult:
    stance: Stance
    headline: str
    explanation: str
    drivers: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.0


class ReasonerContract(ABC):
    """Port for turning gathered evidence into an explainable opinion.

    The Phase 11 default is a deterministic, template-based reasoner (offline,
    reproducible, exercised in tests). An LLM-backed reasoner implements the
    same contract to produce a richer narrative, and can be swapped in at the
    composition root without changing the service, domain, or API.
    """

    name: str = "reasoner"

    @abstractmethod
    async def reason(self, inputs: ReasoningInputs) -> ReasonedResult:
        raise NotImplementedError
