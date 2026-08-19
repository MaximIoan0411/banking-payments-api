from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_account, get_db
from app.models.account import Account
from app.schemas.transaction import DepositCreate, PaymentCreate, TransactionOut
from app.services.idempotency import (
    compute_request_hash,
    finalize_idempotency_key,
    get_existing_idempotency_key,
    reserve_idempotency_key,
)
from app.services.payments import execute_deposit, execute_payment, get_account_by_number

router = APIRouter(prefix="/transactions", tags=["transactions"])

PAYMENTS_ENDPOINT = "POST /transactions/payments"


@router.post("/deposits", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_deposit(
    payload: DepositCreate,
    account: Annotated[Account, Depends(get_current_account)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await execute_deposit(db, account.id, payload.amount, payload.description)


@router.post("/payments", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    account: Annotated[Account, Depends(get_current_account)],
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
):
    
    sender_account_id = account.id
    sender_user_id = account.user_id
    sender_account_number = account.account_number

    if payload.recipient_account_number == sender_account_number:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Nu poți face o plată către propriul cont"
        )

    recipient = await get_account_by_number(db, payload.recipient_account_number)
    if recipient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contul destinatar nu există")
    recipient_account_id = recipient.id

    request_hash = compute_request_hash(payload.model_dump(mode="json"))

    entry = await reserve_idempotency_key(
        db, sender_user_id, idempotency_key, PAYMENTS_ENDPOINT, request_hash
    )

    if entry is None:
        existing = await get_existing_idempotency_key(
            db, sender_user_id, idempotency_key, PAYMENTS_ENDPOINT
        )
        if existing is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Idempotency key conflict, retry")
        if existing.request_hash != request_hash:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Idempotency-Key reused with a different request payload",
            )
        if existing.response_body is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Request with this Idempotency-Key is already being processed",
            )
        return TransactionOut.model_validate_json(existing.response_body)

    entry_id = entry.id

    transaction = await execute_payment(
        db, sender_account_id, recipient_account_id, payload.amount, payload.description, entry_id
    )

    response = TransactionOut.model_validate(transaction)
    await finalize_idempotency_key(db, entry_id, status.HTTP_201_CREATED, response.model_dump_json())
    return response