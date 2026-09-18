from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.modules.advisor.application.agents import (
    DETERMINISTIC,
    AnalystAgent,
    PortfolioAgent,
    PortfolioPosition,
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


# ---------------------------------------------------------------------------
# Portfolio-aware advice
# ---------------------------------------------------------------------------


class _FakeQuantity:
    def __init__(self, value: float) -> None:
        self.value = value


class _FakeCost:
    def __init__(self, amount: float) -> None:
        self.amount = amount


class _FakeHolding:
    def __init__(self, symbol: str, quantity: float, average_cost: float) -> None:
        self.symbol = symbol
        self.quantity = _FakeQuantity(quantity)
        self.average_cost = _FakeCost(average_cost)


class _FakeHoldingRepository:
    def __init__(self, holdings: list[_FakeHolding]) -> None:
        self._holdings = holdings

    async def list_by_environment(self, environment_id):
        return self._holdings


class _BrokenHoldingRepository:
    async def list_by_environment(self, environment_id):
        raise RuntimeError("database is down")


async def _service_with_holdings(holdings, repo_override=None) -> AdvisorService:
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
                "e1",
                EventType.EARNINGS_MISS,
                Sentiment.NEGATIVE,
                EventImportance.HIGH,
                "ACME misses earnings badly as demand collapses",
                symbols=("ACME",),
                sectors=("Technology",),
            ),
        ]
    )
    return AdvisorService(
        event_repository=repo,
        analyst=AnalystAgent(None, "m-analyst"),
        strategist=StrategistAgent(None, "m-strategist"),
        writer=WriterAgent(None, "m-writer"),
        portfolio=PortfolioAgent(None, "m-portfolio"),
        holding_repository=(
            repo_override
            if repo_override is not None
            else _FakeHoldingRepository(holdings)
        ),
    )


@pytest.mark.asyncio
async def test_advice_is_market_wide_when_no_environment_is_given() -> None:
    """The portfolio node must not run — the original behaviour is preserved."""
    service = await _service_with_holdings([_FakeHolding("ACME", 10, 100.0)])

    report = await service.generate(AdvisorRequest(max_events=20))

    assert report.portfolio is None
    assert "portfolio" not in report.models


@pytest.mark.asyncio
async def test_portfolio_pass_maps_market_calls_onto_held_positions() -> None:
    holdings = [
        _FakeHolding("ACME", quantity=60, average_cost=100.0),  # 60% — oversized
        _FakeHolding("RELIANCE.NS", quantity=20, average_cost=100.0),  # 20%
        _FakeHolding("UNRELATED", quantity=20, average_cost=100.0),  # 20%
    ]
    service = await _service_with_holdings(holdings)

    report = await service.generate(
        AdvisorRequest(max_events=20, environment_id="env-1")
    )

    assert report.portfolio is not None
    assert report.models["portfolio"] == DETERMINISTIC
    advice = report.portfolio
    assert advice.environment_id == "env-1"
    assert advice.holdings_count == 3

    by_symbol = {a.symbol: a for a in advice.actions}
    # Every held position is reported, none invented.
    assert set(by_symbol) == {"ACME", "RELIANCE.NS", "UNRELATED"}
    # ACME has a fundamental problem (earnings miss) -> reduce, not accumulate.
    assert by_symbol["ACME"].action in ("trim", "exit")
    # No event touches UNRELATED, so the correct answer is to do nothing.
    assert by_symbol["UNRELATED"].action == "hold"
    # Weights are computed from cost basis and reported per position.
    assert by_symbol["ACME"].weight_pct == pytest.approx(60.0, abs=0.1)

    # 60% in one name is a concentration risk regardless of the thesis.
    assert any("ACME" in warning for warning in advice.concentration_warnings)
    # Actionable items sort ahead of holds.
    assert advice.actions[-1].action == "hold"
    assert advice.summary


@pytest.mark.asyncio
async def test_positive_call_on_an_oversized_position_does_not_add() -> None:
    """A good thesis is not a reason to concentrate further."""
    strategy_source = await _service_with_holdings(
        [_FakeHolding("RELIANCE.NS", quantity=90, average_cost=100.0),
         _FakeHolding("OTHER", quantity=10, average_cost=100.0)]
    )

    report = await strategy_source.generate(
        AdvisorRequest(max_events=20, environment_id="env-1")
    )

    action = next(
        a for a in report.portfolio.actions if a.symbol == "RELIANCE.NS"
    )
    # The short-term view on Energy is positive, but the position is 90%.
    assert action.action != "add"
    assert "already large" in action.rationale or action.action in ("trim", "hold")


@pytest.mark.asyncio
async def test_unheld_buy_calls_surface_as_opportunities() -> None:
    service = await _service_with_holdings(
        [_FakeHolding("UNRELATED", quantity=10, average_cost=100.0),
         _FakeHolding("OTHER", quantity=10, average_cost=100.0)]
    )

    report = await service.generate(
        AdvisorRequest(max_events=20, environment_id="env-1")
    )

    opportunities = " ".join(report.portfolio.unheld_opportunities)
    # RELIANCE.NS is a buy call the portfolio has no exposure to.
    assert "RELIANCE.NS" in opportunities


@pytest.mark.asyncio
async def test_holdings_failure_degrades_to_market_wide_advice() -> None:
    service = await _service_with_holdings([], repo_override=_BrokenHoldingRepository())

    report = await service.generate(
        AdvisorRequest(max_events=20, environment_id="env-1")
    )

    # The report still arrives; it just has no portfolio section.
    assert report.portfolio is None
    assert report.event_count == 2
    assert report.narrative


@pytest.mark.asyncio
async def test_empty_portfolio_skips_the_portfolio_node() -> None:
    service = await _service_with_holdings([])

    report = await service.generate(
        AdvisorRequest(max_events=20, environment_id="env-empty")
    )

    assert report.portfolio is None


@pytest.mark.asyncio
async def test_portfolio_agent_reports_every_position_even_when_unaffected() -> None:
    positions = [
        PortfolioPosition("AAA", quantity=1, value=100.0, weight_pct=50.0),
        PortfolioPosition("BBB", quantity=1, value=100.0, weight_pct=50.0),
    ]
    strategy, _ = await StrategistAgent(None, "m").strategize(
        (await AnalystAgent(None, "m").analyze([]))[0], []
    )

    advice, source = await PortfolioAgent(None, "m").advise(
        strategy, positions, "env-1"
    )

    assert source == DETERMINISTIC
    assert {a.symbol for a in advice.actions} == {"AAA", "BBB"}
    assert all(a.action == "hold" for a in advice.actions)


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
