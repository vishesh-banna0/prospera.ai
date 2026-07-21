from __future__ import annotations

import logging

from backend.modules.reasoning.application.reasoners import (
    ReasonedResult,
    ReasonerContract,
    ReasoningInputs,
)
from backend.modules.reasoning.domain.entities import Stance
from backend.shared.llm import LLMClient, extract_json_object

logger = logging.getLogger(__name__)


def _stance_from_action(action: str | None) -> Stance:
    return {
        "buy": Stance.BULLISH,
        "sell": Stance.BEARISH,
        "hold": Stance.NEUTRAL,
    }.get(action or "", Stance.NEUTRAL)


def _build_drivers(inputs: ReasoningInputs) -> tuple[str, ...]:
    drivers: list[str] = []
    if inputs.company_overall is not None:
        drivers.append(
            f"Company score {inputs.company_overall:.0f}/100"
            + (f" ({inputs.company_rating})" if inputs.company_rating else "")
        )
    drivers.extend(inputs.signal_drivers)
    drivers.extend(inputs.event_summaries[:3])
    return tuple(drivers)


class DeterministicReasoner(ReasonerContract):
    """Template-based reasoner: offline, reproducible, and always available.

    Maps the fused decision to a stance and assembles a plain-English
    explanation from the structured evidence. No model, no network — this is
    the default and the fallback for the LLM reasoner.
    """

    name = "deterministic"

    async def reason(self, inputs: ReasoningInputs) -> ReasonedResult:
        stance = _stance_from_action(inputs.fused_action)
        drivers = _build_drivers(inputs)
        confidence = inputs.fused_confidence or 0.0
        name = inputs.company_name or inputs.symbol

        headline = f"{stance.value.capitalize()} on {inputs.symbol}"
        if inputs.fused_action:
            headline += f" — fused signal says {inputs.fused_action.upper()}"

        parts: list[str] = []
        if inputs.fused_action is not None:
            parts.append(
                f"The blended signal for {name} is {inputs.fused_action.upper()} "
                f"(score {inputs.fused_score:+.2f}, confidence {confidence:.0%})."
            )
        else:
            parts.append(
                f"No fused signal has been computed for {name} yet, so this view "
                "is neutral until the upstream signals are available."
            )
        if inputs.company_overall is not None:
            parts.append(
                f"Company intelligence scores it {inputs.company_overall:.0f}/100"
                + (f" ({inputs.company_rating})." if inputs.company_rating else ".")
            )
        if inputs.event_summaries:
            parts.append(
                "Recent events: " + "; ".join(inputs.event_summaries[:3]) + "."
            )
        if inputs.research_snippets:
            parts.append(
                "Grounded in research context: "
                + inputs.research_snippets[0][:160].strip()
                + "…"
            )

        return ReasonedResult(
            stance=stance,
            headline=headline,
            explanation=" ".join(parts),
            drivers=drivers,
            confidence=confidence,
        )


_SYSTEM_PROMPT = (
    "You are a buy-side financial analyst. You are given structured evidence "
    "about one stock (a blended trading signal, a company score, recent news "
    "events, and research snippets). Weigh the evidence and respond with ONLY a "
    "JSON object using exactly these keys:\n"
    '{"stance": "bullish"|"bearish"|"neutral", "headline": <one short line>, '
    '"explanation": <2-4 sentences citing the evidence>, "drivers": [<short '
    'bullet strings>]}\n'
    "Be balanced and do not invent facts beyond the evidence provided."
)


class LLMReasoner(ReasonerContract):
    """LLM-backed reasoner producing a richer narrative (same contract).

    Prompts a locally-hosted, OpenAI-compatible chat model with the structured
    evidence and parses a JSON opinion. Any failure falls back to the
    deterministic reasoner, so enabling it never reduces reliability. The
    quantitative confidence is carried over from the fused signal rather than
    trusting the model to self-report a calibrated number.
    """

    name = "llm"

    def __init__(self, llm: LLMClient, fallback: ReasonerContract | None = None) -> None:
        self._llm = llm
        self._fallback = fallback or DeterministicReasoner()

    async def reason(self, inputs: ReasoningInputs) -> ReasonedResult:
        prompt = self._build_prompt(inputs)
        try:
            raw = await self._llm.complete(system=_SYSTEM_PROMPT, user=prompt)
            parsed = extract_json_object(raw)
        except Exception as exc:
            logger.warning("LLM reasoning failed (%s); using deterministic.", exc)
            return await self._fallback.reason(inputs)

        try:
            stance = Stance(str(parsed.get("stance", "neutral")).strip().lower())
        except ValueError:
            stance = _stance_from_action(inputs.fused_action)

        headline = str(parsed.get("headline") or f"{stance.value.capitalize()} on {inputs.symbol}")
        explanation = str(parsed.get("explanation") or "").strip()
        if not explanation:
            return await self._fallback.reason(inputs)

        raw_drivers = parsed.get("drivers")
        drivers = (
            tuple(str(d) for d in raw_drivers if str(d).strip())
            if isinstance(raw_drivers, list)
            else _build_drivers(inputs)
        )

        return ReasonedResult(
            stance=stance,
            headline=headline,
            explanation=explanation,
            drivers=drivers,
            confidence=inputs.fused_confidence or 0.0,
        )

    def _build_prompt(self, inputs: ReasoningInputs) -> str:
        lines = [f"Symbol: {inputs.symbol}"]
        if inputs.company_name:
            lines.append(f"Company: {inputs.company_name}")
        if inputs.fused_action is not None:
            lines.append(
                f"Blended signal: {inputs.fused_action.upper()} "
                f"(score {inputs.fused_score:+.2f}, confidence {inputs.fused_confidence:.0%})"
            )
        if inputs.company_overall is not None:
            lines.append(
                f"Company score: {inputs.company_overall:.0f}/100 ({inputs.company_rating})"
            )
        if inputs.signal_drivers:
            lines.append("Signal drivers: " + "; ".join(inputs.signal_drivers))
        if inputs.event_summaries:
            lines.append("Recent events: " + "; ".join(inputs.event_summaries[:5]))
        for i, snippet in enumerate(inputs.research_snippets[:3], 1):
            lines.append(f"Research snippet {i}: {snippet}")
        return "\n".join(lines)
