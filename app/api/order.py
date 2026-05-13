from __future__ import annotations

from fastapi import APIRouter

from app.models.models import OrderResponse, PlaceOrderRequest, PortfolioResponse
from app.service.trade import trade_service

router = APIRouter(prefix="/api", tags=["trade"])


@router.post("/order", response_model=OrderResponse)
async def place_order(payload: PlaceOrderRequest) -> OrderResponse:
    return await trade_service.place_order(payload)


@router.get("/order/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str) -> OrderResponse:
    return trade_service.get_order(order_id)


@router.get("/user/{user_id}/portfolio", response_model=PortfolioResponse)
async def get_portfolio(user_id: str) -> PortfolioResponse:
    return trade_service.get_user_portfolio(user_id)
