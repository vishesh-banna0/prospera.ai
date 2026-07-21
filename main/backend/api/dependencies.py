from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db_session
from backend.core.exceptions import ConfigurationError
from backend.core.config import get_settings

from backend.modules.simulator.application.services import SimulatorService

from backend.modules.simulator.application.commands import (
    CreateEnvironmentUseCase,
    RenameEnvironmentUseCase,
    DeleteEnvironmentUseCase,
    AddVirtualCashUseCase,
    WithdrawVirtualCashUseCase,
    BuyStockUseCase,
    SellStockUseCase,
)

from backend.modules.simulator.application.queries import (
    GetEnvironmentUseCase,
    GetHoldingsUseCase,
    GetTransactionsUseCase,
    GetPortfolioPerformanceUseCase,
)

from backend.modules.simulator.infrastructure.repositories import (
    SqlEnvironmentRepository,
    SqlHoldingRepository,
    SqlTransactionRepository,
)

from backend.modules.market_data.application.services import MarketDataService
from backend.modules.market_data.infrastructure.clients import FinnhubClient
from backend.modules.market_data.infrastructure.fx import (
    StaticFxRateProvider,
    YFinanceFxRateProvider,
)
from backend.modules.market_data.infrastructure.repositories import (
    CompositeSymbolSearchRepository,
    FinnhubMarketMetadataRepository,
    FinnhubQuoteRepository,
    FinnhubSymbolSearchRepository,
    SqlMarketDataRepository,
    YFinanceHistoricalDataProvider,
)
from backend.modules.news.application.services import NewsIntelligenceService
from backend.modules.news.infrastructure.repositories import FinnhubNewsProvider
from backend.modules.news.infrastructure.repositories import SqlNewsArticleRepository

from backend.modules.events.application.services import EventExtractionService
from backend.modules.events.infrastructure.extractors import RuleBasedEventExtractor
from backend.modules.events.infrastructure.llm_extractor import LLMEventExtractor
from backend.modules.events.infrastructure.repositories import SqlNewsEventRepository

from backend.shared.llm import build_llm_from_settings

from backend.modules.research.application.services import ResearchService
from backend.modules.research.infrastructure.providers import (
    HashingEmbedder,
    PlainTextParser,
)
from backend.modules.research.infrastructure.repositories import SqlResearchRepository

from backend.modules.company.application.services import CompanyIntelligenceService
from backend.modules.company.infrastructure.repositories import (
    SqlCompanyScoreRepository,
)

from backend.modules.prediction.application.services import PredictionService
from backend.modules.prediction.infrastructure.predictors import LogisticBaselineModel
from backend.modules.prediction.infrastructure.repositories import (
    SqlPredictionRepository,
)

from backend.modules.signals.application.services import SignalFusionService
from backend.modules.signals.infrastructure.repositories import (
    SqlFusedSignalRepository,
)

from backend.modules.reasoning.application.services import ReasoningService
from backend.modules.reasoning.infrastructure.reasoners import (
    DeterministicReasoner,
    LLMReasoner,
)
from backend.modules.reasoning.infrastructure.repositories import (
    SqlReasonedOpinionRepository,
)

from backend.modules.backtesting.application.services import BacktestService


# The request-scoped database session dependency now lives in
# backend.core.database (get_db_session) so the engine/session factory is
# shared across the app instead of being re-created here.


async def get_market_data_service(
    session: AsyncSession = Depends(get_db_session),
) -> MarketDataService:
    """
    Provide market data service.
    """
    settings = get_settings()

    provider_name = settings.market_data_provider.strip().lower()
    if provider_name != "finnhub":
        raise ConfigurationError(
            "MARKET_DATA_PROVIDER must be set to 'finnhub' for the current backend integration."
        )

    client = FinnhubClient(settings=settings)
    market_data_repository = SqlMarketDataRepository(
        session,
        base_currency=settings.base_currency,
    )
    yfinance_provider = YFinanceHistoricalDataProvider()

    # Static (offline) FX rates from config; used directly when FX_LIVE is off
    # and as the fallback for the live yfinance provider otherwise.
    static_fx = StaticFxRateProvider(
        base_currency=settings.base_currency,
        overrides={
            "USD": settings.fx_usd_inr,
            "EUR": settings.fx_eur_inr,
            "GBP": settings.fx_gbp_inr,
        },
    )
    fx_provider = (
        YFinanceFxRateProvider(
            fallback=static_fx,
            base_currency=settings.base_currency,
            ttl_seconds=settings.fx_cache_ttl_seconds,
        )
        if settings.fx_live
        else static_fx
    )

    return MarketDataService(
        quote_repository=FinnhubQuoteRepository(client),
        historical_price_repository=market_data_repository,
        symbol_search_repository=CompositeSymbolSearchRepository(
            storage_repository=market_data_repository,
            provider_repository=FinnhubSymbolSearchRepository(client),
        ),
        market_metadata_repository=FinnhubMarketMetadataRepository(client),
        historical_price_provider=yfinance_provider,
        company_profile_repository=market_data_repository,
        company_profile_provider=yfinance_provider,
        fx_rate_provider=fx_provider,
        base_currency=settings.base_currency,
        commit=session.commit,
    )


async def get_news_intelligence_service(
    session: AsyncSession = Depends(get_db_session),
) -> NewsIntelligenceService:
    """
    Provide news intelligence service.
    """
    settings = get_settings()

    provider_name = settings.market_data_provider.strip().lower()
    if provider_name != "finnhub":
        raise ConfigurationError(
            "MARKET_DATA_PROVIDER must be set to 'finnhub' for the current news integration."
        )

    client = FinnhubClient(settings=settings)
    return NewsIntelligenceService(
        repository=SqlNewsArticleRepository(session),
        provider=FinnhubNewsProvider(client),
        commit=session.commit,
    )


async def get_event_extraction_service(
    session: AsyncSession = Depends(get_db_session),
) -> EventExtractionService:
    """
    Provide event extraction service.

    Reads articles from the news warehouse and writes structured events.
    The default extractor is deterministic and rule-based (no external
    dependency); swap in an LLM-backed adapter here to upgrade extraction
    without changing the service, domain, or routes.
    """
    rule_based = RuleBasedEventExtractor()
    llm = build_llm_from_settings(get_settings())
    # Use the LLM extractor when a model is configured (LLM_ENABLED=true),
    # falling back to the deterministic rule-based extractor on any failure.
    extractor = LLMEventExtractor(llm, fallback=rule_based) if llm else rule_based

    return EventExtractionService(
        article_repository=SqlNewsArticleRepository(session),
        event_repository=SqlNewsEventRepository(session),
        extractor=extractor,
        commit=session.commit,
    )


async def get_research_service(
    session: AsyncSession = Depends(get_db_session),
) -> ResearchService:
    """
    Provide research RAG service.

    The default embedder is a deterministic feature-hashing embedder and the
    default parser handles plain text (no model download, no network). Swap in
    a sentence-transformers / hosted-API embedder or a PDF parser adapter here
    to upgrade retrieval quality without changing the service, store, or routes.
    """
    return ResearchService(
        repository=SqlResearchRepository(session),
        embedder=HashingEmbedder(),
        parser=PlainTextParser(),
        commit=session.commit,
    )


async def get_company_intelligence_service(
    session: AsyncSession = Depends(get_db_session),
) -> CompanyIntelligenceService:
    """
    Provide the Phase 10 company intelligence service.

    Reads company profiles + price history through the market data service and
    recent events from the events warehouse, then stores comparable scorecards.
    """
    return CompanyIntelligenceService(
        market_data_service=await get_market_data_service(session),
        event_repository=SqlNewsEventRepository(session),
        score_repository=SqlCompanyScoreRepository(session),
        commit=session.commit,
    )


async def get_prediction_service(
    session: AsyncSession = Depends(get_db_session),
) -> PredictionService:
    """
    Provide the Phase 12 prediction service.

    Uses the dependency-free logistic-regression baseline over price history
    from the market data service. Swap in a trained model (sklearn/XGBoost/
    deep) here behind the same PredictionModelContract to upgrade forecasts.
    """
    return PredictionService(
        market_data_service=await get_market_data_service(session),
        model=LogisticBaselineModel(),
        repository=SqlPredictionRepository(session),
        commit=session.commit,
    )


async def get_signal_fusion_service(
    session: AsyncSession = Depends(get_db_session),
) -> SignalFusionService:
    """
    Provide the Phase 13 signal fusion service.

    Blends the stored outputs of the news (Phase 8), company (Phase 10), and
    prediction (Phase 12) layers into a unified Buy/Hold/Sell recommendation.
    """
    return SignalFusionService(
        event_repository=SqlNewsEventRepository(session),
        company_repository=SqlCompanyScoreRepository(session),
        prediction_repository=SqlPredictionRepository(session),
        signal_repository=SqlFusedSignalRepository(session),
        commit=session.commit,
    )


async def get_reasoning_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReasoningService:
    """
    Provide the Phase 11 reasoning service.

    Gathers the fused signal, company score, events, and research context, then
    produces an explainable opinion. Uses the LLM reasoner when LLM_ENABLED=true
    (falling back to the deterministic reasoner), else the deterministic one.
    """
    deterministic = DeterministicReasoner()
    llm = build_llm_from_settings(get_settings())
    reasoner = LLMReasoner(llm, fallback=deterministic) if llm else deterministic

    return ReasoningService(
        signal_repository=SqlFusedSignalRepository(session),
        company_repository=SqlCompanyScoreRepository(session),
        event_repository=SqlNewsEventRepository(session),
        opinion_repository=SqlReasonedOpinionRepository(session),
        reasoner=reasoner,
        research_service=await get_research_service(session),
        commit=session.commit,
    )


async def get_backtest_service(
    session: AsyncSession = Depends(get_db_session),
) -> BacktestService:
    """
    Provide the Phase 15 backtesting service.

    Stateless historical investment simulation over INR price history from the
    market data service (lump-sum and SIP, with return + risk analytics).
    """
    return BacktestService(
        market_data_service=await get_market_data_service(session),
    )


async def get_simulator_service(
    session: AsyncSession = Depends(get_db_session),
) -> SimulatorService:
    """
    Provide simulator service.
    """

    environment_repo = SqlEnvironmentRepository(session)
    holding_repo = SqlHoldingRepository(session)
    transaction_repo = SqlTransactionRepository(session)
    # portfolio_snapshots are reserved for future backtesting/RL use and are
    # not yet written by any use case, so no snapshot repository is wired here.

    market_data_service = await get_market_data_service(session)

    create_environment = CreateEnvironmentUseCase(
        environment_repository=environment_repo,
    )

    rename_environment = RenameEnvironmentUseCase(
        environment_repository=environment_repo,
    )

    delete_environment = DeleteEnvironmentUseCase(
        environment_repository=environment_repo,
    )

    add_virtual_cash = AddVirtualCashUseCase(
        environment_repository=environment_repo,
        transaction_repository=transaction_repo,
    )

    withdraw_virtual_cash = WithdrawVirtualCashUseCase(
        environment_repository=environment_repo,
        transaction_repository=transaction_repo,
    )

    buy_stock = BuyStockUseCase(
        environment_repository=environment_repo,
        holding_repository=holding_repo,
        transaction_repository=transaction_repo,
        market_data_service=market_data_service,
    )

    sell_stock = SellStockUseCase(
        environment_repository=environment_repo,
        holding_repository=holding_repo,
        transaction_repository=transaction_repo,
        market_data_service=market_data_service,
    )

    get_environment = GetEnvironmentUseCase(
        environment_repository=environment_repo,
    )

    get_holdings = GetHoldingsUseCase(
        holding_repository=holding_repo,
        market_data_service=market_data_service,
    )

    get_transactions = GetTransactionsUseCase(
        transaction_repository=transaction_repo,
    )

    get_portfolio_performance = GetPortfolioPerformanceUseCase(
        environment_repository=environment_repo,
        holding_repository=holding_repo,
        market_data_service=market_data_service,
    )

    return SimulatorService(
        create_environment=create_environment,
        rename_environment=rename_environment,
        delete_environment=delete_environment,
        add_virtual_cash=add_virtual_cash,
        withdraw_virtual_cash=withdraw_virtual_cash,
        buy_stock=buy_stock,
        sell_stock=sell_stock,
        get_environment=get_environment,
        get_holdings=get_holdings,
        get_transactions=get_transactions,
        get_portfolio_performance=get_portfolio_performance,
        commit=session.commit,
    )
