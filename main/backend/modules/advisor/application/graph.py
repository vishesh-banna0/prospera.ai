from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.modules.advisor.application.agents import (
    Analysis,
    AnalystAgent,
    Strategy,
    StrategistAgent,
    WriterAgent,
)
from backend.modules.events.domain.entities import NewsEvent


class AdvisorState(TypedDict, total=False):
    """Shared state passed between the agent nodes as the graph runs."""

    events: list[NewsEvent]
    analysis: Analysis
    strategy: Strategy
    narrative: str
    analyst_source: str
    strategist_source: str
    writer_source: str


def build_advisor_graph(
    analyst: AnalystAgent,
    strategist: StrategistAgent,
    writer: WriterAgent,
) -> Any:
    """Compile the Analyst -> Strategist -> Writer agent graph.

    Each node runs one agent (on its own model, with its own deterministic
    fallback) and writes its result into shared state. Using LangGraph here
    makes the multi-agent structure explicit and leaves room to grow (branches,
    loops, a coordinator, tool use) for the trading agent in the next phase.
    """

    async def analyst_node(state: AdvisorState) -> AdvisorState:
        analysis, source = await analyst.analyze(state["events"])
        return {"analysis": analysis, "analyst_source": source}

    async def strategist_node(state: AdvisorState) -> AdvisorState:
        strategy, source = await strategist.strategize(
            state["analysis"], state["events"]
        )
        return {"strategy": strategy, "strategist_source": source}

    async def writer_node(state: AdvisorState) -> AdvisorState:
        narrative, source = await writer.write(state["analysis"], state["strategy"])
        return {"narrative": narrative, "writer_source": source}

    graph = StateGraph(AdvisorState)
    graph.add_node("analyst", analyst_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "analyst")
    graph.add_edge("analyst", "strategist")
    graph.add_edge("strategist", "writer")
    graph.add_edge("writer", END)

    return graph.compile()


# Purpose:
# The LangGraph orchestration for the multi-agent Advisor. Nodes wrap the agents
# in application/agents.py; the graph fixes the Analyst -> Strategist -> Writer
# flow and carries state between them.
