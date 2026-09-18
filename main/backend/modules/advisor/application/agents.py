from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.modules.advisor.application.dto import (
    HoldingActionView,
    PortfolioAdviceView,
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


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    """One held position, reduced to what the Advisor needs to reason about.

    Deliberately not the simulator's ``Holding`` entity — the Advisor should
    not depend on the simulator's value objects, only on symbol and size.
    """

    symbol: str
    quantity: float
    value: float
    weight_pct: float


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
                return await self._analyze_llm(events), (getattr(self._llm, "last_model", None) or self._model)
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
                return await self._strategize_llm(analysis, events), (getattr(self._llm, "last_model", None) or self._model)
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
# Portfolio agent — strategy + holdings -> per-position actions
# ---------------------------------------------------------------------------

# Absolute floor for calling a position oversized. Below this, a holding is
# not a concentration risk no matter how few names the portfolio has.
_CONCENTRATION_FLOOR_PCT = 25.0

# ...but the floor alone is wrong for small portfolios: in a 2-stock book,
# equal weight is 50% and flagging both halves would demand trimming into a
# target that cannot exist. So a position is oversized only once it is also
# half again as large as an equal-weight slice.
_CONCENTRATION_EQUAL_WEIGHT_MULTIPLE = 1.5


def _concentration_threshold(position_count: int) -> float:
    """The weight above which a position dominates *this* portfolio."""

    if position_count <= 0:
        return _CONCENTRATION_FLOOR_PCT
    equal_weight = 100.0 / position_count
    return max(
        _CONCENTRATION_FLOOR_PCT,
        equal_weight * _CONCENTRATION_EQUAL_WEIGHT_MULTIPLE,
    )

_PORTFOLIO_SYSTEM = (
    "You are a portfolio manager. You are given a market view (sector outlook "
    "and buy/sell calls) and the investor's ACTUAL holdings with their weights. "
    "Translate the market view into an action for each position they hold.\n"
    "Rules:\n"
    "- Only reference symbols in the holdings list. Do NOT invent positions.\n"
    "- 'add' only if the view is positive AND the position is not already "
    "oversized. 'trim' for an oversized position or a weakening view. 'exit' "
    "for a fundamental problem. 'hold' when the view does not touch it — this "
    "is the correct answer for most positions most of the time.\n"
    "- Flag a position as a concentration risk when it is much larger than an "
    "equal-weight slice of this portfolio, even if you like it.\n"
    "- Name market calls the portfolio has NO exposure to as opportunities.\n"
    "Respond with ONLY a JSON object:\n"
    '{"summary": "<2-3 sentences about this portfolio>", "actions": '
    '[{"symbol": str, "action": "add"|"trim"|"exit"|"hold", "rationale": str, '
    '"driver": str, "confidence": 0..1}], "concentration_warnings": [str], '
    '"unheld_opportunities": [str]}'
)


class PortfolioAgent:
    """Maps the market-wide strategy onto the positions actually held.

    This is what makes the Advisor portfolio-aware rather than a market
    commentator: the Analyst and Strategist reason about the world, and this
    agent answers "so what should *I* do, given what I own?". Positions the
    market view says nothing about correctly come back as ``hold``.

    Same shape as the other agents — its own model, its own deterministic
    fallback — so an unavailable model degrades the answer instead of the
    endpoint.
    """

    role = "portfolio"

    def __init__(self, llm: LLMClient | None, model: str) -> None:
        self._llm = llm
        self._model = model

    async def advise(
        self,
        strategy: Strategy,
        positions: list[PortfolioPosition],
        environment_id: str,
    ) -> tuple[PortfolioAdviceView, str]:
        if not positions:
            return (
                PortfolioAdviceView(
                    environment_id=environment_id,
                    holdings_count=0,
                    summary="This portfolio holds no positions yet.",
                ),
                DETERMINISTIC,
            )
        if self._llm is not None:
            try:
                advice = await self._advise_llm(strategy, positions, environment_id)
                return advice, (getattr(self._llm, "last_model", None) or self._model)
            except Exception as exc:
                logger.warning("Portfolio LLM failed (%s); using deterministic.", exc)
        return (
            _deterministic_portfolio_advice(strategy, positions, environment_id),
            DETERMINISTIC,
        )

    async def _advise_llm(
        self,
        strategy: Strategy,
        positions: list[PortfolioPosition],
        environment_id: str,
    ) -> PortfolioAdviceView:
        user = (
            "Holdings:\n"
            + "\n".join(
                f"- {p.symbol}: {p.weight_pct:.1f}% of portfolio "
                f"({p.quantity:g} units)"
                for p in positions
            )
            + "\n\nShort-term calls:\n"
            + "\n".join(
                f"- {r.action} {r.target} — {r.rationale}" for r in strategy.short_term
            )
            + "\n\nLong-term calls:\n"
            + "\n".join(
                f"- {r.action} {r.target} — {r.rationale}" for r in strategy.long_term
            )
        )
        raw = await self._llm.complete(system=_PORTFOLIO_SYSTEM, user=user)
        parsed = extract_json_object(raw)

        held = {p.symbol.upper(): p for p in positions}
        actions: list[HoldingActionView] = []
        seen: set[str] = set()
        for item in parsed.get("actions", []) or []:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol") or "").strip().upper()
            # Hard guard against the model inventing positions.
            if symbol not in held or symbol in seen:
                continue
            seen.add(symbol)
            driver = item.get("driver")
            actions.append(
                HoldingActionView(
                    symbol=symbol,
                    action=_one_of(item.get("action"), _HOLDING_ACTIONS, "hold"),
                    weight_pct=round(held[symbol].weight_pct, 2),
                    rationale=str(item.get("rationale") or "").strip(),
                    driver=str(driver).strip() if driver else None,
                    confidence=_clamp_confidence(item.get("confidence")),
                )
            )

        # Anything the model skipped is an implicit hold — never silently drop
        # a position from the report.
        for symbol, position in held.items():
            if symbol in seen:
                continue
            actions.append(
                HoldingActionView(
                    symbol=symbol,
                    action="hold",
                    weight_pct=round(position.weight_pct, 2),
                    rationale="No recent event in the market view touches this position.",
                    confidence=0.4,
                )
            )

        if not actions:
            raise ValueError("Portfolio agent returned no usable actions.")

        summary = str(parsed.get("summary") or "").strip()
        return PortfolioAdviceView(
            environment_id=environment_id,
            holdings_count=len(positions),
            actions=tuple(_sorted_actions(actions)),
            concentration_warnings=_merge_concentration_warnings(
                parsed.get("concentration_warnings"), positions
            ),
            unheld_opportunities=tuple(
                str(o).strip()
                for o in (parsed.get("unheld_opportunities") or [])
                if str(o).strip()
            )[:5],
            summary=summary or _portfolio_summary(actions, positions),
        )


# ---------------------------------------------------------------------------
# Writer agent — analysis + strategy -> plain-English narrative
# ---------------------------------------------------------------------------

_WRITER_SYSTEM = (
    "You are an investment advisor writing for a retail investor. In 4-8 plain "
    "English sentences, summarize the recent news, which sectors are affected, "
    "and the short-term vs long-term guidance. If the investor's own portfolio "
    "positions are provided, address them directly — what to do and what to "
    "leave alone — rather than speaking only about the market. Be concrete and "
    "balanced. End with: 'This is simulated guidance, not investment advice.' "
    "Respond with plain text only."
)


class WriterAgent:
    """Synthesizes the analyst + strategist output into readable advice."""

    role = "writer"

    def __init__(self, llm: LLMClient | None, model: str) -> None:
        self._llm = llm
        self._model = model

    async def write(
        self,
        analysis: Analysis,
        strategy: Strategy,
        portfolio: PortfolioAdviceView | None = None,
    ) -> tuple[str, str]:
        if self._llm is not None:
            try:
                text = await self._llm.complete(
                    system=_WRITER_SYSTEM,
                    user=_writer_input(analysis, strategy, portfolio),
                )
                text = text.strip()
                if text:
                    return text, (getattr(self._llm, "last_model", None) or self._model)
            except Exception as exc:
                logger.warning("Writer LLM failed (%s); using deterministic.", exc)
        return _deterministic_narrative(analysis, strategy, portfolio), DETERMINISTIC


# ---------------------------------------------------------------------------
# Deterministic fallbacks (offline, reproducible, and always available)
# ---------------------------------------------------------------------------

_IMPACTS = ("positive", "negative", "mixed", "neutral")
_MAGNITUDES = ("high", "medium", "low")
_ACTIONS = ("buy", "sell", "hold", "avoid")
_HOLDING_ACTIONS = ("add", "trim", "exit", "hold")

# Report order: the actions that require doing something come first, and
# "hold" (the common, do-nothing case) sinks to the bottom.
_ACTION_PRIORITY = {"exit": 0, "trim": 1, "add": 2, "hold": 3}


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


def _sorted_actions(actions: list[HoldingActionView]) -> list[HoldingActionView]:
    return sorted(
        actions,
        key=lambda a: (_ACTION_PRIORITY.get(a.action, 9), -a.weight_pct),
    )


def _concentration_warnings(positions: list[PortfolioPosition]) -> list[str]:
    """Positions large enough to dominate the portfolio's outcome."""

    threshold = _concentration_threshold(len(positions))
    warnings = []
    for position in sorted(positions, key=lambda p: -p.weight_pct):
        if position.weight_pct >= threshold:
            warnings.append(
                f"{position.symbol} is {position.weight_pct:.1f}% of the "
                "portfolio — a single-name shock would move the whole book."
            )
    return warnings


def _merge_concentration_warnings(
    raw: object,
    positions: list[PortfolioPosition],
) -> tuple[str, ...]:
    """Model-written warnings plus the ones arithmetic guarantees.

    Concentration is a fact about the weights, not a judgement call, so the
    deterministic warnings are always included even when the LLM missed them.
    """

    model_warnings = [
        str(w).strip() for w in (raw or []) if str(w).strip()
    ]
    computed = _concentration_warnings(positions)
    # Keep computed ones first; they are the ones we can stand behind.
    merged = computed + [w for w in model_warnings if w not in computed]
    return tuple(merged[:5])


def _portfolio_summary(
    actions: list[HoldingActionView],
    positions: list[PortfolioPosition],
) -> str:
    counts: dict[str, int] = {}
    for action in actions:
        counts[action.action] = counts.get(action.action, 0) + 1
    moves = ", ".join(
        f"{count} to {name}"
        for name, count in sorted(counts.items(), key=lambda kv: _ACTION_PRIORITY.get(kv[0], 9))
        if name != "hold"
    )
    if not moves:
        return (
            f"No recent event materially affects these {len(positions)} "
            "positions — no action suggested."
        )
    return f"Across {len(positions)} positions: {moves}."


def _deterministic_portfolio_advice(
    strategy: Strategy,
    positions: list[PortfolioPosition],
    environment_id: str,
) -> PortfolioAdviceView:
    """Rule-based mapping of market calls onto held positions.

    The mapping is deliberately conservative: a position is only acted on when
    a call names it (by symbol) or names its sector. Everything else is a
    hold, because "the market view is silent on this" is not a reason to
    trade. Long-term calls take precedence over short-term ones for a position
    already owned, since an existing holding is a long-term commitment.
    """

    held = {p.symbol.upper(): p for p in positions}
    # Map each held symbol to the strongest call that names it. Long-term
    # calls are applied last so they win where both exist.
    call_by_symbol: dict[str, RecommendationView] = {}
    for recommendation in (*strategy.short_term, *strategy.long_term):
        target = recommendation.target.strip().upper()
        if target in held:
            call_by_symbol[target] = recommendation

    threshold = _concentration_threshold(len(positions))
    actions: list[HoldingActionView] = []
    for symbol, position in held.items():
        call = call_by_symbol.get(symbol)
        oversized = position.weight_pct >= threshold

        if call is None:
            action, rationale = (
                ("trim", "No fresh catalyst, and the position is oversized.")
                if oversized
                else ("hold", "No recent event in the market view touches this position.")
            )
            confidence = 0.4
        elif call.action == "buy":
            if oversized:
                action = "hold"
                rationale = (
                    f"The view is positive ({call.rationale[:90]}), but at "
                    f"{position.weight_pct:.1f}% this position is already large "
                    "enough — adding would concentrate it further."
                )
            else:
                action = "add"
                rationale = call.rationale or "The market view favours this name."
            confidence = call.confidence
        elif call.action == "avoid":
            action = "trim"
            rationale = call.rationale or "The market view has turned against this name."
            confidence = call.confidence
        elif call.action == "sell":
            action = "exit"
            rationale = call.rationale or "The market view calls for exiting this name."
            confidence = call.confidence
        else:  # "hold"
            action = "hold"
            rationale = call.rationale or "The view is neutral on this position."
            confidence = call.confidence

        actions.append(
            HoldingActionView(
                symbol=symbol,
                action=action,
                weight_pct=round(position.weight_pct, 2),
                rationale=rationale,
                driver=call.target if call else None,
                confidence=confidence,
            )
        )

    # Buy calls on names the portfolio does not own are the opportunities.
    opportunities = []
    for recommendation in (*strategy.long_term, *strategy.short_term):
        target = recommendation.target.strip()
        if recommendation.action != "buy" or target.upper() in held:
            continue
        entry = f"{target} — {recommendation.rationale[:110]}"
        if entry not in opportunities:
            opportunities.append(entry)

    sorted_actions = _sorted_actions(actions)
    return PortfolioAdviceView(
        environment_id=environment_id,
        holdings_count=len(positions),
        actions=tuple(sorted_actions),
        concentration_warnings=tuple(_concentration_warnings(positions)[:5]),
        unheld_opportunities=tuple(opportunities[:5]),
        summary=_portfolio_summary(sorted_actions, positions),
    )


def _writer_input(
    analysis: Analysis,
    strategy: Strategy,
    portfolio: PortfolioAdviceView | None = None,
) -> str:
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
    if portfolio is not None and portfolio.actions:
        lines.append("The investor's actual positions and what to do with them:")
        lines += [
            f"- {a.action.upper()} {a.symbol} ({a.weight_pct:.1f}% of portfolio) "
            f"— {a.rationale}"
            for a in portfolio.actions
        ]
        if portfolio.concentration_warnings:
            lines.append("Concentration risks:")
            lines += [f"- {w}" for w in portfolio.concentration_warnings]
    return "\n".join(lines)


def _deterministic_narrative(
    analysis: Analysis,
    strategy: Strategy,
    portfolio: PortfolioAdviceView | None = None,
) -> str:
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
    if portfolio is not None and portfolio.actions:
        actionable = [a for a in portfolio.actions if a.action != "hold"]
        if actionable:
            parts.append(
                "For your portfolio: "
                + "; ".join(f"{a.action} {a.symbol}" for a in actionable[:3])
                + "."
            )
        else:
            parts.append(
                "For your portfolio: nothing in the recent news calls for a "
                "change to your positions."
            )
        if portfolio.concentration_warnings:
            parts.append(portfolio.concentration_warnings[0])
    parts.append("This is simulated guidance, not investment advice.")
    return " ".join(parts)


# Purpose:
# The multi-agent Advisor team: an Analyst, a Strategist, a Portfolio manager,
# and a Writer, each on its own local model, each with a deterministic fallback
# so the Advisor works offline and never hard-fails. The dual-horizon logic
# (event-driven short-term with exit triggers; transient-dip vs
# fundamental-problem long-term) lives in both the LLM prompts and the
# deterministic rules. The Portfolio agent is what turns a market view into
# advice about positions the investor actually owns; it runs only when the
# request supplies an environment, so the market-wide report is unchanged.
