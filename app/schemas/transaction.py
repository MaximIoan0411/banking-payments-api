import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.enums import TransactionStatus, TransactionType


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: TransactionType
    status: TransactionStatus
    amount: Decimal
    description: str | None
    merchant_name: str | None
    created_at: datetime