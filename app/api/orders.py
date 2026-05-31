from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.models.models import CreateOrderRequest, DbOrderResponse, DbTradeResponse
from app.service.persistent_trade import persistent_trade_service

router = APIRouter(prefix="/api", tags=["orders"])


@router.post("/orders", response_model=DbOrderResponse)
async def create_order(
    payload: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DbOrderResponse:
    return persistent_trade_service.place_order(db, current_user, payload)


@router.get("/orders", response_model=list[DbOrderResponse])
async def list_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DbOrderResponse]:
    return persistent_trade_service.list_orders(db, current_user)


@router.get("/orders/{order_id}", response_model=DbOrderResponse)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DbOrderResponse:
    return persistent_trade_service.get_order(db, current_user, order_id)


@router.delete("/orders/{order_id}", response_model=DbOrderResponse)
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DbOrderResponse:
    return persistent_trade_service.cancel_order(db, current_user, order_id)


@router.get("/trades", response_model=list[DbTradeResponse])
async def list_trades(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DbTradeResponse]:
    return persistent_trade_service.list_trades(db, current_user)
