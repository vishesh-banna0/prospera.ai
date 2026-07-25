from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.modules.advisor.application.dto import (
    RecommendationView,
    SectorImpactView,
)
from backend.modules.events.domain.entities import (
    EventImportance,
    EventType,
    NewsEvent,
    Sentiment,
)
from backend.shared.llm import LLMClient, extract_json_object

logger = logging.getLogger(__name__)

DETERMINISTIC = "deterministic"

# Event types whose shocks are usually TRANSIENT/EXTERNAL — a strong company
# dipping on one of these is a candidate long-term "buy the dip" (recovery).
_TRANSIENT_EXTERNAL = {
    EventType.GEOPOLITICAL,
    EventType.MONETARY_POLICY,
    EventType.TRADE_POLICY,
    EventType.MACRO_INDICATOR,
    EventType.SECTOR_TREND,
}
# Event types that signal a FUNDAMENTAL company problem — NOT a dip to buy.
_FUNDAMENTAL_COMPANY = {
    EventType.EARNINGS_MISS,
    EventType.GUIDANCE_CUT,
    EventType.LEGAL,
    EventType.REGULATORY,
    EventType.LAYOFFS,
}

_IMPORTANCE_WEIGHT = {
    EventImportance.HIGH: 3,
    EventImportance.MEDIUM: 2,
    EventImportance.LOW: 1,
}


@dataclass(frozen=True, slots=True)
class Analysis:
    market_summary: str
    sectors: tuple[SectorImpactView, ...]


@dataclass(frozen=True, slots=True)
class Strategy:
    short_term: tuple[RecommendationView, ...]
    long_term: tuple[RecommendationView, ...]


def _event_target(event: NewsEvent) -> str:
    if event.symbols:
        return event.symbols[0]
    if event.sectors:
        return event.sectors[0]
    return "Broad market"


def _events_as_text(events: list[NewsEvent], limit: int = 30) -> str:
    lines = []
    for e in events[:limit]:
        who = ",".join(e.symbols) or ",".join(e.sectors) or "market"
        lines.append(
            f"- [{e.event_date.date()}] ({e.event_type.value}/{e.sentiment.value}/"
            f"{e.importance.value}) {who}: {e.headline[:140]}"
        )
    return "\n".join(lines)


def _clamp_confidence(raw: object, default: float = 0.5) -> float:
    try:
        return min(1.0, max(0.0, float(raw)))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Analyst agent — recent events -> per-sector impact
# ---------------------------------------------------------------------------

_ANALYST_SYSTEM = (
    "You are a financial market analyst. For each affected sector, judge the "
    "likely effect on that sector's STOCK PRICES (its investment outlook) — NOT "
    "the mood of the headline. Crucially, some sectors BENEFIT from bad-sounding "
    "news: a war or oil-supply shock is usually POSITIVE for Energy and Defense "
    "(higher oil and defense spending) but NEGATIVE for airlines, logistics and "
    "other oil consumers; a risk-off shock lifts safe havens (gold, utilities). "
    "So 'impact' is the direction of the sector's shares, which can differ from "
    "the news sentiment. Respond with ONLY a JSON object:\n"
    '{"market_summary": "<2-3 sentences>", "sectors": [{"sector": str, '
    '"impact": "positive"|"negative"|"mixed"|"neutral", '
    '"magnitude": "high"|"medium"|"low", "drivers": ["<short strings>"]}]}\n'
    "Be concise and only include sectors the events actually touch."
)


class AnalystAgent:
    """Summarizes recent events into per-sector impact (its own model)."""

    role = "analyst"

    def __init__(self, llm: LLMClient | None, model: str) -> None:
        self._llm = llm
        self._model = model

    async def analyze(self, events: list[NewsEvent]) -> tuple[Analysis, str]:
        if self._llm is not None:
            try:
                return await self._analyze_llm(events), self._model
            except Exception as exc:
                logger.warning("Analyst LLM failed (%s); using deterministic.", exc)
        return _deterministic_analysis(events), DETERMINISTIC

    async def _analyze_llm(self, events: list[NewsEvent]) -> Analysis:
        raw = await self._llm.complete(
            system=_ANALYST_SYSTEM, user=_events_as_text(events)
        )
        parsed = extract_json_object(raw)
        summary = str(parsed.get("market_summary") or "").strip()
        sectors: list[SectorImpactView] = []
        for item in parsed.get("sectors", []) or []:
            if not isinstance(item, dict) or not item.get("sector"):
                continue
            sectors.append(
                SectorImpactView(
                    sector=str(item["sector"]).strip(),
                    impact=_one_of(item.get("impact"), _IMPACTS, "neutral"),
                    magnitude=_one_of(item.get("magnitude"), _MAGNITUDES, "medium"),
                    drivers=tuple(
                        str(d).strip() for d in (item.get("drivers") or []) if str(d).strip()
                    )[:4],
                )
            )
        if not summary and not sectors:
            raise ValueError("Analyst returned empty analysis.")
        if not summary:
            summary = f"Analyzed {len(events)} recent events."
        return Analysis(market_summary=summary, sectors=tuple(sectors[:8]))


# ---------------------------------------------------------------------------
# Strategist agent — analysis + events -> short/long-term recommendations
# ---------------------------------------------------------------------------

_STRATEGIST_SYSTEM = (
    "You are a portfolio strategist. Using the sector outlook and events, give "
    "SHORT-TERM (event-driven) and LONG-TERM (mean-reversion) recommendations.\n"
    "Rules:\n"
    "- Short-term trades react to catalysts and MUST include a 'trigger' (an "
    "exit/entry condition).\n"
    "- Separate BENEFICIARIES from VICTIMS of a transient shock:\n"
    "  * A sector that BENEFITS (e.g. Energy/Defense in a war, as oil and "
    "spending rise) is a SHORT-TERM buy you EXIT when the event resolves. It is "
    "NOT a long-term buy — the boost fades.\n"
    "  * A strong company/sector temporarily HURT by the event (the dip) is the "
    "LONG-TERM buy-the-dip for recovery.\n"
    "- A FUNDAMENTAL problem (earnings miss, guidance cut, fraud, regulatory) is "
    "a long-term AVOID, not a dip to buy.\n"
    "- Do NOT list the same name as both a short-term and a long-term buy on one "
    "transient catalyst.\n"
    "Example: oil spikes on a war -> SHORT-TERM buy Energy (exit when it "
    "de-escalates); the airline/tech names that fell are the LONG-TERM "
    "buy-the-dip. Stay consistent with the sector outlook you are given.\n"
    "Respond with ONLY a JSON object:\n"
    '{"short_term": [{"target": str, "action": "buy"|"sell"|"hold"|"avoid", '
    '"horizon": "short_term", "rationale": str, "trigger": str, '
    '"confidence": 0..1}], "long_term": [{"target": str, "action": '
    '"buy"|"sell"|"hold"|"avoid", "horizon": "long_term", "rationale": str, '
    '"confidence": 0..1}]}'
)


class StrategistAgent:
    """Turns analysis + events into dual-horizon calls (its own model)."""

    role = "strategist"

    def __init__(self, llm: LLMClient | None, model: str) -> None:
        self._llm = llm
        self._model = model

    async def strategize(
        self, analysis: Analysis, events: list[NewsEvent]
    ) -> tuple[Strategy, str]:
        if self._llm is not None:
            try:
                return await self._strategize_llm(analysis, events), self._model
            except Exception as exc:
                logger.warning("Strategist LLM failed (%s); using deterministic.", exc)
        return _deterministic_strategy(analysis, events), DETERMINISTIC

    async def _strategize_llm(
        self, analysis: Analysis, events: list[NewsEvent]
    ) -> Strategy:
        user = (
            "Sector analysis:\n"
            + "\n".join(
                f"- {s.sector}: {s.impact} ({s.magnitude})" for s in analysis.sectors
            )
            + "\n\nEvents:\n"
            + _events_as_text(events)
        )
        raw = await self._llm.complete(system=_STRATEGIST_SYSTEM, user=user)
        parsed = extract_json_object(raw)
        short = _parse_recs(parsed.get("short_term"), "short_term")
        long = _parse_recs(parsed.get("long_term"), "long_term")
        if not short and not long:
            raise ValueError("Strategist returned no recommendations.")
        return Strategy(short_term=short, long_term=long)


# ---------------------------------------------------------------------------
# Writer agent — analysis + strategy -> plain-English narrative
# ---------------------------------------------------------------------------

_WRITER_SYSTEM = (
    "You are an investment advisor writing for a retail investor. In 4-8 plain "
    "English sentences, summarize the recent news, which sectors are affected, "
    "and the short-term vs long-term guidance. Be concrete and balanced. End "
    "with: 'This is simulated guidance, not investment advice.' Respond with "
    "plain text only."
)


class WriterAgent:
    """Synthesizes the analyst + strategist output into readable advice."""

    role = "writer"

    def __init__(self, llm: LLMClient | None, model: str) -> None:
        self._llm = llm
        self._model = model

    async def write(self, analysis: Analysis, strategy: Strategy) -> tuple[str, str]:
        if self._llm is not None:
            try:
                text = await self._llm.complete(
                    system=_WRITER_SYSTEM, user=_writer_input(analysis, strategy)
                )
                text = text.strip()
                if text:
                    return text, self._model
            except Exception as exc:
                logger.warning("Writer LLM failed (%s); using deterministic.", exc)
        return _deterministic_narrative(analysis, strategy), DETERMINISTIC


# ---------------------------------------------------------------------------
# Deterministic fallbacks (offline, reproducible, and always available)
# ---------------------------------------------------------------------------

_IMPACTS = ("positive", "negative", "mixed", "neutral")
_MAGNITUDES = ("high", "medium", "low")
_ACTIONS = ("buy", "sell", "hold", "avoid")


def _one_of(raw: object, allowed: tuple[str, ...], default: str) -> str:
    value = str(raw or "").strip().lower()
    return value if value in allowed else default


def _parse_recs(raw: object, horizon: str) -> tuple[RecommendationView, ...]:
    out: list[RecommendationView] = []
    for item in raw or []:
        if not isinstance(item, dict) or not item.get("target"):
            continue
        trigger = item.get("trigger")
        out.append(
            RecommendationView(
                target=str(item["target"]).strip(),
                action=_one_of(item.get("action"), _ACTIONS, "hold"),
                horizon=horizon,
                rationale=str(item.get("rationale") or "").strip(),
                trigger=str(trigger).strip() if trigger else None,
                confidence=_clamp_confidence(item.get("confidence")),
            )
        )
    return tuple(out[:6])


# Sectors whose SHARES typically rise on a conflict/supply shock even though the
# news itself reads negative (higher oil / defense spending).
_GEO_POSITIVE_SECTORS = {"Energy", "Defense", "Defence"}


def _deterministic_analysis(events: list[NewsEvent]) -> Analysis:
    # 'impact' is the effect on the sector's SHARES, not the news mood. Company
    # events give a direction from sentiment; transient/external shocks add
    # volatility (mixed) unless the sector is a known beneficiary.
    buckets: dict[str, dict] = {}
    for e in events:
        sectors = e.sectors or ("Broad market",)
        weight = _IMPORTANCE_WEIGHT[e.importance]
        transient = e.event_type in _TRANSIENT_EXTERNAL
        for sector in sectors:
            bucket = buckets.setdefault(
                sector, {"pos": 0, "neg": 0, "volatile": 0, "drivers": []}
            )
            if transient:
                if (
                    e.event_type == EventType.GEOPOLITICAL
                    and sector in _GEO_POSITIVE_SECTORS
                ):
                    bucket["pos"] += weight
                else:
                    bucket["volatile"] += weight
            elif e.sentiment == Sentiment.POSITIVE:
                bucket["pos"] += weight
            elif e.sentiment == Sentiment.NEGATIVE:
                bucket["neg"] += weight
            else:
                bucket["volatile"] += weight
            if e.importance != EventImportance.LOW and len(bucket["drivers"]) < 3:
                bucket["drivers"].append(e.headline[:120])

    sectors: list[SectorImpactView] = []
    for sector, bucket in sorted(
        buckets.items(),
        key=lambda kv: -(kv[1]["pos"] + kv[1]["neg"] + kv[1]["volatile"]),
    ):
        pos, neg, vol = bucket["pos"], bucket["neg"], bucket["volatile"]
        if pos and neg and abs(pos - neg) <= 1:
            impact = "mixed"
        elif pos > neg:
            impact = "positive"
        elif neg > pos:
            impact = "negative"
        elif vol > 0:
            impact = "mixed"
        else:
            impact = "neutral"
        total = pos + neg + vol
        magnitude = "high" if total >= 6 else "medium" if total >= 3 else "low"
        sectors.append(
            SectorImpactView(
                sector=sector,
                impact=impact,
                magnitude=magnitude,
                drivers=tuple(bucket["drivers"]),
            )
        )

    summary = (
        f"Analyzed {len(events)} recent events across {len(sectors)} sector groups."
    )
    return Analysis(market_summary=summary, sectors=tuple(sectors[:8]))


def _share_direction(event: NewsEvent, impacts: dict[str, str]) -> str:
    """Best-effort direction of the TARGET's shares (not the news mood)."""

    if event.event_type in _TRANSIENT_EXTERNAL:
        sector = event.sectors[0] if event.sectors else None
        impact = impacts.get(sector) if sector else None
        if impact == "positive":
            return "up"
        if impact == "negative":
            return "down"
        if event.event_type == EventType.GEOPOLITICAL and sector in _GEO_POSITIVE_SECTORS:
            return "up"
        return "down" if event.sentiment == Sentiment.NEGATIVE else "up"
    return "up" if event.sentiment == Sentiment.POSITIVE else "down"


def _deterministic_strategy(analysis: Analysis, events: list[NewsEvent]) -> Strategy:
    impacts = {s.sector: s.impact for s in analysis.sectors}
    short: list[RecommendationView] = []
    long: list[RecommendationView] = []
    seen_short: set[str] = set()
    seen_long: set[str] = set()

    ranked = sorted(events, key=lambda e: _IMPORTANCE_WEIGHT[e.importance], reverse=True)
    for e in ranked:
        if e.importance == EventImportance.LOW:
            continue
        target = _event_target(e)
        direction = _share_direction(e, impacts)  # "up" | "down" for the shares
        transient = e.event_type in _TRANSIENT_EXTERNAL
        label = e.event_type.value.replace("_", " ")

        # Short-term: trade the immediate move, always with an exit condition.
        if target != "Broad market" and target not in seen_short:
            if direction == "up":
                short.append(
                    RecommendationView(
                        target=target,
                        action="buy",
                        horizon="short_term",
                        rationale=f"Catalyst lifting {target}: {e.headline[:110]}",
                        trigger=(
                            "Exit when the event de-escalates — the move is "
                            "event-driven."
                            if transient
                            else "Take profit once the catalyst is priced in."
                        ),
                        confidence=e.confidence,
                    )
                )
            else:
                short.append(
                    RecommendationView(
                        target=target,
                        action="avoid" if transient else "sell",
                        horizon="short_term",
                        rationale=f"Catalyst pressuring {target}: {e.headline[:110]}",
                        trigger="Reassess once the driver reverses.",
                        confidence=e.confidence,
                    )
                )
            seen_short.add(target)

        # Long-term: buy transient DIPS (victims), avoid transient SPIKES
        # (beneficiaries — the boost fades) and fundamental problems.
        long_target = e.symbols[0] if e.symbols else (e.sectors[0] if e.sectors else None)
        if not long_target or long_target in seen_long:
            continue
        if transient and direction == "down":
            long.append(
                RecommendationView(
                    target=long_target,
                    action="buy",
                    horizon="long_term",
                    rationale=(
                        f"Temporary {label} shock — quality names tend to "
                        f"recover: {e.headline[:90]}"
                    ),
                    confidence=min(0.6, e.confidence),
                )
            )
            seen_long.add(long_target)
        elif transient and direction == "up":
            long.append(
                RecommendationView(
                    target=long_target,
                    action="avoid",
                    horizon="long_term",
                    rationale=(
                        f"The {label}-driven gain is temporary and likely to "
                        "fade — not a long-term hold here."
                    ),
                    confidence=min(0.55, e.confidence),
                )
            )
            seen_long.add(long_target)
        elif not transient and direction == "down":
            long.append(
                RecommendationView(
                    target=long_target,
                    action="avoid",
                    horizon="long_term",
                    rationale=(
                        f"Fundamental concern ({label}) — not a dip to buy: "
                        f"{e.headline[:90]}"
                    ),
                    confidence=min(0.6, e.confidence),
                )
            )
            seen_long.add(long_target)
        elif not transient and direction == "up":
            long.append(
                RecommendationView(
                    target=long_target,
                    action="buy",
                    horizon="long_term",
                    rationale=f"Fundamental improvement ({label}): {e.headline[:90]}",
                    confidence=min(0.6, e.confidence),
                )
            )
            seen_long.add(long_target)

    return Strategy(short_term=tuple(short[:6]), long_term=tuple(long[:6]))


def _writer_input(analysis: Analysis, strategy: Strategy) -> str:
    lines = [f"Market summary: {analysis.market_summary}", "Sectors:"]
    lines += [f"- {s.sector}: {s.impact} ({s.magnitude})" for s in analysis.sectors]
    lines.append("Short-term calls:")
    lines += [
        f"- {r.action} {r.target} — {r.rationale}" for r in strategy.short_term
    ]
    lines.append("Long-term calls:")
    lines += [
        f"- {r.action} {r.target} — {r.rationale}" for r in strategy.long_term
    ]
    return "\n".join(lines)


def _deterministic_narrative(analysis: Analysis, strategy: Strategy) -> str:
    parts = [analysis.market_summary]
    negative = [s.sector for s in analysis.sectors if s.impact == "negative"]
    positive = [s.sector for s in analysis.sectors if s.impact == "positive"]
    if negative:
        parts.append("Under pressure: " + ", ".join(negative[:4]) + ".")
    if positive:
        parts.append("Catching a bid: " + ", ".join(positive[:4]) + ".")
    if strategy.short_term:
        parts.append(
            "Short-term: "
            + "; ".join(f"{r.action} {r.target}" for r in strategy.short_term[:3])
            + "."
        )
    if strategy.long_term:
        parts.append(
            "Long-term: "
            + "; ".join(f"{r.action} {r.target}" for r in strategy.long_term[:3])
            + "."
        )
    parts.append("This is simulated guidance, not investment advice.")
    return " ".join(parts)


# Purpose:
# The multi-agent Advisor team: an Analyst, a Strategist, and a Writer, each on
# its own local model, each with a deterministic fallback so the Advisor works
# offline and never hard-fails. The dual-horizon logic (event-driven short-term
# with exit triggers; transient-dip vs fundamental-problem long-term) lives in
# both the LLM prompts and the deterministic rules.
