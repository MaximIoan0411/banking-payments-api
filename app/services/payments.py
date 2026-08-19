from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TransactionStatus, TransactionType
from app.models.account import Account
from app.models.transaction import Transaction


async def get_account_by_number(db: AsyncSession, account_number: str) -> Account | None:
    result = await db.execute(select(Account).where(Account.account_number == account_number))
    return result.scalar_one_or_none()


async def execute_deposit(
    db: AsyncSession, account_id: uuid.UUID, amount: Decimal, description: str | None
) -> Transaction:
    result = await db.execute(select(Account).where(Account.id == account_id).with_for_update())
    account = result.scalar_one()

    account.balance += amount
    transaction = Transaction(
        account_id=account_id,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.COMPLETED,
        amount=amount,
        description=description,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    return transaction


async def execute_payment(
    db: AsyncSession,
    sender_account_id: uuid.UUID,
    recipient_account_id: uuid.UUID,
    amount: Decimal,
    description: str | None,
    idempotency_key_id: uuid.UUID,
) -> Transaction:
    result = await db.execute(
        select(Account).where(Account.id == sender_account_id).with_for_update()
    )
    sender_account = result.scalar_one()

    if sender_account.balance < amount:
        transaction = Transaction(
            account_id=sender_account_id,
            related_account_id=recipient_account_id,
            idempotency_key_id=idempotency_key_id,
            type=TransactionType.PAYMENT,
            status=TransactionStatus.FAILED,
            amount=amount,
            description=description,
        )
    else:
        sender_account.balance -= amount
        transaction = Transaction(
            account_id=sender_account_id,
            related_account_id=recipient_account_id,
            idempotency_key_id=idempotency_key_id,
            type=TransactionType.PAYMENT,
            status=TransactionStatus.PENDING,
            amount=amount,
            description=description,
        )

    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    return transaction