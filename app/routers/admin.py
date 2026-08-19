from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_account_or_404, get_current_admin, get_db
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.admin import AdminAccountOut
from app.schemas.transaction import TransactionOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


@router.get("/accounts", response_model=list[AdminAccountOut])
async def list_recent_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    result = await db.execute(
        select(Account, User.email, User.full_name)
        .join(User, User.id == Account.user_id)
        .order_by(Account.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        AdminAccountOut(
            id=account.id,
            account_number=account.account_number,
            balance=account.balance,
            currency=account.currency,
            owner_email=email,
            owner_full_name=full_name,
            created_at=account.created_at,
        )
        for account, email, full_name in result.all()
    ]


@router.get("/transactions", response_model=list[TransactionOut])
async def list_recent_transactions(
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    result = await db.execute(
        select(Transaction)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/accounts/{account_id}/transactions", response_model=list[TransactionOut])
async def list_account_transactions(
    account: Annotated[Account, Depends(get_account_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    account_id = account.id
    result = await db.execute(
        select(Transaction)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()