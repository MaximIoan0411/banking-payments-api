from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey

IDEMPOTENCY_KEY_TTL_HOURS = 24


def compute_request_hash(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


async def get_existing_idempotency_key(
    db: AsyncSession, user_id: uuid.UUID, key: str, endpoint: str
) -> IdempotencyKey | None:
    result = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user_id,
            IdempotencyKey.key == key,
            IdempotencyKey.endpoint == endpoint,
        )
    )
    return result.scalar_one_or_none()


async def reserve_idempotency_key(
    db: AsyncSession, user_id: uuid.UUID, key: str, endpoint: str, request_hash: str
) -> IdempotencyKey | None:
    entry = IdempotencyKey(
        key=key,
        user_id=user_id,
        endpoint=endpoint,
        request_hash=request_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=IDEMPOTENCY_KEY_TTL_HOURS),
    )
    db.add(entry)
    try:
        await db.commit()
        await db.refresh(entry)
        return entry
    except IntegrityError:
        await db.rollback()
        return None


async def finalize_idempotency_key(
    db: AsyncSession, entry_id: uuid.UUID, status_code: int, response_body: str
) -> None:
    entry = await db.get(IdempotencyKey, entry_id)
    if entry is None:
        return
    entry.status_code = status_code
    entry.response_body = response_body
    await db.commit()