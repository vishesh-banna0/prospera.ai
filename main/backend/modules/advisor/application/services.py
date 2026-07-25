from __future__ import annotations

from datetime import UTC, datetime

from backend.modules.advisor.application.agents import (
    DETERMINISTIC,
    AnalystAgent,
    StrategistAgent,
    WriterAgent,
)
from backend.modules.advisor.application.dto import AdvisorReportView, AdvisorRequest
from backend.modules.advisor.application.graph import build_advisor_graph
from backend.modules.events.domain.repositories import NewsEventRepository


class AdvisorService:
    """Coordinates the multi-agent Advisor: Analyst -> Strategist -> Writer.

    Pulls the recent events warehouse, runs them through the LangGraph agent
    graph (each node an agent on its own model, each with a deterministic
    fallback), and assembles one advisory report with short/long-term guidance.
    """

    def __init__(
        self,
        event_repository: NewsEventRepository,
        analyst: AnalystAgent,
        strategist: StrategistAgent,
        writer: WriterAgent,
    ) -> None:
        self._events = event_repository
        self._graph = build_advisor_graph(analyst, strategist, writer)

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

        final = await self._graph.ainvoke({"events": events})
        analysis = final["analysis"]
        strategy = final["strategy"]
        narrative = final["narrative"]
        analyst_src = final["analyst_source"]
        strategist_src = final["strategist_source"]
        writer_src = final["writer_source"]

        sources = (analyst_src, strategist_src, writer_src)
        if all(s == DETERMINISTIC for s in sources):
            source = "deterministic"
        elif all(s != DETERMINISTIC for s in sources):
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
            models={
                "analyst": analyst_src,
                "strategist": strategist_src,
                "writer": writer_src,
            },
            source=source,
        )


# Purpose:
# Application boundary for the AI Advisor — orchestrate the agent team over the
# recent events warehouse and return one structured, explainable readout.
