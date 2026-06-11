# Purpose:
# Declares contracts required to retrieve and optionally cache market data.
#
# Future Responsibilities:
# - Define how current quotes are retrieved.
# - Define how historical prices are accessed.
# - Define how symbol search and metadata lookup are performed.
#
# Dependencies:
# - backend.modules.market_data.domain.entities
#
# Future Classes / Interfaces:
# - QuoteRepository
# - HistoricalPriceRepository
# - SymbolSearchRepository
# - MarketMetadataRepository
#
# What Should Not Live Here:
# - Provider-specific HTTP code.
# - Simulator read models.
# - API pagination formatting.
