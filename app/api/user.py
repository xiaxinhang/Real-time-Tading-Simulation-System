from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import KlineResponse, MarketMetricsResponse, UserMetricsResponse
from app.service.analysis import analysis_service
from app.service.market import market_service
from app.service.market_query import market_query_service

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/user/{user_id}/analysis", response_model=UserMetricsResponse)
async def user_analysis(user_id: str) -> UserMetricsResponse:
    return analysis_service.user_metrics(user_id)


@router.get("/market/analysis", response_model=MarketMetricsResponse)
async def market_analysis() -> MarketMetricsResponse:
    return analysis_service.market_metrics()


@router.post("/market/refresh-real")
async def refresh_real_market() -> dict:
    return await market_service.refresh_real_now()


@router.get("/market/klines", response_model=list[KlineResponse])
async def market_klines(
    symbol: str,
    interval: str = "1m",
    limit: int = 120,
    db: Session = Depends(get_db),
) -> list[KlineResponse]:
    return market_query_service.klines(db, symbol=symbol, interval=interval, limit=min(limit, 500))
