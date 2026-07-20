from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from backend.modules.events.application.extractors import EventExtractorContract
from backend.modules.events.domain.entities import (
    EventImportance,
    EventType,
    NewsEvent,
    Sentiment,
)
from backend.modules.news.domain.entities import NewsArticle


@dataclass(frozen=True, slots=True)
class _EventRule:
    """One detection rule for the rule-based extractor.

    ``pattern`` is a compiled regex tested against the lowercased article
    text. ``requires_earnings_context`` gates earnings beat/miss on the text
    actually being about earnings/results (so "the plan missed the deadline"
    is not read as an earnings miss).
    """

    event_type: EventType
    default_sentiment: Sentiment
    base_importance: EventImportance
    confidence: float
    pattern: re.Pattern[str]
    requires_earnings_context: bool = False


# Detected in priority order; the first matching rule wins. An article that
# matches nothing produces no event, which is expected and correct.
_EARNINGS_CONTEXT = re.compile(
    r"\b(earnings|results|profit|revenue|quarter|quarterly|q[1-4]|guidance)\b"
)

_RULES: tuple[_EventRule, ...] = (
    _EventRule(
        EventType.MERGER_ACQUISITION,
        Sentiment.NEUTRAL,
        EventImportance.HIGH,
        0.7,
        re.compile(
            r"\b(acquir\w*|acquisition|merg\w*|takeover|buyout|to buy|"
            r"buys? rival|stake in)\b"
        ),
    ),
    _EventRule(
        EventType.IPO,
        Sentiment.NEUTRAL,
        EventImportance.HIGH,
        0.7,
        re.compile(r"\b(ipo|initial public offering|market debut|going public|lists on)\b"),
    ),
    _EventRule(
        EventType.EARNINGS_BEAT,
        Sentiment.POSITIVE,
        EventImportance.HIGH,
        0.8,
        re.compile(
            r"\b(beat|beats|topped|tops|exceed\w*|above estimates|"
            r"better[- ]than[- ]expected)\b"
        ),
        requires_earnings_context=True,
    ),
    _EventRule(
        EventType.EARNINGS_MISS,
        Sentiment.NEGATIVE,
        EventImportance.HIGH,
        0.8,
        re.compile(
            r"\b(miss|misses|missed|below estimates|worse[- ]than[- ]expected|"
            r"fell short|shortfall)\b"
        ),
        requires_earnings_context=True,
    ),
    _EventRule(
        EventType.GUIDANCE_RAISED,
        Sentiment.POSITIVE,
        EventImportance.HIGH,
        0.75,
        re.compile(
            r"\b(rais\w* (its )?(guidance|forecast|outlook)|"
            r"lifts? (guidance|forecast|outlook)|"
            r"upgrade[sd]? (its )?guidance|boosts? (its )?outlook)\b"
        ),
    ),
    _EventRule(
        EventType.GUIDANCE_CUT,
        Sentiment.NEGATIVE,
        EventImportance.HIGH,
        0.75,
        re.compile(
            r"\b(cuts? (its )?(guidance|forecast|outlook)|"
            r"lowers? (its )?(guidance|forecast|outlook)|"
            r"slashes? (its )?(guidance|forecast|outlook)|profit warning|warns?)\b"
        ),
    ),
    _EventRule(
        EventType.LAYOFFS,
        Sentiment.NEGATIVE,
        EventImportance.MEDIUM,
        0.7,
        re.compile(r"\b(layoffs?|lays off|job cuts|cuts? jobs|workforce reduction)\b"),
    ),
    _EventRule(
        EventType.REGULATORY,
        Sentiment.NEGATIVE,
        EventImportance.MEDIUM,
        0.65,
        re.compile(
            r"\b(regulator\w*|antitrust|probe|investigation|sanction\w*|"
            r"sebi|\brbi\b|\bsec\b|fined?|penalt\w*)\b"
        ),
    ),
    _EventRule(
        EventType.LEADERSHIP_CHANGE,
        Sentiment.NEUTRAL,
        EventImportance.MEDIUM,
        0.6,
        re.compile(
            r"\b(ceo|cfo|chief executive|resign\w*|steps down|appoints?|"
            r"names? new|new chief)\b"
        ),
    ),
    _EventRule(
        EventType.ANALYST_RATING,
        Sentiment.NEUTRAL,
        EventImportance.MEDIUM,
        0.6,
        re.compile(
            r"\b(upgrade[sd]?|downgrade[sd]?|price target|outperform|underperform|"
            r"overweight|underweight|buy rating|sell rating)\b"
        ),
    ),
    _EventRule(
        EventType.DIVIDEND,
        Sentiment.POSITIVE,
        EventImportance.MEDIUM,
        0.6,
        re.compile(r"\b(dividend|payout|buyback|share repurchase)\b"),
    ),
    _EventRule(
        EventType.LEGAL,
        Sentiment.NEGATIVE,
        EventImportance.MEDIUM,
        0.6,
        re.compile(r"\b(lawsuit|sues?|sued|settlement|litigation|court ruling)\b"),
    ),
    _EventRule(
        EventType.PARTNERSHIP,
        Sentiment.POSITIVE,
        EventImportance.LOW,
        0.55,
        re.compile(r"\b(partnership|partners? with|joint venture|teams? up|alliance)\b"),
    ),
    _EventRule(
        EventType.PRODUCT_LAUNCH,
        Sentiment.POSITIVE,
        EventImportance.LOW,
        0.55,
        re.compile(r"\b(launch\w*|unveil\w*|introduc\w*|rolls? out|new product)\b"),
    ),
    _EventRule(
        EventType.EARNINGS,
        Sentiment.NEUTRAL,
        EventImportance.MEDIUM,
        0.55,
        re.compile(
            r"\b(earnings|quarterly results|q[1-4] results|financial results|"
            r"reports? (profit|revenue|loss))\b"
        ),
    ),
)

_POSITIVE_TERMS: tuple[str, ...] = (
    "gain", "gains", "gained", "surge", "surges", "surged", "jump", "jumps",
    "rally", "rallies", "rallied", "rise", "rises", "rose", "soar", "soars",
    "record high", "strong", "growth", "climbs", "climbed", "boost", "beat",
    "beats", "tops", "profit", "upgrade", "outperform",
)

_NEGATIVE_TERMS: tuple[str, ...] = (
    "fall", "falls", "fell", "drop", "drops", "dropped", "plunge", "plunges",
    "slump", "slumps", "decline", "declines", "weak", "loss", "losses", "warn",
    "warns", "cut", "cuts", "miss", "misses", "slash", "sinks", "tumble",
    "tumbles", "downgrade", "underperform", "layoff", "layoffs",
)


class RuleBasedEventExtractor(EventExtractorContract):
    """Deterministic keyword/regex event extractor.

    The Phase 8 default: no API key, no network, fully reproducible, and
    exercised in the test suite. It detects the single best-matching event
    type per article (priority-ordered), refines sentiment from a small
    lexicon, and inherits the article's symbols and sectors.

    It is deliberately conservative — it favors precision over recall and
    emits nothing when unsure. Swap in an LLM adapter (same contract) when
    higher recall and nuance are needed.
    """

    source = "rule-based"

    async def extract_events(
        self,
        article: NewsArticle,
    ) -> list[NewsEvent]:
        text = self._build_text(article)
        if not text:
            return []

        has_earnings_context = bool(_EARNINGS_CONTEXT.search(text))

        matched: _EventRule | None = None
        for rule in _RULES:
            if rule.requires_earnings_context and not has_earnings_context:
                continue
            if rule.pattern.search(text):
                matched = rule
                break

        if matched is None:
            return []

        sentiment = self._resolve_sentiment(matched, text)
        importance = self._resolve_importance(matched, text)
        primary_symbol = article.symbols[0] if article.symbols else ""

        event = NewsEvent(
            event_id=self._event_id(article.article_id, matched.event_type, primary_symbol),
            article_id=article.article_id,
            event_type=matched.event_type,
            sentiment=sentiment,
            importance=importance,
            headline=article.title,
            summary=article.summary,
            symbols=article.symbols,
            sectors=article.sectors,
            keywords=self._matched_keywords(matched, text),
            confidence=matched.confidence,
            source=self.source,
            event_date=article.published_at,
        )
        return [event]

    def _build_text(
        self,
        article: NewsArticle,
    ) -> str:
        parts = [article.title, article.summary or "", article.body or ""]
        return " ".join(part for part in parts if part).lower().strip()

    def _resolve_sentiment(
        self,
        rule: _EventRule,
        text: str,
    ) -> Sentiment:
        # Event types with a strong inherent direction keep their default.
        anchored = {
            EventType.EARNINGS_BEAT,
            EventType.EARNINGS_MISS,
            EventType.GUIDANCE_RAISED,
            EventType.GUIDANCE_CUT,
            EventType.LAYOFFS,
        }
        if rule.event_type in anchored:
            return rule.default_sentiment

        positive = self._count_terms(text, _POSITIVE_TERMS)
        negative = self._count_terms(text, _NEGATIVE_TERMS)
        if positive > negative:
            return Sentiment.POSITIVE
        if negative > positive:
            return Sentiment.NEGATIVE
        return rule.default_sentiment

    def _resolve_importance(
        self,
        rule: _EventRule,
        text: str,
    ) -> EventImportance:
        if rule.base_importance == EventImportance.MEDIUM:
            positive = self._count_terms(text, _POSITIVE_TERMS)
            negative = self._count_terms(text, _NEGATIVE_TERMS)
            if abs(positive - negative) >= 2:
                return EventImportance.HIGH
        return rule.base_importance

    def _matched_keywords(
        self,
        rule: _EventRule,
        text: str,
    ) -> tuple[str, ...]:
        found = rule.pattern.findall(text)
        flattened: list[str] = []
        for item in found:
            value = item if isinstance(item, str) else next((part for part in item if part), "")
            value = value.strip()
            if value and value not in flattened:
                flattened.append(value)
        return tuple(flattened[:5])

    def _count_terms(
        self,
        text: str,
        terms: tuple[str, ...],
    ) -> int:
        return sum(1 for term in terms if term in text)

    def _event_id(
        self,
        article_id: str,
        event_type: EventType,
        primary_symbol: str,
    ) -> str:
        fingerprint = "|".join((article_id, event_type.value, primary_symbol))
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
