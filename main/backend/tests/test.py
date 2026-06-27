from datetime import datetime
from decimal import Decimal

from modules.market_data.domain.entities import (
    HistoricalPriceBar,
    Instrument,
    MarketMetadata,
    MarketQuote,
)

from backend.shared.types import (
    CurrencyCode,
    FxRate,
    Money,
    Symbol,
)


def separator(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_money():
    separator("MONEY")

    m1 = Money(
        amount=Decimal("100.50"),
        currency=CurrencyCode("USD"),
    )

    m2 = Money(
        amount=Decimal("50.25"),
        currency=CurrencyCode("USD"),
    )

    print("m1:", m1)
    print("m2:", m2)

    print("Addition:", m1 + m2)
    print("Subtraction:", m1 - m2)

    print("m1 > m2:", m1 > m2)
    print("m1 < m2:", m1 < m2)

    print("Is Zero:", m1.is_zero())
    print("Is Negative:", m1.is_negative())


def test_fx():
    separator("FX CONVERSION")

    usd = Money(
        amount=Decimal("10"),
        currency=CurrencyCode("USD"),
    )

    fx = FxRate(
        from_currency=CurrencyCode("USD"),
        to_currency=CurrencyCode("INR"),
        rate=Decimal("83.50"),
    )

    converted = fx.convert(usd)

    print("Original:", usd)
    print("Converted:", converted)


def test_instrument():
    separator("INSTRUMENT")

    instrument = Instrument(
        symbol=Symbol("AAPL"),
        instrument_name="Apple Inc.",
        exchange="NASDAQ",
        native_currency=CurrencyCode("USD"),
        sector="Technology",
        industry="Consumer Electronics",
    )

    print(instrument)
    print("Priced Symbol:", instrument.priced_symbol)


def test_market_quote():
    separator("MARKET QUOTE")

    quote = MarketQuote(
        symbol=Symbol("AAPL"),
        native_currency=CurrencyCode("USD"),
        last_price=Money(
            amount=Decimal("210"),
            currency=CurrencyCode("USD"),
        ),
        previous_close=Money(
            amount=Decimal("200"),
            currency=CurrencyCode("USD"),
        ),
        open_price=Money(
            amount=Decimal("205"),
            currency=CurrencyCode("USD"),
        ),
        high_price=Money(
            amount=Decimal("215"),
            currency=CurrencyCode("USD"),
        ),
        low_price=Money(
            amount=Decimal("202"),
            currency=CurrencyCode("USD"),
        ),
        volume=5000000,
        as_of=datetime.now(),
    )

    print(quote)
    print("Price Change:", quote.price_change)
    print("Price Change %:", quote.price_change_percent)


def test_historical_bar():
    separator("HISTORICAL PRICE BAR")

    bar = HistoricalPriceBar(
        symbol=Symbol("AAPL"),
        native_currency=CurrencyCode("USD"),
        open_price=Money(
            amount=Decimal("100"),
            currency=CurrencyCode("USD"),
        ),
        high_price=Money(
            amount=Decimal("110"),
            currency=CurrencyCode("USD"),
        ),
        low_price=Money(
            amount=Decimal("95"),
            currency=CurrencyCode("USD"),
        ),
        close_price=Money(
            amount=Decimal("105"),
            currency=CurrencyCode("USD"),
        ),
        volume=1000000,
        timestamp=datetime.now(),
    )

    print(bar)


def test_market_metadata():
    separator("MARKET METADATA")

    metadata = MarketMetadata(
        supported_exchanges=("NASDAQ", "NYSE", "NSE"),
        supported_currencies=(
            CurrencyCode("USD"),
            CurrencyCode("INR"),
        ),
        timezone="America/New_York",
        market_status="OPEN",
        last_updated_at=datetime.now(),
    )

    print(metadata)


def test_currency_validation():
    separator("CURRENCY VALIDATION")

    try:
        MarketQuote(
            symbol=Symbol("AAPL"),
            native_currency=CurrencyCode("USD"),
            last_price=Money(
                amount=Decimal("210"),
                currency=CurrencyCode("INR"),
            ),
        )

    except ValueError as exc:
        print("Validation successful.")
        print("Caught:", exc)


if __name__ == "__main__":
    test_money()
    test_fx()
    test_instrument()
    test_market_quote()
    test_historical_bar()
    test_market_metadata()
    test_currency_validation()

    separator("ALL TESTS COMPLETED")