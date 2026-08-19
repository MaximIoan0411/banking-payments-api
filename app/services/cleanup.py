from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TransactionStatus, TransactionType
from app.models.account import Account
from app.models.idempotency_key import IdempotencyKey
from app.models.transaction import Transaction
from app.models.webhook_event import WebhookEvent

logger = logging.getLogger(__name__)

WEBHOOK_EVENT_RETENTION_DAYS = 7
PENDING_TRANSACTION_TIMEOUT_HOURS = 24


async def cleanup_expired_idempotency_keys(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(delete(IdempotencyKey).where(IdempotencyKey.expires_at < now))
    await db.commit()
    return result.rowcount or 0


async def cleanup_old_webhook_events(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=WEBHOOK_EVENT_RETENTION_DAYS)
    result = await db.execute(
        delete(WebhookEvent).where(
            WebhookEvent.processed.is_(True),
            WebhookEvent.created_at < cutoff,
        )
    )
    await db.commit()
    return result.rowcount or 0


async def expire_stale_pending_transactions(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=PENDING_TRANSACTION_TIMEOUT_HOURS)
    result = await db.execute(
        select(Transaction.id).where(
            Transaction.status == TransactionStatus.PENDING,
            Transaction.type == TransactionType.PAYMENT,
            Transaction.created_at < cutoff,
        )
    )
    stale_ids = [row[0] for row in result.all()]

    expired_count = 0
    for transaction_id in stale_ids:
        result = await db.execute(
            select(Transaction).where(Transaction.id == transaction_id).with_for_update()
        )
        transaction = result.scalar_one_or_none()
        if transaction is None or transaction.status != TransactionStatus.PENDING:
            continue  
        
        sender_account_id = transaction.account_id
        amount = transaction.amount

        result = await db.execute(
            select(Account).where(Account.id == sender_account_id).with_for_update()
        )
        sender_account = result.scalar_one()
        sender_account.balance += amount  

        transaction.status = TransactionStatus.FAILED
        transaction.description = f"{transaction.description or ''} [auto-expired by cleanup job]".strip()

        await db.commit()
        expired_count += 1

    return expired_count