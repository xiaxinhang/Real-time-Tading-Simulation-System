from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Account, CashFlow, User


class AccountService:
    def create_default_account(self, db: Session, user: User) -> Account:
        account = Account(
            user_id=user.id,
            cash=settings.initial_cash,
            available_cash=settings.initial_cash,
            frozen_cash=0.0,
            realized_pnl=0.0,
        )
        db.add(account)
        db.flush()
        db.add(
            CashFlow(
                user_id=user.id,
                flow_type="initial_deposit",
                amount=settings.initial_cash,
                balance_after=settings.initial_cash,
                ref_id=None,
            )
        )
        return account


account_service = AccountService()
