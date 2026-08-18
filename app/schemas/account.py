import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_number: str
    balance: Decimal
    currency: str