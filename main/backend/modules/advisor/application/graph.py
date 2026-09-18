from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.modules.advisor.application.agents import (
    Analysis,
    AnalystAgent,
    PortfolioAgent,
    PortfolioPosition,
    Strategy,
    StrategistAgent,
    WriterAgent,
)
from backend.modules.advisor.application.dto import PortfolioAdviceView
from backend.modules.events.domain.entities import NewsEvent


class AdvisorState(TypedDict, total=False):
    """Shared state passed between the agent nodes as the graph runs."""

    events: list[NewsEvent]
    # Present only when the caller asked for portfolio-aware advice.
    positions: list[PortfolioPosition]
    environment_id: str

    analysis: Analysis
    strategy: Strategy
    portfolio: PortfolioAdviceView | None
    narrative: str

    analyst_source: str
    strategist_source: str
    portfolio_source: str
    writer_source: str


def build_advisor_graph(
    analyst: AnalystAgent,
    strategist: StrategistAgent,
    writer: WriterAgent,
    portfolio: PortfolioAgent | None = None,
) -> Any:
    """Compile the Analyst -> Strategist -> [Portfolio] -> Writer agent graph.

    Each node runs one agent (on its own model, with its own deterministic
    fallback) and writes its result into shared state.

    The Portfolio node is conditional: the graph branches after the Strategist
    and only runs it when the request supplied holdings. That is a real
    routing decision rather than a flag inside a node, which is what LangGraph
    is for — and it keeps the market-wide report on exactly the path it had
    before, so adding portfolio awareness cost the old behaviour nothing.

    Flow:
        START -> analyst -> strategist -> (portfolio?) -> writer -> END
    """

    async def analyst_node(state: AdvisorState) -> AdvisorState:
        analysis, source = await analyst.analyze(state["events"])
        return {"analysis": analysis, "analyst_source": source}

    async def strategist_node(state: AdvisorState) -> AdvisorState:
        strategy, source = await strategist.strategize(
            state["analysis"], state["events"]
        )
        return {"strategy": strategy, "strategist_source": source}

    async def portfolio_node(state: AdvisorState) -> AdvisorState:
        advice, source = await portfolio.advise(
            state["strategy"],
            state.get("positions") or [],
            state.get("environment_id") or "",
        )
        return {"portfolio": advice, "portfolio_source": source}

    async def writer_node(state: AdvisorState) -> AdvisorState:
        narrative, source = await writer.write(
            state["analysis"], state["strategy"], state.get("portfolio")
        )
        return {"narrative": narrative, "writer_source": source}

    def route_after_strategist(state: AdvisorState) -> str:
        """Run the portfolio pass only when there are positions to reason about."""
        if portfolio is not None and state.get("positions"):
            return "portfolio"
        return "writer"

    graph = StateGraph(AdvisorState)
    graph.add_node("analyst", analyst_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "analyst")
    graph.add_edge("analyst", "strategist")

    if portfolio is not None:
        graph.add_node("portfolio", portfolio_node)
        graph.add_conditional_edges(
            "strategist",
            route_after_strategist,
            {"portfolio": "portfolio", "writer": "writer"},
        )
        graph.add_edge("portfolio", "writer")
    else:
        graph.add_edge("strategist", "writer")

    graph.add_edge("writer", END)

    return graph.compile()


# Purpose:
# The LangGraph orchestration for the multi-agent Advisor. Nodes wrap the agents
# in application/agents.py; the graph fixes the Analyst -> Strategist ->
# [Portfolio] -> Writer flow, routes around the portfolio pass when no holdings
# were supplied, and carries state between them.
