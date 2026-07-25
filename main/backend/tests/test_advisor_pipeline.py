from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.modules.advisor.application.agents import (
    DETERMINISTIC,
    AnalystAgent,
    StrategistAgent,
    WriterAgent,
)
from backend.modules.advisor.application.dto import AdvisorRequest
from backend.modules.advisor.application.services import AdvisorService
from backend.modules.events.domain.entities import (
    EventImportance,
    EventType,
    NewsEvent,
    Sentiment,
)
from backend.modules.events.infrastructure.repositories import (
    InMemoryNewsEventRepository,
)


def _event(
    event_id: str,
    event_type: EventType,
    sentiment: Sentiment,
    importance: EventImportance,
    headline: str,
    symbols: tuple[str, ...] = (),
    sectors: tuple[str, ...] = (),
) -> NewsEvent:
    return NewsEvent(
        event_id=event_id,
        article_id=f"art-{event_id}",
        event_type=event_type,
        sentiment=sentiment,
        importance=importance,
        headline=headline,
        event_date=datetime(2026, 7, 20, tzinfo=UTC),
        symbols=symbols,
        sectors=sectors,
        confidence=0.8,
    )


@pytest.mark.asyncio
async def test_strategist_dual_horizon_transient_vs_fundamental() -> None:
    # A transient external shock (war) on a name = long-term buy-the-dip;
    # a fundamental problem (earnings miss) on a name = long-term avoid.
    events = [
        _event(
            "g1",
            EventType.GEOPOLITICAL,
            Sentiment.NEGATIVE,
            EventImportance.HIGH,
            "War fears hammer Samsung on supply worries",
            symbols=("SSNLF",),
            sectors=("Technology",),
        ),
        _event(
            "e1",
            EventType.EARNINGS_MISS,
            Sentiment.NEGATIVE,
            EventImportance.HIGH,
            "Acme misses earnings badly as demand collapses",
            symbols=("ACME",),
            sectors=("Technology",),
        ),
    ]
    analysis, analyst_src = await AnalystAgent(None, "m").analyze(events)
    strategy, strat_src = await StrategistAgent(None, "m").strategize(analysis, events)

    assert analyst_src == DETERMINISTIC and strat_src == DETERMINISTIC
    long_by_target = {r.target: r for r in strategy.long_term}
    assert long_by_target["SSNLF"].action == "buy"  # transient dip -> buy
    assert long_by_target["ACME"].action == "avoid"  # fundamental -> avoid
    # Every short-term call carries an exit/entry trigger.
    assert strategy.short_term
    assert all(r.horizon == "short_term" for r in strategy.short_term)
    assert all(r.trigger for r in strategy.short_term)


@pytest.mark.asyncio
async def test_advisor_service_runs_graph_deterministically() -> None:
    repo = InMemoryNewsEventRepository()
    await repo.upsert_events(
        [
            _event(
                "g1",
                EventType.GEOPOLITICAL,
                Sentiment.NEGATIVE,
                EventImportance.HIGH,
                "Oil spikes on Middle East conflict",
                symbols=("RELIANCE.NS",),
                sectors=("Energy",),
            ),
            _event(
                "p1",
                EventType.PRODUCT_LAUNCH,
                Sentiment.POSITIVE,
                EventImportance.MEDIUM,
                "TechCo unveils a popular new product",
                symbols=("TECH",),
                sectors=("Technology",),
            ),
        ]
    )
    service = AdvisorService(
        event_repository=repo,
        analyst=AnalystAgent(None, "m-analyst"),
        strategist=StrategistAgent(None, "m-strategist"),
        writer=WriterAgent(None, "m-writer"),
    )

    report = await service.generate(AdvisorRequest(max_events=20))

    assert report.source == "deterministic"
    assert report.event_count == 2
    assert len(report.sectors) >= 1
    assert report.narrative
    assert report.models == {
        "analyst": DETERMINISTIC,
        "strategist": DETERMINISTIC,
        "writer": DETERMINISTIC,
    }
    # Energy benefits from the war short-term, but the boost is temporary — so it
    # should be a SHORT-term buy and a LONG-term avoid (never a long-term buy).
    assert any(
        r.target == "RELIANCE.NS" and r.action == "buy" for r in report.short_term
    )
    assert any(
        r.target == "RELIANCE.NS" and r.action == "avoid" for r in report.long_term
    )
    assert not any(
        r.target == "RELIANCE.NS" and r.action == "buy" for r in report.long_term
    )


@pytest.mark.asyncio
async def test_energy_beneficiary_not_bought_for_both_horizons() -> None:
    # The exact bug reported: a war lifts oil -> Energy shares up. That's a
    # short-term buy you exit on resolution, NOT a long-term buy, and the sector
    # outlook must read positive (share direction), not negative (news mood).
    events = [
        _event(
            "o1",
            EventType.GEOPOLITICAL,
            Sentiment.NEGATIVE,
            EventImportance.HIGH,
            "Oil spikes as war escalates in the Gulf",
            symbols=("XOM",),
            sectors=("Energy",),
        )
    ]
    analysis, _ = await AnalystAgent(None, "m").analyze(events)
    energy = next(s for s in analysis.sectors if s.sector == "Energy")
    assert energy.impact == "positive"  # outlook for shares, not the news mood

    strategy, _ = await StrategistAgent(None, "m").strategize(analysis, events)
    short_buys = {r.target for r in strategy.short_term if r.action == "buy"}
    long_buys = {r.target for r in strategy.long_term if r.action == "buy"}
    assert "XOM" in short_buys
    assert "XOM" not in long_buys  # the spike fades — not a long-term buy


@pytest.mark.asyncio
async def test_advisor_service_handles_no_events() -> None:
    service = AdvisorService(
        event_repository=InMemoryNewsEventRepository(),
        analyst=AnalystAgent(None, "m"),
        strategist=StrategistAgent(None, "m"),
        writer=WriterAgent(None, "m"),
    )
    report = await service.generate(AdvisorRequest())
    assert report.source == "none"
    assert report.event_count == 0
    assert report.short_term == () and report.long_term == ()
