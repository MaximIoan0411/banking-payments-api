from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db
from app.schemas.webhook import WebhookPaymentConfirmation
from app.services.webhook_processing import get_existing_webhook_event, handle_webhook_event, reserve_webhook_event
from app.services.webhook_signature import verify_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()


@router.post("/payment-confirmation", status_code=status.HTTP_202_ACCEPTED)
async def payment_confirmation(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_webhook_signature: Annotated[str, Header(alias="X-Webhook-Signature")],
):
    raw_body = await request.body()

    if not verify_signature(raw_body, x_webhook_signature, settings.WEBHOOK_SECRET):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature")

    try:
        payload = WebhookPaymentConfirmation.model_validate_json(raw_body)
    except ValidationError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid payload")

    entry = await reserve_webhook_event(
        db, payload.event_id, payload.event_type, raw_body.decode()
    )

    if entry is None:
        return {"status": "duplicate event, ignored"}

    background_tasks.add_task(
        handle_webhook_event, db, entry.id, payload.event_type, payload.transaction_id, payload.amount
    )

    return {"status": "accepted, processing"}