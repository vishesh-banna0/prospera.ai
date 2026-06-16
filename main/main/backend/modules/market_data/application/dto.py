# Purpose:
# Defines input and output contracts for market data use cases.
#
# Future Responsibilities:
# - Standardize quote requests, historical price requests, and symbol search requests.
# - Standardize response objects returned to simulator and API consumers.
#
# Dependencies:
# - backend.shared.types
#
# Future Classes:
# - QuoteRequest
# - HistoricalPriceRequest
# - SymbolSearchRequest
# - QuoteView
# - HistoricalPriceSeriesView
# - InstrumentSearchResultView
#
# What Should Not Live Here:
# - Vendor payload parsing.
# - Cache invalidation logic.
# - Simulator performance calculations.
