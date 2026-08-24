import json

from sqlalchemy import select

from app.config import get_settings
from app.models.webhook_event import WebhookEvent
from app.services.webhook_signature import generate_signature

settings = get_settings()


def _signed_headers(body: dict) -> dict:
    raw_body = json.dumps(body).encode()
    signature = generate_signature(raw_body, settings.WEBHOOK_SECRET)
    return {"X-Webhook-Signature": signature, "Content-Type": "application/json"}


async def _create_pending_payment(client, funded_sender, recipient, idempotency_key, amount="100.00"):
    response = await client.post(
        "/transactions/payments",
        json={
            "amount": amount,
            "recipient_account_number": recipient["account_number"],
            "description": "webhook test",
        },
        headers={**funded_sender["headers"], "Idempotency-Key": idempotency_key},
    )
    return response.json()


async def test_webhook_invalid_signature(client):
    body = {
        "event_id": "evt_1",
        "event_type": "payment.succeeded",
        "transaction_id": "00000000-0000-0000-0000-000000000000",
        "amount": "10.00",
    }
    response = await client.post(
        "/webhooks/payment-confirmation",
        content=json.dumps(body),
        headers={"X-Webhook-Signature": "sha256=invalid", "Content-Type": "application/json"},
    )
    assert response.status_code == 401


async def test_webhook_payment_succeeded_credits_recipient(client, funded_sender, recipient):
    transaction = await _create_pending_payment(client, funded_sender, recipient, "wh-key-1")

    body = {
        "event_id": "evt_success_1",
        "event_type": "payment.succeeded",
        "transaction_id": transaction["id"],
        "amount": "100.00",
    }
    response = await client.post(
        "/webhooks/payment-confirmation", content=json.dumps(body), headers=_signed_headers(body)
    )
    assert response.status_code == 202

    recipient_balance = await client.get("/accounts/me", headers=recipient["headers"])
    assert recipient_balance.json()["balance"] == "100.00"


async def test_webhook_duplicate_event_ignored(client, funded_sender, recipient):
    transaction = await _create_pending_payment(client, funded_sender, recipient, "wh-key-2")
    body = {
        "event_id": "evt_dup_1",
        "event_type": "payment.succeeded",
        "transaction_id": transaction["id"],
        "amount": "100.00",
    }
    headers = _signed_headers(body)

    await client.post("/webhooks/payment-confirmation", content=json.dumps(body), headers=headers)
    await client.post("/webhooks/payment-confirmation", content=json.dumps(body), headers=headers)

    recipient_balance = await client.get("/accounts/me", headers=recipient["headers"])
    assert recipient_balance.json()["balance"] == "100.00"


async def test_webhook_payment_failed_refunds_sender(client, funded_sender, recipient):
    transaction = await _create_pending_payment(client, funded_sender, recipient, "wh-key-3")
    body = {
        "event_id": "evt_failed_1",
        "event_type": "payment.failed",
        "transaction_id": transaction["id"],
        "amount": "100.00",
    }
    response = await client.post(
        "/webhooks/payment-confirmation", content=json.dumps(body), headers=_signed_headers(body)
    )
    assert response.status_code == 202

    sender_balance = await client.get("/accounts/me", headers=funded_sender["headers"])
    assert sender_balance.json()["balance"] == "500.00"


async def test_webhook_amount_mismatch_records_error(client, db_session, funded_sender, recipient):
    transaction = await _create_pending_payment(client, funded_sender, recipient, "wh-key-4")
    body = {
        "event_id": "evt_mismatch_1",
        "event_type": "payment.succeeded",
        "transaction_id": transaction["id"],
        "amount": "999.00",
    }
    response = await client.post(
        "/webhooks/payment-confirmation", content=json.dumps(body), headers=_signed_headers(body)
    )
    assert response.status_code == 202

    result = await db_session.execute(select(WebhookEvent).where(WebhookEvent.event_id == "evt_mismatch_1"))
    event = result.scalar_one()
    assert event.processed is False
    assert "Amount mismatch" in event.error_message


async def test_webhook_transaction_not_found_records_error(client, db_session):
    body = {
        "event_id": "evt_notfound_1",
        "event_type": "payment.succeeded",
        "transaction_id": "00000000-0000-0000-0000-000000000000",
        "amount": "50.00",
    }
    response = await client.post(
        "/webhooks/payment-confirmation", content=json.dumps(body), headers=_signed_headers(body)
    )
    assert response.status_code == 202

    result = await db_session.execute(select(WebhookEvent).where(WebhookEvent.event_id == "evt_notfound_1"))
    event = result.scalar_one()
    assert "not found" in event.error_message