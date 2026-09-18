from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_prediction_service
from backend.modules.prediction.application.dto import (
    ForecastRequest,
    MultiHorizonForecastView,
    PredictionsView,
    PredictionView,
    PredictRequest,
)
from backend.modules.prediction.application.services import PredictionService

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/predict/{symbol}", response_model=PredictionView)
async def predict(
    symbol: str,
    lookback_days: int = Query(default=365, ge=30, le=3650),
    horizon_days: int = Query(default=1, ge=1, le=30),
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionView:
    """Forecast the next move for a symbol from its price history."""
    try:
        return await service.predict(
            PredictRequest(
                symbol=symbol, lookback_days=lookback_days, horizon_days=horizon_days
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/forecast/{symbol}", response_model=MultiHorizonForecastView)
async def forecast(
    symbol: str,
    lookback_days: int = Query(default=730, ge=60, le=3650),
    horizons: list[int] = Query(default=[1, 5, 21, 63]),
    include_events: bool = Query(default=True),
    service: PredictionService = Depends(get_prediction_service),
) -> MultiHorizonForecastView:
    """Forecast a symbol across several horizons at once.

    Runs the hybrid ensemble — a logistic classifier on technical features, an
    EWMA drift/volatility model, and an AR(1) model on log returns — pooling
    their probabilities in log-odds space, then tilting the blend by the
    recent news-event score for the symbol.

    Defaults cover 1 day, 1 week, 1 month, and 1 quarter of trading days.
    Reporting several horizons is deliberate: 1-day direction is close to a
    coin flip and skill improves with horizon, so a single number invites
    over-reading. Pass ``include_events=false`` for a price-only forecast,
    which is the clean way to see what the news term actually contributed.

    This endpoint does not persist — use ``POST /predictions/predict/{symbol}``
    for a stored, single-horizon forecast.
    """
    try:
        return await service.forecast(
            ForecastRequest(
                symbol=symbol,
                lookback_days=lookback_days,
                horizons=tuple(horizons),
                include_events=include_events,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=PredictionsView)
async def list_predictions(
    limit: int = Query(default=50, ge=1, le=200),
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionsView:
    """List the latest forecast per symbol, most recent first."""
    return await service.list_latest(limit=limit)


@router.get("/{symbol}", response_model=PredictionView)
async def get_prediction(
    symbol: str,
    service: PredictionService = Depends(get_prediction_service),
) -> PredictionView:
    """Get the latest stored forecast for a symbol."""
    try:
        return await service.get_latest(symbol)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


"""
Purpose:
Expose Phase 12 price-direction forecasts over HTTP.

Endpoints:
- POST /predictions/predict/{symbol}: Forecast and store
- GET /predictions: List latest forecasts
- GET /predictions/{symbol}: Latest forecast for one symbol

What Should Not Live Here:
- Model math (infrastructure/predictors.py) or feature engineering (domain).
"""
