from __future__ import annotations

from decimal import Decimal

# Static fallback conversion rates expressed as "how many INR per 1 unit of
# currency". These keep the app working fully offline (and keep the whole test
# suite network-free). When live FX is enabled, these are only used if the live
# fetch fails. They are overridable via configuration (see backend.core.config).
DEFAULT_RATES_TO_INR: dict[str, Decimal] = {
    "INR": Decimal("1"),
    "USD": Decimal("83.0"),
    "EUR": Decimal("90.0"),
    "GBP": Decimal("105.0"),
    "JPY": Decimal("0.55"),
    "AUD": Decimal("55.0"),
    "CAD": Decimal("61.0"),
    "SGD": Decimal("62.0"),
}


def build_rate_table(overrides: dict[str, float] | None = None) -> dict[str, Decimal]:
    """Return a copy of the default INR rate table with any overrides applied."""

    table = dict(DEFAULT_RATES_TO_INR)
    if overrides:
        for code, rate in overrides.items():
            table[str(code).upper()] = Decimal(str(rate))
    return table


# Purpose:
# Hold the static fallback FX rates and a small helper to build the rate table.
# The live/real-time conversion logic lives in the market_data infrastructure
# FX providers so this stays a dependency-free, importable-anywhere primitive.
#
# What Should Not Live Here:
# - Network calls (belong in an FX provider adapter).
# - Business/trading rules.
