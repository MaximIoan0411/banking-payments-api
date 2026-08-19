import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class WebhookPaymentConfirmation(BaseModel):
    event_id: str
    event_type: Literal["payment.succeeded", "payment.failed"]
    transaction_id: uuid.UUID
    amount: Decimal