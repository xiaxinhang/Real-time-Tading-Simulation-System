from __future__ import annotations

from fastapi import APIRouter

from app.models.models import MarketMetricsResponse, UserMetricsResponse
from app.service.analysis import analysis_service

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/user/{user_id}/analysis", response_model=UserMetricsResponse)
async def user_analysis(user_id: str) -> UserMetricsResponse:
    return analysis_service.user_metrics(user_id)


@router.get("/market/analysis", response_model=MarketMetricsResponse)
async def market_analysis() -> MarketMetricsResponse:
    return analysis_service.market_metrics()
