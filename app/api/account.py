from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import Account, CashFlow, Position, User
from app.models.models import AccountDetailResponse, CashFlowResponse, PositionDetailResponse

router = APIRouter(prefix="/api", tags=["account"])


def _account_for_user(db: Session, user: User) -> Account:
    account = db.scalar(select(Account).where(Account.user_id == user.id))
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/account", response_model=AccountDetailResponse)
async def get_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountDetailResponse:
    account = _account_for_user(db, current_user)
    position_value = sum(position.quantity * position.avg_price for position in account.positions)
    return AccountDetailResponse(
        cash=round(account.cash, 2),
        available_cash=round(account.available_cash, 2),
        frozen_cash=round(account.frozen_cash, 2),
        realized_pnl=round(account.realized_pnl, 2),
        total_equity=round(account.cash + position_value, 2),
    )


@router.get("/positions", response_model=list[PositionDetailResponse])
async def get_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PositionDetailResponse]:
    account = _account_for_user(db, current_user)
    rows = db.scalars(select(Position).where(Position.account_id == account.id).order_by(Position.symbol)).all()
    return [
        PositionDetailResponse(
            symbol=row.symbol,
            quantity=row.quantity,
            available_quantity=row.available_quantity,
            frozen_quantity=row.frozen_quantity,
            avg_price=round(row.avg_price, 4),
        )
        for row in rows
    ]


@router.get("/cashflows", response_model=list[CashFlowResponse])
async def get_cashflows(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CashFlowResponse]:
    rows = db.scalars(
        select(CashFlow)
        .where(CashFlow.user_id == current_user.id)
        .order_by(CashFlow.created_at.desc(), CashFlow.id.desc())
        .limit(100)
    ).all()
    return [
        CashFlowResponse(
            id=row.id,
            flow_type=row.flow_type,
            amount=round(row.amount, 2),
            balance_after=round(row.balance_after, 2),
            ref_id=row.ref_id,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
