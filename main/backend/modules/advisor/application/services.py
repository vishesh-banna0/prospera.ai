from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.modules.advisor.application.agents import (
    DETERMINISTIC,
    AnalystAgent,
    PortfolioAgent,
    PortfolioPosition,
    StrategistAgent,
    WriterAgent,
)
from backend.modules.advisor.application.dto import AdvisorReportView, AdvisorRequest
from backend.modules.advisor.application.graph import build_advisor_graph
from backend.modules.events.domain.repositories import NewsEventRepository

logger = logging.getLogger(__name__)


class AdvisorService:
    """Coordinates the multi-agent Advisor: Analyst -> Strategist -> Writer.

    Pulls the recent events warehouse, runs them through the LangGraph agent
    graph (each node an agent on its own model, each with a deterministic
    fallback), and assembles one advisory report with short/long-term guidance.

    When the request names a simulator environment, the graph also runs a
    Portfolio agent that maps the market-wide calls onto the positions actually
    held — so the advice is about this portfolio, not about the market in the
    abstract. Without an environment the behaviour is exactly as before.
    """

    def __init__(
        self,
        event_repository: NewsEventRepository,
        analyst: AnalystAgent,
        strategist: StrategistAgent,
        writer: WriterAgent,
        portfolio: PortfolioAgent | None = None,
        holding_repository=None,
    ) -> None:
        self._events = event_repository
        self._holdings = holding_repository
        self._graph = build_advisor_graph(analyst, strategist, writer, portfolio)

    async def generate(self, request: AdvisorRequest) -> AdvisorReportView:
        max_events = min(max(1, int(request.max_events)), 200)
        events = await self._events.list_events(limit=max_events)
        events = sorted(events, key=lambda e: e.event_date, reverse=True)[:max_events]

        if not events:
            return AdvisorReportView(
                market_summary=(
                    "No recent events to analyze yet. Sync news and run event "
                    "extraction first, then generate advice."
                ),
                sectors=(),
                short_term=(),
                long_term=(),
                narrative="No recent events available to advise on.",
                event_count=0,
                generated_at=datetime.now(UTC),
                models={},
                source="none",
            )

        positions = await self._load_positions(request.environment_id)

        final = await self._graph.ainvoke(
            {
                "events": events,
                "positions": positions,
                "environment_id": request.environment_id or "",
            }
        )
        analysis = final["analysis"]
        strategy = final["strategy"]
        narrative = final["narrative"]
        portfolio_advice = final.get("portfolio")

        sources = {
            "analyst": final["analyst_source"],
            "strategist": final["strategist_source"],
            "writer": final["writer_source"],
        }
        # Only reported when the node actually ran, so the models map stays an
        # honest record of which agents contributed.
        if "portfolio_source" in final:
            sources["portfolio"] = final["portfolio_source"]

        values = tuple(sources.values())
        if all(s == DETERMINISTIC for s in values):
            source = "deterministic"
        elif all(s != DETERMINISTIC for s in values):
            source = "llm"
        else:
            source = "mixed"

        return AdvisorReportView(
            market_summary=analysis.market_summary,
            sectors=analysis.sectors,
            short_term=strategy.short_term,
            long_term=strategy.long_term,
            narrative=narrative,
            event_count=len(events),
            generated_at=datetime.now(UTC),
            models=sources,
            source=source,
            portfolio=portfolio_advice,
        )

    async def _load_positions(
        self,
        environment_id: str | None,
    ) -> list[PortfolioPosition]:
        """Read holdings and convert them to portfolio weights.

        Positions are valued at cost basis, which keeps this to a single
        repository read with no market-data round trip per symbol. Weights are
        what the Portfolio agent reasons about, and cost-basis weights are
        close enough to drive add/trim/exit judgements; the precise live-value
        breakdown is what ``/portfolio/risk`` is for.

        Any failure degrades to a market-wide report rather than failing the
        request — advice without the portfolio pass is still useful.
        """

        if not environment_id or self._holdings is None:
            return []

        try:
            holdings = await self._holdings.list_by_environment(environment_id)
        except Exception as exc:
            logger.warning(
                "Could not load holdings for environment %s (%s); returning "
                "market-wide advice.",
                environment_id,
                exc,
            )
            return []

        raw: list[tuple[str, float, float]] = []
        for holding in holdings:
            try:
                quantity = float(holding.quantity.value)
                cost = float(holding.average_cost.amount)
            except (AttributeError, TypeError, ValueError):
                continue
            if quantity <= 0 or cost < 0:
                continue
            raw.append((str(holding.symbol).upper(), quantity, quantity * cost))

        total_value = sum(value for _, _, value in raw)
        if not raw or total_value <= 0:
            return []

        return [
            PortfolioPosition(
                symbol=symbol,
                quantity=quantity,
                value=value,
                weight_pct=value / total_value * 100.0,
            )
            for symbol, quantity, value in sorted(raw, key=lambda r: -r[2])
        ]


# Purpose:
# Application boundary for the AI Advisor — orchestrate the agent team over the
# recent events warehouse (and, when asked, the investor's actual holdings) and
# return one structured, explainable readout.
