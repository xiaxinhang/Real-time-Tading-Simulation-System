from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.models.models import CreateStrategyRequest, StrategyResponse
from app.service.strategy import strategy_service

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.post("", response_model=StrategyResponse)
async def create_strategy(
    payload: CreateStrategyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StrategyResponse:
    return strategy_service.create_strategy(db, current_user, payload)


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StrategyResponse]:
    return strategy_service.list_strategies(db, current_user)


@router.post("/{strategy_id}/start", response_model=StrategyResponse)
async def start_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StrategyResponse:
    return strategy_service.start_strategy(db, current_user, strategy_id)


@router.post("/{strategy_id}/stop", response_model=StrategyResponse)
async def stop_strategy(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StrategyResponse:
    return strategy_service.stop_strategy(db, current_user, strategy_id)


@router.post("/{strategy_id}/run-once", response_model=StrategyResponse)
async def run_strategy_once(
    strategy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StrategyResponse:
    return strategy_service.run_once(db, current_user, strategy_id)
