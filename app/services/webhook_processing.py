from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TransactionStatus, TransactionType
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.webhook_event import WebhookEvent

import logging

logger = logging.getLogger(__name__)


class TransactionNotFoundError(Exception):
    def __init__(self, transaction_id: uuid.UUID) -> None:
        super().__init__(f"Transaction {transaction_id} not found")


class TransactionAlreadyProcessedError(Exception):
    def __init__(self, transaction_id: uuid.UUID) -> None:
        super().__init__(f"Transaction {transaction_id} was already processed")


class AmountMismatchError(Exception):
    def __init__(self, expected: Decimal, received: Decimal) -> None:
        super().__init__(f"Amount mismatch: transaction has {expected}, webhook sent {received}")


async def reserve_webhook_event(
    db: AsyncSession, event_id: str, event_type: str, payload: str
) -> WebhookEvent | None:
    entry = WebhookEvent(
        event_id=event_id, event_type=event_type, payload=payload, signature_valid=True
    )
    db.add(entry)
    try:
        await db.commit()
        await db.refresh(entry)
        return entry
    except IntegrityError:
        await db.rollback()
        return None


async def get_existing_webhook_event(db: AsyncSession, event_id: str) -> WebhookEvent | None:
    result = await db.execute(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
    return result.scalar_one_or_none()


async def mark_webhook_processed(db: AsyncSession, entry_id: uuid.UUID) -> None:
    event = await db.get(WebhookEvent, entry_id)
    if event:
        event.processed = True
        await db.commit()


async def process_payment_succeeded(
    db: AsyncSession, transaction_id: uuid.UUID, amount: Decimal
) -> None:
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id).with_for_update()
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise TransactionNotFoundError(transaction_id)
    if transaction.status != TransactionStatus.PENDING:
        raise TransactionAlreadyProcessedError(transaction_id)
    if transaction.amount != amount:
        raise AmountMismatchError(transaction.amount, amount)

    sender_account_id = transaction.account_id
    recipient_account_id = transaction.related_account_id
    description = transaction.description

    result = await db.execute(
        select(Account).where(Account.id == recipient_account_id).with_for_update()
    )
    recipient_account = result.scalar_one()
    recipient_account.balance += amount

    db.add(
        Transaction(
            account_id=recipient_account_id,
            related_account_id=sender_account_id,
            type=TransactionType.TRANSFER_IN,
            status=TransactionStatus.COMPLETED,
            amount=amount,
            description=description,
        )
    )

    transaction.status = TransactionStatus.COMPLETED
    await db.commit()


async def process_payment_failed(
    db: AsyncSession, transaction_id: uuid.UUID, amount: Decimal
) -> None:
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id).with_for_update()
    )
    transaction = result.scalar_one_or_none()
    if transaction is None:
        raise TransactionNotFoundError()
    if transaction.status != TransactionStatus.PENDING:
        raise TransactionAlreadyProcessedError()
    if transaction.amount != amount:
        raise AmountMismatchError()

    sender_account_id = transaction.account_id

    result = await db.execute(
        select(Account).where(Account.id == sender_account_id).with_for_update()
    )
    sender_account = result.scalar_one()
    sender_account.balance += amount  

    transaction.status = TransactionStatus.FAILED
    await db.commit()
    
    
async def record_webhook_error(db: AsyncSession, entry_id: uuid.UUID, error_message: str) -> None:
    event = await db.get(WebhookEvent, entry_id)
    if event:
        event.error_message = error_message
        await db.commit()


async def handle_webhook_event(
    db: AsyncSession,
    entry_id: uuid.UUID,
    event_type: str,
    transaction_id: uuid.UUID,
    amount: Decimal,
) -> None:
    try:
        if event_type == "payment.succeeded":
            await process_payment_succeeded(db, transaction_id, amount)
        else:
            await process_payment_failed(db, transaction_id, amount)
        await mark_webhook_processed(db, entry_id)
    except (TransactionNotFoundError, TransactionAlreadyProcessedError, AmountMismatchError) as exc:
        await db.rollback()
        logger.warning("Webhook event %s failed: %s", entry_id, exc)
        await record_webhook_error(db, entry_id, str(exc))
    except Exception:
        await db.rollback()
        logger.exception("Unexpected error processing webhook event %s", entry_id)
        await record_webhook_error(db, entry_id, "Unexpected internal error")