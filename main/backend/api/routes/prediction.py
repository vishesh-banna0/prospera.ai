from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_prediction_service
from backend.modules.prediction.application.dto import (
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
