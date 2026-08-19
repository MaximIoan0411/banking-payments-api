import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr


class AdminAccountOut(BaseModel):
    id: uuid.UUID
    account_number: str
    balance: Decimal
    currency: str
    owner_email: EmailStr
    owner_full_name: str
    created_at: datetime