import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import TransactionStatus, TransactionType


class DepositCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    recipient_account_number: str = Field(min_length=1, max_length=34)
    description: str | None = Field(default=None, max_length=255)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: TransactionType
    status: TransactionStatus
    amount: Decimal
    description: str | None
    related_account_id: uuid.UUID | None
    created_at: datetime